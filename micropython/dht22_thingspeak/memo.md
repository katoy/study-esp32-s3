# ESP32-S3 DHT22 Monitor — 開発メモ

最終更新: 2025-09-28

## 方針（現行）
- フロント資産は `static/app.js` と `static/style.css` に一本化（旧: app_mini.js, style_mini.css, app_lite_min.js は廃止）
- サーバは `microdot` による HTTP API（WebSocket は現行未使用）
- センサーは DHT22（GPIO4 推奨、外付けプルアップ必須）
- ThingSpeak は JST スロット境界で整列送信。UI 非依存のバックグラウンド送信スレッドあり

## API 一覧（現行）
- GET `/` → index.html
- GET `/static/app.js`, `/static/style.css`
- GET `/manifest.json`
- GET `/health`, `/config`, `/api/system`
- GET `/api/realtime`, `/api/data`, `/api/logs`

## データ仕様（要点）
- `/api/realtime` の `type` はレガシー互換のため "dht11" 固定。実機は DHT22
- 温度・湿度は 1 桁小数で丸め（`round(x, 1)`）
- 失敗時は前回正常データを `/api/data` で返すフォールバック

## センサー安定化/リトライ
- 測定直前に 60ms 待機で安定化
- 3 回までリトライ。2 回目以降はセンサー再初期化
- 妥当性チェック: `-40≤temp≤80`, `0≤hum≤100`, かつ `!= 1`
- 取得成功で履歴を保持（最大 100 件、古いものから削除）

## 送信/スロット制御（ThingSpeak）
- `THINGSPEAK_INTERVAL_MS` に基づく JST スロット（current_slot = floor(JST / interval)）
- 同一スロット内の重複送信は抑制（強制送信時を除く）
- 送信 URL は GET クエリ直付け（MicroPython の `urequests` の制限）

## 運用メモ
- `wifi_config.py` は gitignore 対象（鍵情報）
- LOW_POWER_MODE 有効時: HTTP サーバを起動せず、送信後に deep-sleep
- WebREPL は任意（`webrepl.start()`）。パスワードは適宜変更

## 開発時の注意
- PC 上の LSP で `machine`, `dht`, `urequests`, `microdot` など未解決扱いは正常（実機で解決）
- `DHT_PIN`, `USE_INTERNAL_PULLUP` の変更は `main.py` 上部の定義で調整
- 静的資産の互換ルートは削除済み。index.html は `./static/style.css`, `./static/app.js` のみ参照

## TODO/今後の拡張アイデア
- しきい値アラート（温湿度の上下限超過時にログ/通知）
- 期間統計（1h/24h の min/max/avg を別 API で提供）
- オフラインバッファ（WiFi 切断中のローカル保存→回復時にまとめ送信）
- 設定 UI（ThingSpeak ON/OFF・間隔変更）