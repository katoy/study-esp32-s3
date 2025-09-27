# ESP32-S3 DHT22 Environmental Monitor

Thonny IDE 対応の MicroPython IoT 環境監視システム。ESP32-S3 + DHT22 で温湿度を計測し、HTTP API でフロントエンドに配信します。NTP による JST 時刻、ThingSpeak 連携（JST スロット整列）、軽量 UI（app.js / style.css のみ）を備えています。

## 目次

- [ESP32-S3 DHT22 Environmental Monitor](#esp32-s3-dht22-environmental-monitor)
  - [目次](#目次)
  - [主な機能](#主な機能)
  - [ファイル構成（要点）](#ファイル構成要点)
  - [セットアップ（Thonny）](#セットアップthonny)
  - [WiFi 設定](#wifi-設定)
  - [ハードウェア配線（DHT22/AM2302）](#ハードウェア配線dht22am2302)
  - [実行](#実行)
  - [デプロイ（ESP32 再配置スクリプト）](#デプロイesp32-再配置スクリプト)
    - [要件](#要件)
    - [主な機能](#主な機能-1)
    - [使い方（例）](#使い方例)
    - [クリーンアップ仕様](#クリーンアップ仕様)
    - [典型的なエラーと対処](#典型的なエラーと対処)
  - [API（現行実装）](#api現行実装)
  - [ThingSpeak 連携（オプション）](#thingspeak-連携オプション)
  - [トラブルシューティング](#トラブルシューティング)
  - [ライセンス / 貢献](#ライセンス--貢献)

## 主な機能

- リアルタイム監視: DHT22（温度・湿度）を HTTP API で配信（30s 目安、整列可能）
- 正確な時刻: NTP 同期の JST タイムスタンプ
- クラウド連携: ThingSpeak へ自動送信（既定 1 分、JST スロット整列）
- 統計/トレンド: 最小/最大/平均、増減トレンド、快適性指標（体感温度など）
- 診断と堅牢性: 安定化待ち、リトライ、センサー再初期化、システムログ API
- 軽量 UI: `static/app.js` と `static/style.css` のみ（フォールバックや互換ルートなし）

## ファイル構成（要点）

```
📁 ルート/
├─ main.py                     # メイン（HTTPサーバ & センサー制御）
├─ boot.py                     # 起動スクリプト（任意）
├─ wifi_config.py              # WiFi/ThingSpeak 設定（必須）
├─ wifi_config.example.py      # 設定テンプレート
├─ index.html                  # UI
├─ manifest.json               # PWA 設定
├─ static/
│   ├─ app.js                  # フロントロジック（一本化）
│   └─ style.css               # スタイル（一本化）
├─ lib/                        # 追加ライブラリ（任意）
└─ memo.md                     # 開発メモ
```

## セットアップ（Thonny）

1) Thonny をインストール: https://thonny.org/

2) Interpreter を MicroPython (ESP32) に設定し、ESP32-S3 と接続（適切なシリアルポートを選択）。

3) 必須ファイルを ESP32 にアップロード:
- `main.py`, `wifi_config.py`, `index.html`, `manifest.json`, `static/app.js`, `static/style.css`

4) ライブラリ（必要な場合）:
- 本プロジェクトは標準 MicroPython + `microdot` で動作します。
- `from microdot import Microdot, Response` を使用しているため、未導入なら以下を実行:
  ```python
  import upip
  upip.install('microdot')
  ```

## WiFi 設定

テンプレートから作成します。

```
cp wifi_config.example.py wifi_config.py
# wifi_config.py を編集して SSID / パスワード / ThingSpeak 設定を記入
```

## ハードウェア配線（DHT22/AM2302）

- VCC → ESP32 3.3V
- GND → ESP32 GND
- DATA → ESP32 GPIO4（推奨）
- DATA と VCC 間に 4.7kΩ〜10kΩ の外付けプルアップ抵抗（必須）

注意: ETIMEDOUT の典型原因はプルアップ不足です。`USE_INTERNAL_PULLUP = False` が既定（外付け推奨）。

## 実行

1) ESP32 を接続し、Thonny で `main.py` を実行
2) ブラウザで `http://<ESP32のIP>/` にアクセス

## デプロイ（ESP32 再配置スクリプト）

`deploy_to_esp32.py` は mpremote を使って、ESP32 に「必要ファイルだけ」を再配置し、不要ファイルを残さないようにクリーンアップするツールです。ポート指定がある場合は自動的に `mpremote connect <PORT>` を前置して実行します。

### 要件
- ホストPCに `mpremote` がインストールされていること

### 主な機能
- 必要ファイルのみアップロード（`main.py`, `wifi_config.py`, `index.html`, `manifest.json`, `static/app.js`, `static/style.css`）
- `/static` の不要資産を削除（`app.js` と `style.css` 以外は削除）
- `microdot` が未導入なら `mip install microdot` を実行
- 任意でルート直下の不要ファイルを削除（`--strict`）
- 忙しい/不安定なときに備えたリトライ（回数・待ち時間は可変）
- 差分更新（`--verify`）: 変更があるファイルのみを転送（ハッシュ比較）
- 強制更新（`--force`）: すべての対象ファイルを再転送

### 使い方（例）

```zsh
# 最小構成で再配置（boot.py は配布しない）
python3 deploy_to_esp32.py --port /dev/tty.usbmodem1101

# boot.py も配布したい場合
python3 deploy_to_esp32.py --port /dev/tty.usbmodem1101 --with-boot

# 失敗しても他のファイルは続行
python3 deploy_to_esp32.py --port /dev/tty.usbmodem1101 --keep-going

# ルート直下もクリーンアップ（確認スキップ）
python3 deploy_to_esp32.py --port /dev/tty.usbmodem1101 --strict --yes

# 接続が不安定な場合のリトライ強化（5回、待ち3秒）
python3 deploy_to_esp32.py --port /dev/tty.usbmodem1101 --retries 5 --retry-wait 3

# ドライラン（実行せず計画のみ表示）
python3 deploy_to_esp32.py --dry-run
```

ポート名は環境により異なります（macOS では `/dev/tty.usbmodemXXXX` や `/dev/cu.usbserial-XXXX` など）。

補足:
- 疎通チェック: スクリプト実行時に簡易的な疎通チェックを行います。失敗時は Thonny の占有やデバイスのリセットを案内します。
- ポート指定なしでも動作しますが、複数デバイス接続環境では `--port` の明示指定を推奨します。

### クリーンアップ仕様
- `/static`: `app.js`, `style.css` 以外は削除
- ルート（`--strict` 指定時）: 以下の allowlist 以外は削除対象（ディレクトリは削除しない）
  - `main.py`, `index.html`, `manifest.json`, `wifi_config.py`, `static`, `lib`, `webrepl.py`, `webrepl_cfg.py`

### 典型的なエラーと対処
- `could not enter raw repl`（raw REPL に入れない）
  - Thonny がポートを占有していないか確認（Stop/Restart backend / Thonny を閉じる）
  - ESP32 の EN リセットや USB 抜き差しを実施
  - `--retries` と `--retry-wait` を増やして再試行

## API（現行実装）

HTTP ベース（WebSocket は未使用）。

- GET `/` → index.html
- GET `/static/app.js`, `/static/style.css` → 静的ファイル
- GET `/manifest.json` → PWA マニフェスト
- GET `/health` → ヘルスチェック（メモリ/稼働/センサー）
- GET `/config` → 設定（ThingSpeak 設定の有無など）
- GET `/api/realtime` → 最新データ（安定化リトライ付き）
- GET `/api/data` → センサー読み取り（失敗時は前回データを返却）
- GET `/api/logs` → システムログ（カテゴリ/レベル/limit でフィルタ）
- GET `/api/system` → システム情報（メモリ/uptime/履歴件数）

データ例（`/api/realtime`）:
```json
{
  "type": "dht11",
  "temp_c": 25.0,
  "hum_pct": 60.0,
  "timestamp": "2025-09-27 12:34:56 JST",
  "measurement_count": 42
}
```
備考: `type` はレガシー互換のため "dht11" 固定ですが、実センサーは DHT22 です。

## ThingSpeak 連携（オプション）

`wifi_config.py` 例:
```python
THINGSPEAK_ENABLED = True
THINGSPEAK_API_KEY = "YOUR_WRITE_API_KEY"
THINGSPEAK_CHANNEL_ID = "YOUR_CHANNEL_ID"
THINGSPEAK_INTERVAL_MS = 60000  # 1分
```
- JST のスロット境界（間隔の倍数秒）で自動送信（重複抑制）
- 失敗しても UI/計測は継続、ログに記録

## トラブルシューティング

- センサー ETIMEDOUT: 外付けプルアップ（4.7k〜10kΩ）を追加／配線確認
- 画面が更新されない: ブラウザ強制リロード（Cmd+Shift+R）
- WiFi 接続失敗: `wifi_config.py` の SSID/パスワードを確認
- ThingSpeak 失敗: API 設定と送信間隔（≥15 秒）を確認
- メモリ不足: 不要ログ削減、再起動

## ライセンス / 貢献

MIT License。Issue/PR/提案歓迎です。

—

開発環境: Thonny IDE + MicroPython on ESP32-S3
推奨 ESP32: ESP32-S3-DevKitC-1
センサー: DHT22/AM2302
最終更新: 2025年9月28日