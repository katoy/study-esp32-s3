# wifi_config.template.py
# WiFi接続設定テンプレートファイル
#
# 使用方法:
# 1. このファイルを wifi_config.py にコピーまたはリネーム
# 2. 実際の認証情報に置き換える
# 3. wifi_config.py は .gitignore に追加して機密情報を保護する

# ===== WiFi接続設定 =====
WIFI_SSID = "YOUR_WIFI_SSID"              # あなたのWiFi SSID名に置き換えてください
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"       # あなたのWiFiパスワードに置き換えてください
WIFI_HOSTNAME = "esp32s3-ws"           # ESP32のホスト名（任意変更可能）

# ===== ThingSpeak設定 =====
THINGSPEAK_ENABLED = False                                    # ThingSpeak送信の有効/無効
THINGSPEAK_API_KEY = "YOUR_THINGSPEAK_WRITE_API_KEY"         # Write API Key（下記手順で取得）
THINGSPEAK_CHANNEL_ID = "YOUR_CHANNEL_ID"                    # Channel ID（数字）
THINGSPEAK_INTERVAL_MS = 300000                               # 送信間隔（ミリ秒、5分。無料プラン最小15秒以上）

# ===== 省電力モード設定 =====
# True の場合、HTTPサーバーを起動せず、ThingSpeak の送信スロットに合わせて起動→測定→送信→ディープスリープを繰り返します。
# UIアクセスが不要なバッテリー運用向けです。
LOW_POWER_MODE = False

# ===== ThingSpeak設定手順 =====
# 1. https://thingspeak.com/ でアカウント作成
# 2. 新しいチャンネルを作成
# 3. Field 1: Temperature (°C), Field 2: Humidity (%) と設定
# 4. API Keys タブから Write API Key をコピー
# 5. 上記のTHINGSPEAK_API_KEYに貼り付け
# 6. Channel Settings の Channel ID を THINGSPEAK_CHANNEL_ID に設定
# 7. THINGSPEAK_ENABLED を True に変更

# ===== 使用例 =====
# main.py での使用方法:
# from wifi_config import WIFI_SSID, WIFI_PASSWORD, WIFI_HOSTNAME
# from wifi_config import THINGSPEAK_ENABLED, THINGSPEAK_API_KEY, THINGSPEAK_CHANNEL_ID, THINGSPEAK_INTERVAL_MS

# ===== セキュリティ注意事項 =====
# - wifi_config.py は機密情報を含むため、Gitリポジトリにコミットしないでください
# - .gitignore に wifi_config.py を追加することを強く推奨します
# - 本番環境では環境変数の使用も検討してください

# ===== 設定例（コメントアウト済み） =====
# WIFI_SSID = "MyHomeWiFi"
# WIFI_PASSWORD = "MySecurePassword123"
# WIFI_HOSTNAME = "esp32s3-sensor01"
#
# THINGSPEAK_ENABLED = True
# THINGSPEAK_API_KEY = "ABCD1234EFGH5678"
# THINGSPEAK_CHANNEL_ID = "1234567"
# THINGSPEAK_INTERVAL_MS = 30000  # 30秒間隔