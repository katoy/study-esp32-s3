# main.py - ESP32-S3 DHT22 環境モニター

# ===== インポート =====
import time
import gc
import sys
try:
    import _thread
except Exception:
    _thread = None
from microdot import Microdot, Response

# --- ローカルモジュール ---
from sensor_manager import SensorManager
from thingspeak import ThingSpeakClient
from web_routes import register_routes
from websocket_server import WebSocketServer

# ===== 定数設定 =====
# --- 時間関連 ---
JST_OFFSET_SEC = 9 * 3600

# --- ハードウェア関連 ---
DHT_PIN = 4
USE_INTERNAL_PULLUP = False

# --- ネットワーク関連 ---
WS_PORT = 80
WEBREPL_PASSWORD = "esp32s3"

# --- サービス関連 ---
THINGSPEAK_API_URL = "https://api.thingspeak.com"

# --- アプリケーション設定 ---
MAX_HISTORY_SIZE = 100
MAX_LOG_SIZE = 50
VALID_TEMP_RANGE = (-40, 80)
VALID_HUM_RANGE = (0, 100)

# ===== グローバルコンテキスト =====
# アプリケーション全体で共有するオブジェクトと設定
context = {
    'boot_time': time.time(),
    'system_logs': [],
    'urequests_available': False,
    'config': {
        'JST_OFFSET_SEC': JST_OFFSET_SEC,
        'DHT_PIN': DHT_PIN,
        'USE_INTERNAL_PULLUP': USE_INTERNAL_PULLUP,
        'WS_PORT': WS_PORT,
        'MAX_HISTORY_SIZE': MAX_HISTORY_SIZE,
        'VALID_TEMP_RANGE': VALID_TEMP_RANGE,
        'VALID_HUM_RANGE': VALID_HUM_RANGE,
    }
}

# ===== ユーティリティ関数 =====
def log_message(message, category='general', level='info'):
    timestamp = format_jst_time()
    log_entry = {'timestamp': timestamp, 'category': category, 'level': level, 'message': message}
    context['system_logs'].append(log_entry)
    if len(context['system_logs']) > MAX_LOG_SIZE:
        context['system_logs'].pop(0)
    print(f"[{timestamp}] [{level.upper()}] [{category.upper()}] {message}")

def format_jst_time(unix_ts=None):
    try:
        if unix_ts is None: unix_ts = time.time()
        jst_ts = unix_ts + JST_OFFSET_SEC
        t = time.localtime(jst_ts)
        return f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d} JST"
    except Exception:
        return "----/--/-- --:--:-- JST"

# コンテキストに関数を追加
context['log_message'] = log_message
context['format_jst_time'] = format_jst_time

# ===== 初期化処理 =====
print("=" * 50)
log_message("メインプログラム開始", "system", "info")
print("=" * 50)

try:
    import urequests
    context['urequests_available'] = True
    log_message("urequestsライブラリを検出しました。", "system", "info")
except ImportError:
    log_message("urequestsライブラリが見つかりません。", "system", "warning")

try:
    from wifi_config import WIFI_SSID, WIFI_PASSWORD, WIFI_HOSTNAME
    # TODO: WiFi接続処理をここに実装
except ImportError:
    log_message("wifi_config.py が見つかりません。", "config", "warning")

try:
    from wifi_config import THINGSPEAK_ENABLED, THINGSPEAK_API_KEY, THINGSPEAK_CHANNEL_ID, THINGSPEAK_INTERVAL_MS, LOW_POWER_MODE
    log_message("wifi_config.py からThingSpeak設定を読み込みました。", "config", "info")
except ImportError:
    log_message("ThingSpeak設定が見つかりません。デフォルト値を使用します。", "config", "warning")
    THINGSPEAK_ENABLED, THINGSPEAK_API_KEY, THINGSPEAK_CHANNEL_ID, THINGSPEAK_INTERVAL_MS, LOW_POWER_MODE = False, "", "", 60000, False

# --- オブジェクトのインスタンス化 ---
context['sensor_manager'] = SensorManager(
    pin=DHT_PIN, 
    use_internal_pullup=USE_INTERNAL_PULLUP, 
    log_func=log_message,
    valid_temp_range=VALID_TEMP_RANGE,
    valid_hum_range=VALID_HUM_RANGE,
    max_history_size=MAX_HISTORY_SIZE
)

# WebSocketサーバーを作成してセンサーマネージャーに接続
websocket_server = WebSocketServer(log_message)
context['sensor_manager'].set_websocket_server(websocket_server)
context['websocket_server'] = websocket_server

thingspeak_client = ThingSpeakClient(
    api_key=THINGSPEAK_API_KEY, channel_id=THINGSPEAK_CHANNEL_ID, interval_ms=THINGSPEAK_INTERVAL_MS,
    enabled=THINGSPEAK_ENABLED, log_func=log_message, api_url=THINGSPEAK_API_URL,
    jst_offset=JST_OFFSET_SEC, urequests_available=context['urequests_available']
)

app = Microdot()
Response.default_content_type = 'text/html; charset=utf-8'
register_routes(app, context)

try:
    import webrepl
    webrepl.start(password=WEBREPL_PASSWORD)
    log_message(f"WebREPLが起動しました。", "network", "info")
except ImportError:
    log_message("webreplモジュールは無効です。", "network", "warning")

print("=" * 50)
log_message(f"初期メモリ空き容量: {gc.mem_free()} bytes", "system", "debug")

# ===== メイン処理 =====
def main():
    log_message("HTTPサーバーを起動します...", "http", "info")
    
    initial_data = context['sensor_manager'].read_with_retry()
    if initial_data:
        log_message(f"初回データ取得成功: {initial_data['temperature']:.1f}°C, {initial_data['humidity']:.1f}%", "sensor", "info")
        thingspeak_client.send_data(initial_data)
    else:
        log_message("初回センサー読み取りに失敗しました。", "sensor", "warning")

    if _thread and THINGSPEAK_ENABLED:
        try:
            _thread.start_new_thread(thingspeak_client.background_worker, (context['sensor_manager'],))
        except Exception as e:
            log_message(f"バックグラウンドスレッドの起動に失敗: {e}", "cloud", "error")

    if LOW_POWER_MODE:
        log_message("低電力モードは現在サポートされていません。", "system", "warning")
    else:
        try:
            # WebSocket対応サーバーを起動
            run_websocket_server(app, websocket_server, WS_PORT)
        except Exception as e:
            log_message(f"Webサーバーの実行中に致命的なエラー: {e}", "http", "critical")

def run_websocket_server(app, websocket_server, port):
    """WebSocket対応の統合サーバーを実行"""
    import socket
    
    log_message(f"WebSocket対応サーバーを開始 (port: {port})", "http", "info")
    
    # サーバーソケットを作成
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(5)
    
    log_message("HTTPサーバーが起動しました。WebSocket接続を待機中...", "http", "info")
    
    while True:
        try:
            # 新しいクライアント接続を受け入れ
            client_socket, addr = server_socket.accept()
            log_message(f"新しいクライアント接続: {addr}", "http", "debug")
            
            # リクエストデータを受信
            request_data = client_socket.recv(1024)
            if not request_data:
                client_socket.close()
                continue
                
            # WebSocketアップグレード要求かチェック
            request_str = request_data.decode('utf-8', errors='ignore')
            
            if 'Upgrade: websocket' in request_str and '/ws' in request_str:
                # WebSocketアップグレード処理
                if websocket_server.handle_websocket_upgrade(request_data, client_socket):
                    log_message(f"WebSocketアップグレード成功: {addr}", "websocket", "info")
                    # WebSocketクライアントは別スレッドで処理
                    if _thread:
                        _thread.start_new_thread(handle_websocket_client, (client_socket, websocket_server))
                    else:
                        client_socket.close()
                else:
                    client_socket.close()
            else:
                # 通常のHTTP要求をmicrodotで処理
                handle_http_request(client_socket, request_data, app)
                
        except Exception as e:
            log_message(f"サーバー処理でエラー: {e}", "http", "error")
            
def handle_websocket_client(client_socket, websocket_server):
    """WebSocketクライアントメッセージを処理"""
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            
            # WebSocketメッセージを処理
            if not websocket_server.handle_websocket_message(client_socket, data):
                break  # クライアント切断
                
    except Exception as e:
        log_message(f"WebSocketクライアント処理エラー: {e}", "websocket", "error")
    finally:
        websocket_server.remove_client(client_socket)

def handle_http_request(client_socket, request_data, app):
    """通常のHTTP要求をmicrodotで処理"""
    try:
        # 簡単なHTTP応答処理 (microdotの内部処理を模倣)
        request_str = request_data.decode('utf-8', errors='ignore')
        lines = request_str.split('\r\n')
        if lines:
            method_line = lines[0]
            parts = method_line.split(' ')
            if len(parts) >= 2:
                method, path = parts[0], parts[1]
                
                # 簡単なリクエストオブジェクトを作成
                class SimpleRequest:
                    def __init__(self, method, path):
                        self.method = method
                        self.path = path
                        self.args = {}
                        
                request = SimpleRequest(method, path)
                
                response = None
                # ルートマッチング (簡単な実装)
                for (route_method, route_pattern), (handler, param_names) in app._routes:
                    if method == route_method and matches_route(path, route_pattern, param_names):
                        try:
                            response = handler(request)
                            break
                        except Exception as e:
                            log_message(f"ルートハンドラーエラー: {e}", "http", "error")
                
                # 応答を送信
                if response:
                    send_http_response(client_socket, response)
                else:
                    send_404_response(client_socket)
    except Exception as e:
        log_message(f"HTTP要求処理エラー: {e}", "http", "error")
    finally:
        try:
            client_socket.close()
        except Exception:
            pass

def matches_route(path, pattern_parts, param_names):
    """簡単なルートマッチング"""
    path_parts = [p for p in path.split('/') if p]
    
    if len(path_parts) != len(pattern_parts):
        return False
    
    for i, (path_part, pattern_part) in enumerate(zip(path_parts, pattern_parts)):
        if pattern_part.startswith('<') and pattern_part.endswith('>'):
            continue  # パラメータは何でもマッチ
        elif path_part != pattern_part:
            return False
    
    return True

def send_http_response(client_socket, response):
    """HTTP応答を送信"""
    try:
        status_line = f"HTTP/1.1 {response.status_code} OK\r\n"
        
        headers = []
        if hasattr(response, 'headers') and response.headers:
            for key, value in response.headers.items():
                headers.append(f"{key}: {value}\r\n")
        
        if 'Content-Type' not in (response.headers or {}):
            headers.append(f"Content-Type: {response.default_content_type}\r\n")
        
        headers.append("Connection: close\r\n")
        headers.append("\r\n")
        
        # ヘッダー送信
        client_socket.send(status_line.encode())
        for header in headers:
            client_socket.send(header.encode())
            
        # ボディ送信
        if hasattr(response, 'body') and response.body:
            if isinstance(response.body, str):
                client_socket.send(response.body.encode())
            else:
                client_socket.send(response.body)
                
    except Exception as e:
        log_message(f"HTTP応答送信エラー: {e}", "http", "error")

def send_404_response(client_socket):
    """404応答を送信"""
    try:
        response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n<h1>404 Not Found</h1>"
        client_socket.send(response.encode())
    except Exception:
        pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("ユーザーの操作によりプログラムを停止します。", "system", "info")
    finally:
        log_message("プログラムを終了します。", "system", "info")
        gc.collect()
