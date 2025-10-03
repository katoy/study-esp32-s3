"""
ESP32-S3 WebSocketサーバー + DHT22センサー
温湿度データをWebSocketでリアルタイム配信

必要な配線:
- DHT22 DATA -> GPIO4
- DHT22 VCC -> 3.3V
- DHT22 GND -> GND
- プルアップ抵抗 10kΩ (DATA - VCC間)
"""

import machine
import network
import socket
import time
import dht
import gc
from wifi_config import WIFI_SSID, WIFI_PASSWORD
from wifi_config import THINGSPEAK_ENABLED, THINGSPEAK_API_KEY, THINGSPEAK_CHANNEL_ID, THINGSPEAK_INTERVAL_MS
from simple_websocket import SimpleWebSocket
from thingspeak import ThingSpeakClient

# 設定
DHT_PIN = 4
WEBSOCKET_PORT = 80
READ_INTERVAL_SEC = 30  # センサーデータ送信間隔（秒）
# より頻繁: 1秒, より控えめ: 5秒

def connect_wifi():
    """WiFi接続"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print(f"既にWiFi接続済み: {wlan.ifconfig()}")
        return wlan

    print(f"WiFi接続中: {WIFI_SSID}")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    timeout = 20
    while not wlan.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1
        print(".", end="")

    print()

    if wlan.isconnected():
        config = wlan.ifconfig()
        print(f"✅ WiFi接続成功")
        print(f"   IP: {config[0]}")
        print(f"   サブネット: {config[1]}")
        print(f"   ゲートウェイ: {config[2]}")
        print(f"   DNS: {config[3]}")
        return wlan
    else:
        print("❌ WiFi接続失敗")
        return None

def create_dht_sensor():
    """DHT22センサーを作成"""
    try:
        return dht.DHT22(machine.Pin(DHT_PIN))
    except Exception as e:
        print(f"DHT22センサー初期化エラー: {e}")
        # DHT11でも試してみる
        try:
            return dht.DHT11(machine.Pin(DHT_PIN))
        except Exception as e2:
            print(f"DHT11センサー初期化エラー: {e2}")
            return None

def read_sensor_data(sensor):
    """センサーデータを読み取り"""
    if not sensor:
        return {"error": "センサーが初期化されていません"}

    try:
        sensor.measure()
        temperature = sensor.temperature()
        humidity = sensor.humidity()

        # 妥当性チェック
        if temperature < -40 or temperature > 80:
            return {"error": f"温度値が範囲外: {temperature}°C"}
        if humidity < 0 or humidity > 100:
            return {"error": f"湿度値が範囲外: {humidity}%"}

        return {
            "temperature": temperature,
            "humidity": humidity,
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": f"センサー読み取りエラー: {e}"}

def log_message(message, category='general', level='info'):
    """ログメッセージを出力"""
    icons = {
        'general': '📝',
        'cloud': '☁️',
        'sensor': '🌡️',
        'network': '🌐'
    }
    icon = icons.get(category, '📝')
    print(f"{icon} {message}")

def should_send_data(current_time, interval_seconds):
    """00分00秒を基準にした時刻同期型送信判定
    
    Args:
        current_time: 現在時刻（Unix時刻）
        interval_seconds: 送信間隔（秒）
    
    Returns:
        bool: 送信タイミングの場合True
    """
    # 00分00秒からの経過時間を計算
    time_slot = int(current_time) // interval_seconds
    current_slot = time_slot * interval_seconds
    
    # 現在時刻がスロット境界の1秒以内の場合に送信
    return (current_time - current_slot) < 1.0

def main():
    """メインループ"""
    print("🚀 ESP32-S3 WebSocketサーバー開始")

    # ThingSpeak設定情報を表示
    print(f"📊 ThingSpeak設定:")
    print(f"   有効: {THINGSPEAK_ENABLED}")
    print(f"   チャンネルID: {THINGSPEAK_CHANNEL_ID}")
    print(f"   送信間隔: {THINGSPEAK_INTERVAL_MS/1000:.0f}秒")
    print(f"   API Key: {'設定済み' if THINGSPEAK_API_KEY else '未設定'}")

    # urequests モジュールの可用性チェック
    try:
        import urequests
        urequests_available = True
        print("✅ urequests モジュール利用可能")
    except ImportError:
        urequests_available = False
        print("⚠️ urequests モジュールが見つかりません。ThingSpeak機能は無効になります。")

    # WiFi接続
    wlan = connect_wifi()
    if not wlan:
        print("WiFi接続に失敗しました。プログラムを終了します。")
        return

    # センサー初期化
    sensor = create_dht_sensor()
    if sensor:
        print("✅ DHT22/DHT11センサー初期化成功")
    else:
        print("⚠️  センサー初期化失敗 - エラーデータを送信します")

    # ThingSpeakクライアント初期化
    thingspeak_client = None
    if THINGSPEAK_ENABLED and urequests_available and THINGSPEAK_API_KEY:
        try:
            thingspeak_client = ThingSpeakClient(
                api_key=THINGSPEAK_API_KEY,
                channel_id=THINGSPEAK_CHANNEL_ID,
                interval_ms=THINGSPEAK_INTERVAL_MS,
                enabled=True,
                log_func=log_message,
                api_url="https://api.thingspeak.com",
                jst_offset=9*3600,  # JST = UTC+9
                urequests_available=urequests_available
            )
            print(f"✅ ThingSpeak初期化成功 (チャンネルID: {THINGSPEAK_CHANNEL_ID})")
        except Exception as e:
            print(f"❌ ThingSpeak初期化エラー: {e}")
            thingspeak_client = None
    else:
        if not THINGSPEAK_ENABLED:
            print("ℹ️ ThingSpeak送信は無効に設定されています")
        elif not urequests_available:
            print("⚠️ ThingSpeak送信にはurequestsモジュールが必要です")
        elif not THINGSPEAK_API_KEY:
            print("⚠️ ThingSpeak API Keyが設定されていません")

    # WebSocketサーバー初期化
    ws_server = SimpleWebSocket()

    # ソケット作成
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', WEBSOCKET_PORT))
    server_socket.listen(5)
    server_socket.settimeout(1.0)  # 1秒タイムアウト

    ip = wlan.ifconfig()[0]
    print(f"🌐 WebSocketサーバー開始: ws://{ip}:{WEBSOCKET_PORT}/")
    print(f"📱 Webページ: http://{ip}:{WEBSOCKET_PORT}/")

    thingspeak_interval_sec = THINGSPEAK_INTERVAL_MS / 1000
    
    print(f"🕒 送信タイミング:")
    print(f"   Web画面: {READ_INTERVAL_SEC}秒間隔（00秒基準）")
    print(f"   ThingSpeak: {thingspeak_interval_sec:.0f}秒間隔（00秒基準）")

    try:
        while True:
            current_time = time.time()

            # 新しい接続をチェック
            try:
                conn, addr = server_socket.accept()
                print(f"新しい接続: {addr}")
                ws_server.handle_new_connection(conn)
            except OSError:
                pass  # タイムアウト - 正常

            # 既存クライアントからのフレームを処理
            ws_server.handle_client_frames()

            # ハートビート送信
            ws_server.send_heartbeat()

            # 接続維持データ送信（アイドル回避・ESP32-S3対策）
            if current_time % 8 < 0.1:  # 約8秒ごとにキープアライブ（頻度を下げる）
                ws_server.send_keepalive_data()

            # メモリ監視とクリーンアップ
            ws_server.check_memory_and_cleanup()

            # WiFi接続状態監視
            if not ws_server.check_wifi_connection():
                print("WiFi再接続が必要です - プログラムを再起動してください")
                break

            # Web画面向けデータ送信（時刻同期型）
            if should_send_data(current_time, READ_INTERVAL_SEC):
                sensor_data = read_sensor_data(sensor)
                
                # ThingSpeakステータス情報を追加
                if thingspeak_client:
                    thingspeak_status = thingspeak_client.get_status_message()
                    sensor_data['thingspeak_status'] = thingspeak_status
                else:
                    sensor_data['thingspeak_status'] = '無効'
                
                if "error" not in sensor_data:
                    print(f"📊 Web送信 温度: {sensor_data['temperature']:.1f}°C, 湿度: {sensor_data['humidity']:.1f}%")
                else:
                    print(f"❌ Web送信 {sensor_data['error']}")

                # WebSocketクライアントへのデータ送信
                ws_server.broadcast_data(sensor_data)

            # ThingSpeakへのデータ送信（時刻同期型）
            if thingspeak_client and should_send_data(current_time, thingspeak_interval_sec):
                try:
                    # 最新のセンサーデータを読み取って送信
                    sensor_data_for_thingspeak = read_sensor_data(sensor)
                    if "error" not in sensor_data_for_thingspeak:
                        thingspeak_client.send_data(sensor_data_for_thingspeak)
                        print(f"☁️ ThingSpeak送信完了 温度: {sensor_data_for_thingspeak['temperature']:.1f}°C, 湿度: {sensor_data_for_thingspeak['humidity']:.1f}%")
                    else:
                        print(f"⚠️ ThingSpeak送信スキップ: {sensor_data_for_thingspeak['error']}")
                except Exception as e:
                    print(f"⚠️ ThingSpeak送信エラー: {e}")

            # 定期的なメモリクリーンアップ（10秒ごと）
            if int(current_time) % 10 == 0 and (current_time - int(current_time)) < 0.1:
                gc.collect()
                free_mem = gc.mem_free()
                if free_mem < 50000:  # 50KB以下の場合警告
                    print(f"⚠️ 空きメモリ低下: {free_mem} bytes")

            time.sleep(0.05)  # CPU使用率を下げつつ応答性向上

    except KeyboardInterrupt:
        print("\n🛑 プログラム停止")
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
    finally:
        try:
            server_socket.close()
        except Exception:
            pass
        print("🔌 サーバー終了")

if __name__ == "__main__":
    main()