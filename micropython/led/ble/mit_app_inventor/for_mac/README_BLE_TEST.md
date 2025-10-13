# PICO_LED BLE テスト - 統合版

このドキュメントでは、`pico_led.py`を実行しているRaspberry Pi Pico W2デバイスに対するBLEテストの実行方法を説明します。

## 📁 ファイル構成

### メインプロジェクト
- `../pico_led.py` - BLEペリフェラル（サーバー）- LED制御デバイス
- `../ble_simple_peripheral.py` - 必要な依存ファイル
- `../ble_advertising.py` - 必要な依存ファイル
- `../ble_client_test.py` - MicroPython用BLEクライアント

### テストツール（統合版）
- `ble_test_integrated.py` - **自己完結型BLEテストスクリプト** ⭐
- `../README_BLE_TEST.md` - メインドキュメント

### 手動テストツール
- `BLUETILITY_MANUAL_TEST.md` - BleSee アプリ使用手順

### バックアップファイル
- `backup/run_ble_test.sh` - 旧シェルスクリプト（バックアップ）
- `backup/test_ble_python.py` - 旧Pythonテストスクリプト（バックアップ）

## 🚀 かんたん実行方法

### 1. Raspberry Pi Pico W2の準備
Raspberry Pi Pico W2で以下のファイルをアップロードして実行：
```
- pico_led.py
- ble_simple_peripheral.py
- ble_advertising.py
```

### 2. macOSでBLEテスト実行
```bash
# for_macディレクトリに移動
cd /path/to/mit_app_inventor/for_mac

# 統合テストスクリプトを実行
python3 ble_test_integrated.py
```

**それだけです！** 🎉
- 必要な依存関係は自動的にチェック・インストールされます
- デバイスのスキャンから接続・テストまで全自動で実行されます

## 🛠️ 統合スクリプトの機能

`ble_test_integrated.py` は以下の機能を1つのスクリプトに統合しています：

### 自動セットアップ
1. **システム要件チェック**
   - OS確認（macOS最適化済み）
   - Python 3.7+ バージョン確認

2. **依存関係管理**
   - `bleak` ライブラリの自動チェック
   - 不足時の自動インストール（ユーザー確認あり）

### BLEテスト実行
1. **デバイススキャン**: `PICO_LED`デバイスを検索（10秒タイムアウト）
2. **BLE接続**: 見つかったデバイスに接続
3. **サービス・特性発見**: UART サービスと特性を発見・検証
4. **初期状態確認**: 接続時に現在のLED状態を自動受信 🆕
   - デバイス側が接続検知と同時にLED状態（'1' または '0'）を送信
   - クライアント側で初期状態を確認可能
5. **LED制御テスト**: 3サイクルのLED点滅テスト
   - LED ON コマンド送信 (`b'1\x00'`)
   - 2秒待機
   - LED OFF コマンド送信 (`b'0\x00'`)
   - 2秒待機
   - 3回繰り返し
6. **通知テスト**: デバイスからの通知受信確認

## 📋 期待される動作

### コンソール出力例
```
============================================
 PICO_LED BLE Test - 統合版
============================================
[STEP] システム要件をチェック中...
[INFO] OS: Darwin
[INFO] Python: 3.11.0
[SUCCESS] システム要件OK
[STEP] 依存関係をチェック中...
[SUCCESS] bleak ライブラリが見つかりました
[STEP] PICO_LED デバイスをスキャン中...
[SUCCESS] デバイス発見: PICO_LED at AA:BB:CC:DD:EE:FF
[STEP] デバイス情報:
  デバイス名: PICO_LED
  MACアドレス: AA:BB:CC:DD:EE:FF
  サービス UUID: 6E400001-B5A3-F393-E0A9-E50E24DCCA9E
  ...
[SUCCESS] 🎉 テスト完了! PICO_LEDデバイスは正常に動作しています。
```

### 物理的な動作
- **接続時の自動状態送信** 🆕: 接続した瞬間に現在のLED状態を受信
- **GPIO16のLEDが3回点滅**（ON → OFF を3回繰り返し）  
- **各コマンド後の状態確認**: LED制御後に現在の状態を自動受信
- テスト完了時に成功メッセージ表示

### 新機能: 接続時LED状態自動送信
```
# デバイス側（pico_led.py）ログ例
Connection established. Current LED state sent: 0

# クライアント側（統合テスト）で受信
[INFO] 接続時の初期状態を受信: 0 (LED OFF)
```

## 🎯 コマンドラインオプション

```bash
# ヘルプ表示
python3 ble_test_integrated.py --help

# セットアップのみ実行（テストはスキップ）
python3 ble_test_integrated.py --setup-only

# 自動実行モード（対話なし）
python3 ble_test_integrated.py --no-interactive
```

## 🔧 トラブルシューティング

### 🔍 デバイスが見つからない場合
```
[ERROR] デバイス 'PICO_LED' が見つかりません!
```

**解決方法:**
1. ✅ Raspberry Pi Pico W2で `pico_led.py` が実行されているか確認
2. ✅ デバイス名が `PICO_LED` になっているか確認
3. ✅ Bluetooth範囲内（数メートル以内）にあるか確認
4. ✅ MacのBluetooth設定が有効になっているか確認

### 🚫 接続できない場合
```
[ERROR] デバイスへの接続に失敗しました
```

**解決方法:**
1. ✅ 他のデバイス（iPhone、Androidアプリなど）が既に接続していないか確認
2. ✅ Raspberry Pi Pico W2を再起動（電源OFF/ON）
3. ✅ しばらく待ってから再実行
4. ✅ Mac側のBluetooth設定をリセット

### ⚙️ 依存関係エラーの場合
```
[ERROR] bleak のインストールに失敗しました
```

**解決方法:**
1. ✅ インターネット接続を確認
2. ✅ 手動インストール: `pip3 install bleak`
3. ✅ Python環境の確認: `python3 --version`
4. ✅ pip の更新: `python3 -m pip install --upgrade pip`

### 💡 LEDが点滅しない場合
**Raspberry Pi Pico W2側の確認:**
1. ✅ LED_ON_COMMAND と LED_OFF_COMMAND が一致しているか
2. ✅ GPIO16番ピンの設定が正しいか
3. ✅ LEDとGNDの配線を確認
4. ✅ `pico_led.py` のコンソール出力を確認

## 🔧 手動テストオプション

GUI ツールでの手動テストについては、別ドキュメントを参照してください：
- [`BLUETILITY_MANUAL_TEST.md`](BLUETILITY_MANUAL_TEST.md) - BleSee アプリを使った手動テスト

## 📊 技術仕様

### BLE 設定
- **デバイス名**: `PICO_LED`
- **Service UUID**: `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` (Nordic UART Service)
- **RX UUID**: `6E400002-B5A3-F393-E0A9-E50E24DCCA9E` (クライアント → サーバー)
- **TX UUID**: `6E400003-B5A3-F393-E0A9-E50E24DCCA9E` (サーバー → クライアント)

### コマンド仕様
- **LED ON**: `b'1\x00'` (ASCII '1' + NULL終端)
- **LED OFF**: `b'0\x00'` (ASCII '0' + NULL終端)

### タイムアウト設定
- **スキャンタイムアウト**: 10秒
- **接続タイムアウト**: 自動管理
- **LED制御間隔**: 2秒

### 依存関係
- **Python**: 3.7以上
- **bleak**: 自動インストール対応
- **macOS**: 推奨（他OSでも動作可能）

---

## 🔄 旧バージョンとの互換性

### バックアップファイル
統合前のファイルは `for_mac/backup/` に保存されています：
- `run_ble_test.sh` - シェルラッパースクリプト
- `test_ble_python.py` - 個別Pythonテストスクリプト

### マイグレーション
旧システムから新しい統合版への移行：

```bash
# 旧バージョンを使用したい場合
cd for_mac/backup
./run_ble_test.sh

# 統合版を使用する場合（推奨）
cd ..
python3 ../ble_test_integrated.py
```

---

## 📈 パフォーマンスと信頼性

### 統合版の利点
✅ **依存関係の自動管理** - bleakライブラリの自動インストール
✅ **エラー処理強化** - 詳細なエラー情報とトラブルシューティング
✅ **ユーザビリティ向上** - 色付き出力と進捗表示
✅ **単一ファイル** - 複数ファイルの管理が不要
✅ **クロスプラットフォーム** - macOS以外でも動作

### 実行時間
- スキャン: 最大10秒
- 接続: 通常1-3秒
- テスト実行: 約20秒（3サイクル）
- 総実行時間: 約30-40秒
[STEP] Device Information:
  Device Name: PICO_LED
  MAC Address: AA:BB:CC:DD:EE:FF
[STEP] Connecting to AA:BB:CC:DD:EE:FF...
[SUCCESS] Connected to device
[STEP] Testing connection and services...
[INFO] Found RX characteristic: 6e400002-b5a3-f393-e0a9-e50e24dcca9e
[INFO] Found TX characteristic: 6e400003-b5a3-f393-e0a9-e50e24dcca9e
[SUCCESS] All required characteristics found
[STEP] Starting LED control test...
[INFO] Test cycle 1/3:
  Turning LED ON... ✓
  Turning LED OFF... ✓
[SUCCESS] All tests completed successfully!
```

---

## BleSee.app を使用した手動テスト

macOSの「BleSee」GUIアプリケーションを使用して、視覚的にBLE通信をテストできます。

### 1. BleSee のインストール

```bash
# Homebrew Cask でインストール
brew install --cask blesee
```

### 2. 手動テスト手順

#### デバイス検索と接続
1. BleSee.app を起動
2. 自動的にBLEデバイスをスキャン開始
3. 「PICO_LED」デバイスをクリック→「Connect」

#### サービス確認
1. 接続されたデバイスを展開
2. `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` (UART Service) を確認
3. RX特性: `6E400002-B5A3-F393-E0A9-E50E24DCCA9E` (Write用)
4. TX特性: `6E400003-B5A3-F393-E0A9-E50E24DCCA9E` (Notify用)

#### LED制御コマンド送信
1. **LED ON**: RX特性に `31 00` を書き込み
2. **LED OFF**: RX特性に `30 00` を書き込み

#### レスポンス確認
1. TX特性で「Subscribe」または「Notify」を有効化
2. LED制御後にレスポンスを受信:
   - LED ON後: `31` ('1')
   - LED OFF後: `30` ('0')

### 3. 詳細なマニュアル

完全な手順については `BLESEE_MANUAL_TEST.md` を参照してください。

### 4. データ形式

| 操作 | 送信データ (16進) | 送信データ (BleSee形式) |
|------|-------------------|------------------------|
| LED ON | 0x31 0x00 | 31 00 |
| LED OFF | 0x30 0x00 | 30 00 |