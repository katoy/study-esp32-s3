# ESP32-S3 WebSocketリアルタイム温湿度モニター

ESP32-S3とDHT22センサーを使って、温湿度データをW### 3. ESP32-S3へのファイル転送

**🚀 推奨方法: 自動デプロイスクリプト**

高機能な自動デプロイスクリプトを使用して、効率的にファイルを転送します。

#### mpremoteツールのインストール
```bash
pip install mpremote
```

#### デプロイスクリプトの実行

**初回デプロイ（全ファイル転送）:**
```bash
python3 deploy_to_esp32.py --force
```

**差分更新（変更ファイルのみ転送）【推奨】:**
```bash
python3 deploy_to_esp32.py --verify
```

**緊急復旧（最小ファイルのみ）:**
```bash
python3 deploy_to_esp32.py --emergency
```

#### デプロイスクリプトの主要機能
- ✅ **SHA256ハッシュ比較による差分更新**
- ✅ **自動ハードウェアリセット**
- ✅ **エラー時の詳細診断メッセージ**
- ✅ **複数デバイス対応**
- ✅ **ドライラン機能**

#### コマンドオプション詳細

| オプション | 説明 | 使用例 |
|-----------|------|--------|
| `--verify, -v` | 【推奨】差分更新 | `python3 deploy_to_esp32.py --verify` |
| `--force, -f` | 全ファイル強制更新 | `python3 deploy_to_esp32.py --force` |
| `--emergency, -e` | 緊急復旧モード | `python3 deploy_to_esp32.py --emergency` |
| `--port, -p` | シリアルポート指定 | `python3 deploy_to_esp32.py -p /dev/cu.usbmodem11401` |
| `--dry-run, -n` | シミュレーション | `python3 deploy_to_esp32.py --verify --dry-run` |
| `--debug, -d` | デバッグログ | `python3 deploy_to_esp32.py --verify --debug` |
| `--no-reset` | リセット無効化 | `python3 deploy_to_esp32.py --verify --no-reset` |
| `--with-boot` | boot.py含める | `python3 deploy_to_esp32.py --verify --with-boot` |

#### 転送されるファイル
自動デプロイスクリプトは以下のファイルを転送します：

**コアシステム:**
- `main.py` - メインプログラム
- `simple_websocket.py` - WebSocketライブラリ
- `thingspeak.py` - ThingSpeak連携
- `dht22_lib.py` - DHT22制御ライブラリ
- `wifi_config.py` - WiFi設定

**WebUI:**
- `static/index.html` - メインHTML
- `static/style.css` - スタイルシート
- `static/app.js` - JavaScript

**📊 手動転送（従来の方法）**

Thonny IDEやrshellを使用する場合：

```bash
# rshellを使用
pip install rshell
rshell -p /dev/cu.usbmodem11401
> cp main.py /pyboard/
> cp wifi_config.py /pyboard/
> cp dht22_lib.py /pyboard/
```でリアルタイムにWebブラウザへ送信するプロジェクトです。

## 📋 概要

- **ESP32-S3**: WebSocketサーバーとして動作
- **DHT22センサー**: 温湿度データの取得
- **Webインターフェース**: リアルタイムグラフ表示
- **MicroPython**: ESP32-S3での実装言語
- **🚀 自動デプロイ**: 高機能なデプロイメントツール搭載

### ✨ 主要な特徴

- 🔄 **差分更新**: SHA256ハッシュ比較による効率的なファイル更新
- 🛠️ **自動リセット**: ハードウェア制御による確実なデプロイ
- 🆘 **緊急復旧**: 問題時の最小ファイル転送機能
- 📊 **詳細診断**: エラー時の包括的なトラブルシューティング
- 🔌 **複数デバイス対応**: 柔軟なポート設定とデバイス管理

## 🛠️ 必要な部品

### ハードウェア
- ESP32-S3開発ボード
- DHT22温湿度センサー
- プルアップ抵抗 10kΩ × 1個
- ブレッドボード
- ジャンパーワイヤー

### ソフトウェア
- MicroPython (ESP32-S3用)
- Thonny IDE または同等のMicroPython開発環境

## 🔌 配線図

```
ESP32-S3        DHT22
--------        -----
GPIO4    -----> DATA
3.3V     -----> VCC
GND      -----> GND

プルアップ抵抗 10kΩ を DATA - VCC 間に接続
```

## 📥 インストール手順

### 1. MicroPythonのインストール

1. [MicroPython公式サイト](https://micropython.org/download/esp32/)からESP32-S3用ファームウェアをダウンロード
2. ESP32-S3をUSBケーブルでPCに接続
3. ファームウェアを書き込み：

```bash
# esptoolを使用する場合
esptool.py --chip esp32s3 --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp32s3 --port /dev/ttyUSB0 write_flash -z 0x0 firmware.bin
```

### 2. プロジェクトファイルのセットアップ

1. このリポジトリをクローンまたはダウンロード
2. WiFi設定ファイルを作成：

```bash
cp wifi_config.template.py wifi_config.py
```

3. `wifi_config.py` を編集してWiFi認証情報を設定：

```python
WIFI_SSID = "あなたのWiFi名"
WIFI_PASSWORD = "あなたのWiFiパスワード"
```

### 3. ESP32-S3へのファイル転送

Thonny IDEまたはrshellを使用して以下のファイルをESP32-S3に転送：

- `main.py` - メインプログラム
- `wifi_config.py` - WiFi設定
- `dht22_lib.py` - DHT22制御ライブラリ
- `boot.py` - ブート時設定（オプション）

## 🚀 使用方法

### 1. ESP32-S3へのデプロイ

**自動デプロイ（推奨）:**
```bash
# 初回または全ファイル更新
python3 deploy_to_esp32.py --force

# 日常的な差分更新
python3 deploy_to_esp32.py --verify

# 動作確認（シミュレーション）
python3 deploy_to_esp32.py --verify --dry-run
```

**デプロイ成功時の出力例:**
```
🚀 ESP32-S3 MicroPython デプロイメントツール
📱 対象デバイス: /dev/cu.usbmodem11401
🔍 更新モード: 差分更新（変更ファイルのみ）
[RESET] ESP32をハードウェアリセット中...
[OK] デバイスが応答しました
[SKIP] :main.py (変更なし)
[UPDATE] static/style.css -> :static/style.css
📊 アップロード結果: 1個アップロード, 7個スキップ
✅ デプロイメント完了！
```

### 2. ESP32-S3の起動

1. 配線を確認
2. ESP32-S3をUSBでPCに接続
3. 自動デプロイでファイルを転送
4. ESP32-S3が自動的に`main.py`を実行

### 2. WebSocketサーバーの確認

起動すると以下のような出力が表示されます：

```
🚀 ESP32-S3 WebSocketサーバー開始
WiFi接続中: YourWiFiName
✅ WiFi接続成功
   IP: 192.168.1.100
✅ DHT22/DHT11センサー初期化成功
🌐 WebSocketサーバー開始: ws://192.168.1.100:80/
📱 Webページ: http://192.168.1.100:80/
```

### 3. Webブラウザでのアクセス

1. 表示されたIPアドレスにブラウザでアクセス
   - 例: `http://192.168.1.100`

2. リアルタイム温湿度モニターページが表示されます

## 📊 機能

### WebSocketサーバー機能
- ✅ HTTPリクエスト処理（HTMLページ配信）
- ✅ WebSocketハンドシェイク
- ✅ 複数クライアント同時接続対応
- ✅ 自動切断検出とクリーンアップ

### センサー機能
- ✅ DHT22/DHT11自動検出
- ✅ エラーハンドリングと再試行
- ✅ データ妥当性チェック
- ✅ 読み取り間隔制御

### Web画面機能
- 🌡️ リアルタイム温度表示
- 💧 リアルタイム湿度表示
- 📈 時系列グラフ（Chart.js使用）
- 🔌 接続状態表示
- ⚠️ エラー表示

### 快適度表示機能（拡張可能）
- 🌟 体感温度（Heat Index）
- 📊 不快指数（Discomfort Index）
- 🎯 快適度レベル（1-5段階）
- 💡 推奨行動アドバイス
- 🏠 室内環境アラート

## 📁 ファイル構成

```
websocket2/
├── main.py                     # メインプログラム
├── simple_websocket.py         # WebSocketサーバーライブラリ
├── thingspeak.py              # ThingSpeak連携ライブラリ
├── dht22_lib.py               # DHT22制御ライブラリ
├── wifi_config.template.py    # WiFi設定テンプレート
├── wifi_config.py             # WiFi設定（作成必要）
├── boot.py                    # ブート設定（オプション）
├── deploy_to_esp32.py         # 🚀 自動デプロイスクリプト
├── deploy_to_esp32_refactored.py  # リファクタリング版
├── dht_diagnose.py           # センサー診断ツール
├── dht22_simple.py           # シンプルなセンサー読み取り例
├── static/                    # Webファイル
│   ├── index.html            # メインHTML
│   ├── style.css             # スタイルシート
│   └── app.js                # JavaScript
└── README.md                 # このファイル
```

### 🚀 主要コンポーネント

**ESP32転送ファイル（自動デプロイ対象）:**
- `main.py` - システムメイン（WebSocket + DHT22）
- `simple_websocket.py` - 軽量WebSocketライブラリ
- `thingspeak.py` - IoTクラウド連携
- `dht22_lib.py` - 温湿度センサー制御
- `wifi_config.py` - WiFi認証設定
- `static/*` - Webユーザーインターフェース

**開発・運用ツール:**
- `deploy_to_esp32.py` - **高機能デプロイツール**
- `dht_diagnose.py` - センサー診断・デバッグ
- `dht22_simple.py` - センサー動作確認用

## 🔧 カスタマイズ

### センサー設定の変更

`main.py` の設定部分を編集：

```python
# 設定
DHT_PIN = 4              # センサー接続ピン
WEBSOCKET_PORT = 80      # WebSocketポート
READ_INTERVAL_SEC = 2    # データ読み取り間隔（秒）
```

### プルアップ抵抗設定

`dht22_lib.py` で内蔵プルアップを使用する場合：

```python
dht_controller = DHT22Controller(pin=4, use_pullup=True)
```

## 🐛 トラブルシューティング

### デプロイ関連エラー

**`mpremote: failed to access /dev/cu.usbmodem*`**
```bash
# デバイス一覧を確認
ls -la /dev/cu.usbmodem*

# 他のアプリケーション（Thonny等）を終了
ps aux | grep -i thonny

# デバイスの再接続
```

**`could not enter raw repl`**
```bash
# 手動リセット
# 1. BOOTボタンを押しながらRSTボタンを押して離す
# 2. BOOTボタンを離す

# スクリプトで自動復旧
python3 deploy_to_esp32.py --emergency
```

**`ファイル転送エラー - 詳細診断と対処法`**

デプロイスクリプトは失敗時に詳細な診断情報を表示します：
- エラー分類と対処法
- 推奨コマンド
- 診断手順

### WiFi接続エラー
```
❌ WiFi接続失敗
```
**解決方法:**
- SSID/パスワードの確認
- 2.4GHz帯WiFiの使用確認
- 電波強度の確認

### センサー読み取りエラー
```
❌ センサー読み取りエラー: OSError: [Errno 110] ETIMEDOUT
```
**解決方法:**
- 配線の確認（特にプルアップ抵抗）
- センサーの電源確認
- 配線の長さ確認（短くする）

### WebSocket接続エラー
```
❌ WebSocket切断
```
**解決方法:**
- ネットワーク接続確認
- ファイアウォール設定確認
- ESP32-S3のメモリ使用量確認

### ブラウザでページが表示されない

1. ESP32-S3のIPアドレスを確認
2. 同じネットワークに接続されているか確認
3. ポート80がブロックされていないか確認

## 📈 データ形式

### WebSocketで送信されるJSON形式

**正常データ:**
```json
{
  "temperature": 25.6,
  "humidity": 65.2,
  "timestamp": 1640995200
}
```

**エラーデータ:**
```json
{
  "error": "センサー読み取りエラー: OSError: [Errno 110] ETIMEDOUT"
}
```

## 🌡️ 快適度指数の算出

温度と湿度から様々な快適度指数を計算できます。以下は主要な指数の算出方法です。

### 1. 体感温度（Heat Index）

実際の気温よりも人間が感じる温度を表す指数。

**算出式:**
```python
def calculate_heat_index(temp_c, humidity):
    """体感温度を算出（℃）"""
    # 摂氏を華氏に変換
    temp_f = temp_c * 9/5 + 32

    # Heat Index計算（Rothfusz式）
    if temp_f < 80 or humidity < 40:
        return temp_c  # 補正なし

    hi = (-42.379 +
          2.04901523 * temp_f +
          10.14333127 * humidity -
          0.22475541 * temp_f * humidity -
          0.00683783 * temp_f**2 -
          0.05481717 * humidity**2 +
          0.00122874 * temp_f**2 * humidity +
          0.00085282 * temp_f * humidity**2 -
          0.00000199 * temp_f**2 * humidity**2)

    # 華氏を摂氏に変換
    return (hi - 32) * 5/9
```

**判定基準:**
| 体感温度 | 危険度 | 状態 |
|---------|-------|------|
| ～27℃ | 安全 | 🟢 快適 |
| 27-32℃ | 注意 | 🟡 やや暑い |
| 32-39℃ | 警戒 | 🟠 暑い |
| 39-51℃ | 危険 | 🔴 非常に暑い |
| 51℃～ | 極度 | ⚫ 極めて危険 |

### 2. 不快指数（Discomfort Index）

温度と湿度の組み合わせによる不快感を数値化。

**算出式:**
```python
def calculate_discomfort_index(temp_c, humidity):
    """不快指数を算出"""
    return 0.81 * temp_c + 0.01 * humidity * (0.99 * temp_c - 14.3) + 46.3
```

**判定基準:**
| 不快指数 | 快適度 | 感覚 |
|---------|-------|------|
| ～55 | 寒い | 🥶 防寒対策必要 |
| 55-60 | 肌寒い | 🧥 上着推奨 |
| 60-65 | なんともない | 😊 快適 |
| 65-70 | 快い | 😄 最適 |
| 70-75 | 暑くない | 🙂 良好 |
| 75-80 | やや暑い | 😅 やや不快 |
| 80-85 | 暑くて汗が出る | 😰 不快 |
| 85～ | 暑くてたまらない | 🥵 非常に不快 |

### 3. 快適度レベル

総合的な環境快適度を5段階で評価。

**算出式:**
```python
def calculate_comfort_level(temp_c, humidity):
    """快適度レベルを算出（1-5）"""
    # 理想的な温度・湿度からの偏差を計算
    temp_optimal = 22.0  # 理想温度
    humidity_optimal = 50.0  # 理想湿度

    temp_dev = abs(temp_c - temp_optimal) / 10.0
    humidity_dev = abs(humidity - humidity_optimal) / 30.0

    # 総合偏差スコア
    total_dev = temp_dev + humidity_dev

    if total_dev <= 0.5:
        return 5  # 非常に快適
    elif total_dev <= 1.0:
        return 4  # 快適
    elif total_dev <= 1.5:
        return 3  # 普通
    elif total_dev <= 2.5:
        return 2  # やや不快
    else:
        return 1  # 不快
```

**快適度レベル:**
| レベル | 状態 | 説明 |
|-------|------|------|
| 5 | 🌟 非常に快適 | 理想的な環境 |
| 4 | 😊 快適 | 良好な環境 |
| 3 | 😐 普通 | 許容範囲 |
| 2 | 😕 やや不快 | 改善推奨 |
| 1 | 😵 不快 | 対策必要 |

### 4. 推奨行動

環境に応じた具体的なアクションを提案。

**算出ロジック:**
```python
def get_recommended_action(temp_c, humidity, heat_index, discomfort_index):
    """推奨行動を取得"""
    actions = []

    # 温度に基づく推奨
    if temp_c < 18:
        actions.append("🔥 暖房使用推奨")
        actions.append("🧥 防寒着着用")
    elif temp_c > 28:
        actions.append("❄️ 冷房使用推奨")
        actions.append("💧 こまめな水分補給")

    # 湿度に基づく推奨
    if humidity < 30:
        actions.append("💨 加湿器使用推奨")
        actions.append("🌊 水分補給強化")
    elif humidity > 70:
        actions.append("🌪️ 除湿器・換気推奨")
        actions.append("👕 吸湿性の良い衣類着用")

    # 体感温度に基づく推奨
    if heat_index > 32:
        actions.append("🚨 熱中症注意")
        actions.append("🏠 屋内への避難推奨")

    return actions if actions else ["😊 現在の環境は快適です"]
```

### 実装例（MicroPython）

```python
class ComfortCalculator:
    @staticmethod
    def calculate_all_indices(temp_c, humidity):
        """全指数を計算"""
        heat_index = ComfortCalculator.calculate_heat_index(temp_c, humidity)
        discomfort_index = ComfortCalculator.calculate_discomfort_index(temp_c, humidity)
        comfort_level = ComfortCalculator.calculate_comfort_level(temp_c, humidity)
        actions = ComfortCalculator.get_recommended_action(
            temp_c, humidity, heat_index, discomfort_index
        )

        return {
            "heat_index": round(heat_index, 1),
            "discomfort_index": round(discomfort_index, 1),
            "comfort_level": comfort_level,
            "recommended_actions": actions
        }
```

**WebSocket送信例:**
```json
{
  "temperature": 25.6,
  "humidity": 65.2,
  "timestamp": 1640995200,
  "comfort_data": {
    "heat_index": 26.8,
    "discomfort_index": 72.4,
    "comfort_level": 4,
    "recommended_actions": [
      "😊 現在の環境は快適です"
    ]
  }
}
```

## 🔒 セキュリティ注意事項

- `wifi_config.py` をGitリポジトリにコミットしない
- 可能であれば専用のIoT用WiFiネットワークを使用
- ファイアウォール設定でアクセス制限を検討

## 📚 参考資料

### ハードウェア・プロトコル
- [MicroPython公式ドキュメント](https://docs.micropython.org/)
- [ESP32-S3データシート](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf)
- [DHT22データシート](https://www.sparkfun.com/datasheets/Sensors/Temperature/DHT22.pdf)
- [WebSocketプロトコル RFC6455](https://tools.ietf.org/html/rfc6455)

### 快適度指数・気象学
- [Heat Index 計算式 - NOAA](https://www.weather.gov/ama/heatindex)
- [不快指数について - 気象庁](https://www.jma.go.jp/jma/kishou/know/faq/faq1.html)
- [Rothfusz Heat Index Equation](https://www.weather.gov/media/ffc/ta_htindx.PDF)
- [体感温度の科学的根拠 - 日本気象学会](https://www.metsoc.jp/)
- [室内環境の快適性指標 - 建築学会](https://www.aij.or.jp/)

### 実装参考
- [Python気象ライブラリ](https://pypi.org/project/metpy/)
- [快適度計算アルゴリズム集](https://github.com/search?q=heat+index+python)

## 🤝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🆕 更新履歴

- **v2.0.0** - 高機能デプロイツール追加
  - 🚀 自動デプロイスクリプト(`deploy_to_esp32.py`)
  - 🔍 SHA256ハッシュによる差分更新
  - 🛠️ ハードウェアリセット制御
  - 🆘 緊急復旧モード
  - 📊 詳細エラー診断
  - 💪 リトライ機能付き通信
  - ⚙️ 豊富なコマンドオプション

- **v1.0.0** - 初回リリース
  - WebSocketサーバー実装
  - DHT22センサー対応
  - リアルタイムWeb画面
  - 複数クライアント対応

## 💡 今後の改善予定

### システム機能
- [ ] HTTPS/WSS対応
- [ ] データログ機能（SDカード保存）
- [ ] アラート機能（しきい値設定）
- [ ] OTA（Over-The-Air）アップデート対応

### デプロイツール強化
- [ ] 設定ファイル対応（よく使うオプション保存）
- [ ] プロファイル機能（開発/本番環境切り替え）
- [ ] WebUI経由デプロイ機能
- [ ] バックアップ・復元機能
- [ ] ログ出力（デプロイ履歴）

### 快適度・分析機能
- [ ] 🌟 体感温度・不快指数の自動計算と表示
- [ ] 📊 快適度履歴グラフ（日/週/月）
- [ ] ⚠️ しきい値アラート（暑さ・寒さ・乾燥・湿度）
- [ ] 💡 AI推奨行動（機械学習ベース）
- [ ] 🏠 室内環境最適化提案

### UI/UX改善
- [ ] モバイル対応改善
- [ ] 設定Web UI（WiFi設定等）
- [ ] マルチ言語対応
- [ ] ダークモード対応
- [ ] 快適度ダッシュボード（カード形式表示）