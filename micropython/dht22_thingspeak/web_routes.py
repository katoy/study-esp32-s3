# web_routes.py - Web server routes for the DHT22 monitor

from microdot import Response
import ujson as json
import gc
import sys
import time

def register_routes(app, context):

    # --- コンテキストからオブジェクトを取得 ---
    sensor_manager = context['sensor_manager']
    log_message = context['log_message']
    format_jst_time = context['format_jst_time']
    boot_time = context['boot_time']
    system_logs = context['system_logs']
    config = context['config']

    @app.route('/')
    def index(request):
        try:
            with open('index.html', 'r', encoding='utf-8') as f:
                return Response(f.read())
        except Exception as e:
            log_message(f"index.htmlの読み込みに失敗しました: {e}", "http", "error")
            return Response("<h1>Error</h1><p>index.htmlが見つかりません。</p>", status_code=500)

    @app.route('/manifest.json')
    def manifest(request):
        try:
            with open('manifest.json', 'r', encoding='utf-8') as f:
                return Response(f.read(), headers={'Content-Type': 'application/json'})
        except Exception as e:
            log_message(f"manifest.jsonの読み込みに失敗しました: {e}", "http", "error")
            return Response('Not found', status_code=404)

    @app.route('/static/<path:path>')
    def static(request, path):
        if '..' in path:
            return Response('Not found', status_code=404)
        try:
            content_type = 'text/plain'
            if path.endswith('.css'):
                content_type = 'text/css'
            elif path.endswith('.js'):
                content_type = 'application/javascript'
            with open('static/' + path, 'r', encoding='utf-8') as f:
                return Response(f.read(), headers={'Content-Type': content_type})
        except Exception as e:
            log_message(f"静的ファイル {path} の読み込みに失敗: {e}", "http", "error")
            return Response('Not found', status_code=404)

    @app.route('/api/data')
    def api_data(request):
        try:
            data = sensor_manager.read_with_retry()
            if data:
                # タイムスタンプを付与して返す
                data['timestamp'] = format_jst_time(data['unix_time'])
                return Response(json.dumps(data), headers={'Content-Type': 'application/json'})
            else:
                if sensor_manager.last_sensor_data:
                    # タイムスタンプを付与して返す
                    last_data = sensor_manager.last_sensor_data
                    last_data['timestamp'] = format_jst_time(last_data['unix_time'])
                    return Response(json.dumps(last_data), headers={'Content-Type': 'application/json'})
                else:
                    raise Exception("センサーの読み取りに繰り返し失敗しました。")
        except Exception as e:
            log_message(f"API /api/data でエラー: {e}", "api", "error")
            error_data = {'error': str(e), 'timestamp': format_jst_time(), 'status': 'error'}
            return Response(json.dumps(error_data), status_code=500, headers={'Content-Type': 'application/json'})

    @app.route('/api/realtime')
    def api_realtime(request):
        try:
            # センサーから最新値を取得（失敗時は直近の正常値を返す）
            data = sensor_manager.read_with_retry()
            if not data and sensor_manager.last_sensor_data:
                data = sensor_manager.last_sensor_data

            if data:
                payload = {
                    'type': 'dht11',  # レガシー互換（UI 側仕様）
                    'temp_c': float(data.get('temperature')),
                    'hum_pct': float(data.get('humidity')),
                    'timestamp': format_jst_time(data.get('unix_time')),
                    'measurement_count': int(data.get('measurement_count', 0))
                }
                return Response(json.dumps(payload), headers={'Content-Type': 'application/json'})
            else:
                raise Exception('センサー読み取りに失敗し、有効な直近データもありません。')
        except Exception as e:
            log_message(f"API /api/realtime でエラー: {e}", "api", "error")
            return Response(json.dumps({'error': str(e), 'timestamp': format_jst_time()}), status_code=500, headers={'Content-Type': 'application/json'})

    @app.route('/api/system')
    def api_system(request):
        try:
            gc.collect()
            info = {
                'memory_free': gc.mem_free(),
                'memory_alloc': gc.mem_alloc(),
                'platform': sys.platform,
                'timestamp': format_jst_time(),
                'uptime_seconds': int(time.time() - boot_time),
                'temperature_history_count': len(sensor_manager.temperature_history),
                'humidity_history_count': len(sensor_manager.humidity_history)
            }
            return Response(json.dumps(info), headers={'Content-Type': 'application/json'})
        except Exception as e:
            log_message(f"API /api/system でエラー: {e}", "api", "error")
            return Response(json.dumps({'error': str(e)}), status_code=500)

    @app.route('/health')
    def health_check(request):
        try:
            gc.collect()
            health = {
                'status': 'healthy',
                'timestamp': format_jst_time(),
                'uptime_seconds': int(time.time() - boot_time),
                'memory_free': gc.mem_free(),
                'sensor_status': sensor_manager.check_sensor_status(),
                'measurement_count': sensor_manager.measurement_count
            }
            return Response(json.dumps(health), headers={'Content-Type': 'application/json'})
        except Exception as e:
            log_message(f"API /health でエラー: {e}", "api", "error")
            return Response(json.dumps({'status': 'error', 'error': str(e)}), status_code=500)

    @app.route('/config')
    def config_info(request):
        try:
            # wifi_configから読み込んだ動的な設定も返す
            from wifi_config import THINGSPEAK_ENABLED, THINGSPEAK_CHANNEL_ID, THINGSPEAK_API_KEY, THINGSPEAK_INTERVAL_MS
            
            cfg_data = {
                'device': 'ESP32-S3',
                'sensor_type': 'DHT22',
                'sensor_pin': config['DHT_PIN'],
                'internal_pullup': config['USE_INTERNAL_PULLUP'],
                'max_history_size': config['MAX_HISTORY_SIZE'],
                'server_port': config['WS_PORT'],
                'thingspeak_enabled': THINGSPEAK_ENABLED,
                'thingspeak_channel_id': THINGSPEAK_CHANNEL_ID if THINGSPEAK_ENABLED else None,
                'urequests_available': context['urequests_available'],
                'thingspeak_api_key_configured': True if THINGSPEAK_API_KEY and THINGSPEAK_API_KEY != 'YOUR_THINGSPEAK_WRITE_API_KEY' else False,
                'thingspeak_interval_sec': (THINGSPEAK_INTERVAL_MS // 1000) if THINGSPEAK_ENABLED else None,
                'timestamp': format_jst_time()
            }
            return Response(json.dumps(cfg_data), headers={'Content-Type': 'application/json'})
        except Exception as e:
            log_message(f"API /config でエラー: {e}", "api", "error")
            return Response(json.dumps({'error': str(e)}), status_code=500)

    @app.route('/api/logs')
    def api_logs(request):
        try:
            category_filter = request.args.get('category')
            level_filter = request.args.get('level')
            limit = int(request.args.get('limit', '50'))

            filtered_logs = [
                log for log in system_logs
                if (not category_filter or log['category'] == category_filter)
                and (not level_filter or log['level'] == level_filter)
            ]

            response_data = {
                'logs': filtered_logs[-limit:],
                'total_logs': len(system_logs),
                'filtered_count': len(filtered_logs),
                'categories': list(set(log['category'] for log in system_logs)),
                'levels': list(set(log['level'] for log in system_logs)),
                'timestamp': format_jst_time()
            }
            return Response(json.dumps(response_data), headers={'Content-Type': 'application/json'})
        except Exception as e:
            log_message(f"API /api/logs でエラー: {e}", "api", "error")
            return Response(json.dumps({'error': str(e)}), status_code=500)