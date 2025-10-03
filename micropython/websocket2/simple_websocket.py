"""
WebSocketサーバー実装
ESP32-S3 MicroPython対応
"""

import socket
import time
import json
import ubinascii
import hashlib
import struct
import gc
import network


def read_file(filepath):
    """ファイルを読み込んで内容を返す"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"ファイル読み込みエラー {filepath}: {e}")
        return None


class SimpleWebSocket:
    """シンプルなWebSocketサーバー実装"""

    def __init__(self):
        self.clients = []
        self.last_memory_check = time.time()
        self.memory_check_interval = 10  # 10秒ごとにメモリチェック
        self.max_clients = 3  # ESP32-S3の制限を考慮
        self.last_wifi_check = time.time()
        self.wifi_check_interval = 30  # 30秒ごとにWiFiチェック
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 5  # 5秒ごとにハートビート（より積極的）
        self.client_timeout = 15  # 15秒でクライアントタイムアウト
        self.connection_counter = 0  # 接続カウンター
        self.last_detailed_log = time.time()
        self.detailed_log_interval = 15  # 15秒ごとに詳細ログ（頻度を下げる）

    def _make_response_key(self, client_key):
        """WebSocketハンドシェイクレスポンスキーを生成"""
        magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept_key = ubinascii.b2a_base64(
            hashlib.sha1((client_key + magic).encode()).digest()
        ).decode().strip()
        return accept_key

    def _parse_websocket_frame(self, data):
        """WebSocketフレームをパース"""
        if len(data) < 2:
            return None

        byte1, byte2 = struct.unpack('!BB', data[:2])
        fin = (byte1 >> 7) & 1
        opcode = byte1 & 0x0f
        masked = (byte2 >> 7) & 1
        payload_len = byte2 & 0x7f

        offset = 2

        # ペイロード長の拡張処理
        if payload_len == 126:
            if len(data) < offset + 2:
                return None
            payload_len = struct.unpack('!H', data[offset:offset+2])[0]
            offset += 2
        elif payload_len == 127:
            if len(data) < offset + 8:
                return None
            payload_len = struct.unpack('!Q', data[offset:offset+8])[0]
            offset += 8

        # マスクキー処理
        if masked:
            if len(data) < offset + 4:
                return None
            mask_key = data[offset:offset+4]
            offset += 4
        else:
            mask_key = None

        # ペイロードデータ
        if len(data) < offset + payload_len:
            return None

        payload = data[offset:offset+payload_len]

        # マスク解除
        if masked and mask_key:
            unmasked = bytearray()
            for i in range(len(payload)):
                unmasked.append(payload[i] ^ mask_key[i % 4])
            payload = bytes(unmasked)

        if opcode == 8:  # Close frame
            return {'type': 'close'}
        elif opcode == 9:  # Ping frame
            return {'type': 'ping', 'payload': payload}
        elif opcode == 10:  # Pong frame
            return {'type': 'pong', 'payload': payload}
        elif opcode == 1:  # Text frame
            return {'type': 'text', 'data': payload.decode('utf-8')}

        return None

    def _create_frame(self, data):
        """WebSocketフレームを作成"""
        if isinstance(data, str):
            data = data.encode('utf-8')

        data_len = len(data)

        if data_len < 126:
            frame = struct.pack('!BB', 0x81, data_len)
        elif data_len < 65536:
            frame = struct.pack('!BBH', 0x81, 126, data_len)
        else:
            frame = struct.pack('!BBQ', 0x81, 127, data_len)

        return frame + data

    def handle_new_connection(self, conn, addr=None):
        """新しいWebSocket接続を処理"""
        try:
            request = conn.recv(1024).decode()

            # WebSocketハンドシェイクチェック
            if 'Upgrade: websocket' not in request:
                # 通常のHTTPリクエスト - 静的ファイルを返す
                self._handle_http_request(request, conn)
                return False            # WebSocketキーを取得
            lines = request.split('\r\n')
            websocket_key = None

            for line in lines:
                if line.startswith('Sec-WebSocket-Key:'):
                    websocket_key = line.split(': ')[1]
                    break

            if not websocket_key:
                conn.close()
                return False

            # WebSocketレスポンスを送信
            response_key = self._make_response_key(websocket_key)
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {response_key}\r\n\r\n"
            )

            conn.send(response.encode())

            # クライアント数制限チェック
            if len(self.clients) >= self.max_clients:
                print(f"⚠️ 最大クライアント数({self.max_clients})に達しているため接続を拒否")
                error_response = "HTTP/1.1 503 Service Unavailable\r\n\r\nMax connections reached"
                conn.send(error_response.encode())
                conn.close()
                return False

            # ソケット設定を最適化
            try:
                conn.settimeout(30)  # 30秒タイムアウト
                # SO_KEEPALIVEを有効化（利用可能な場合のみ）
                try:
                    conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    print("✅ TCP Keep-Alive有効化")
                except (OSError, AttributeError):
                    print("ℹ️ TCP Keep-Aliveは利用できません（MicroPython制限）")

                # TCP_NODELAYを有効化（利用可能な場合）
                try:
                    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    print("✅ TCP_NODELAY有効化")
                except (OSError, AttributeError):
                    print("ℹ️ TCP_NODELAYは利用できません")

                # 送信バッファサイズを調整
                try:
                    conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
                    conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
                    print("✅ ソケットバッファサイズ調整完了")
                except (OSError, AttributeError):
                    print("ℹ️ バッファサイズ調整は利用できません")

            except Exception as sock_error:
                print(f"⚠️ ソケット設定エラー: {sock_error}")

            self.connection_counter += 1
            client_id = f"client_{self.connection_counter}"

            self.clients.append({
                'socket': conn,
                'addr': addr or 'unknown',
                'connected_at': time.time(),
                'last_ping': time.time(),
                'id': client_id,
                'bytes_sent': 0,
                'bytes_received': 0
            })

            print(f"✅ WebSocket接続確立 [{client_id}] from {self.clients[-1]['addr']}。現在の接続数: {len(self.clients)}")
            print(f"📊 接続統計 - 総接続数: {self.connection_counter}, 現在: {len(self.clients)}")

            # メモリ状況確認
            free_memory = gc.mem_free()
            print(f"💾 接続時空きメモリ: {free_memory} bytes")

            # ESP32-S3制限の案内
            if self.connection_counter > 1:
                print(f"ℹ️ ESP32-S3では約10秒で自動切断されますが、即座に再接続されます")

            # 接続確立メッセージを送信
            welcome_msg = {
                "type": "welcome",
                "message": "WebSocket接続が確立されました",
                "timestamp": time.time()
            }

            try:
                frame = self._create_frame(json.dumps(welcome_msg))
                conn.send(frame)
                print("ウェルカムメッセージ送信完了")
            except Exception as send_error:
                print(f"ウェルカムメッセージ送信エラー: {send_error}")

            return True

        except Exception as e:
            print(f"接続処理エラー: {e}")
            try:
                conn.close()
            except:
                pass
            return False

    def _handle_http_request(self, request, conn):
        """HTTPリクエストを処理して適切なファイルを返す"""
        try:
            # リクエストラインを解析
            lines = request.strip().split('\r\n')
            if not lines:
                self._send_error(conn, 400, "Bad Request")
                return

            request_line = lines[0]
            parts = request_line.split()
            if len(parts) < 2:
                self._send_error(conn, 400, "Bad Request")
                return

            method = parts[0]
            path = parts[1]

            if method != 'GET':
                self._send_error(conn, 405, "Method Not Allowed")
                return

            # パスの正規化
            if path == '/':
                path = '/index.html'

            # ファイル名とContent-Typeの決定
            if path.startswith('/'):
                filepath = 'static' + path
            else:
                filepath = 'static/' + path

            # MIMEタイプの決定
            if path.endswith('.html'):
                content_type = 'text/html; charset=utf-8'
            elif path.endswith('.css'):
                content_type = 'text/css; charset=utf-8'
            elif path.endswith('.js'):
                content_type = 'application/javascript; charset=utf-8'
            else:
                content_type = 'text/plain; charset=utf-8'

            # ファイル読み込み（詳細ログ付き）
            print(f"📂 ファイル要求: {path} -> {filepath}")
            content = read_file(filepath)
            if content is None:
                print(f"❌ ファイルが見つかりません: {filepath}")
                self._send_error(conn, 404, "Not Found")
                return

            print(f"✅ ファイル送信成功: {filepath} ({len(content)} bytes)")
            # レスポンス送信
            self._send_response(conn, 200, content_type, content)

        except Exception as e:
            print(f"HTTP処理エラー: {e}")
            self._send_error(conn, 500, "Internal Server Error")

    def _send_response(self, conn, status_code, content_type, content):
        """HTTPレスポンスを送信"""
        status_messages = {
            200: "OK",
            400: "Bad Request",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error"
        }

        status_message = status_messages.get(status_code, "Unknown")
        content_bytes = content.encode('utf-8')

        response = (
            f"HTTP/1.1 {status_code} {status_message}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(content_bytes)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )

        try:
            conn.send(response.encode('utf-8'))
            conn.send(content_bytes)
        except Exception as e:
            print(f"レスポンス送信エラー: {e}")
        finally:
            conn.close()

    def _send_error(self, conn, status_code, message):
        """エラーレスポンスを送信"""
        error_content = f"""<!DOCTYPE html>
<html>
<head><title>{status_code} {message}</title></head>
<body><h1>{status_code} {message}</h1></body>
</html>"""
        self._send_response(conn, status_code, "text/html; charset=utf-8", error_content)

    def handle_client_frames(self):
        """クライアントからのフレームを処理（イベントドリブン方式）"""
        if not self.clients:
            return

        try:
            import select
        except ImportError:
            print("❌ selectモジュールが利用できません。MicroPythonでは対応していない可能性があります。")
            return

        disconnected_clients = []

        # selectを使用してデータが利用可能なソケットのみ処理
        sockets = [client_info['socket'] for client_info in self.clients]

        try:
            # 10ms タイムアウトでデータが読める状態のソケットを取得
            ready_sockets, _, error_sockets = select.select(sockets, [], sockets, 0.01)

            # エラー状態のソケットをまず処理
            for error_socket in error_sockets:
                client_info = next((c for c in self.clients if c['socket'] == error_socket), None)
                if client_info:
                    print(f"⚠️ ソケットエラー検出 [{client_info.get('id', 'unknown')}]")
                    disconnected_clients.append(client_info)

            # データが読める状態のソケットを処理
            for ready_socket in ready_sockets:
                client_info = next((c for c in self.clients if c['socket'] == ready_socket), None)
                if not client_info or client_info in disconnected_clients:
                    continue

                try:
                    data = ready_socket.recv(1024)

                    if len(data) == 0:
                        # 接続が閉じられた
                        connection_age = time.time() - client_info.get('connected_at', time.time())
                        memory_free = gc.mem_free()
                        print(f"🔌 接続切断検出 [{client_info.get('id', 'unknown')}] {client_info['addr']}")
                        print(f"   └─ 接続時間: {connection_age:.1f}秒, 空きメモリ: {memory_free}bytes")
                        print(f"   └─ 最後のping: {time.time() - client_info.get('last_ping', time.time()):.1f}秒前")
                        disconnected_clients.append(client_info)
                        continue

                    frame = self._parse_websocket_frame(data)
                    if frame:
                        if frame['type'] == 'close':
                            print("クライアントからのclose frame受信")
                            disconnected_clients.append(client_info)
                        elif frame['type'] == 'ping':
                            # Pongフレームを返す
                            pong_frame = self._create_pong_frame(frame.get('payload', b''))
                            try:
                                ready_socket.send(pong_frame)
                                client_info['last_ping'] = time.time()
                                print("📡 Ping受信、Pong送信")
                            except Exception as send_error:
                                print(f"Pong送信エラー: {send_error}")
                                disconnected_clients.append(client_info)
                        elif frame['type'] == 'text':
                            # テキストメッセージの処理
                            message = frame['data'].strip()
                            if message == 'ping':
                                # Keep-alive ping応答
                                try:
                                    response_frame = self._create_frame('pong')
                                    ready_socket.send(response_frame)
                                    client_info['last_ping'] = time.time()
                                    print("📡 Keep-alive ping応答送信")
                                except Exception as send_error:
                                    print(f"Keep-alive応答送信エラー: {send_error}")
                                    disconnected_clients.append(client_info)
                            else:
                                print(f"⬅️ {message}")

                    # メモリクリーンアップ
                    del data
                    if 'frame' in locals():
                        del frame

                except Exception as e:
                    connection_age = time.time() - client_info.get('connected_at', time.time())
                    print(f"❌ フレーム処理エラー [{client_info.get('id', 'unknown')}] {type(e).__name__}: {e}")
                    print(f"   └─ 接続時間: {connection_age:.1f}秒")
                    disconnected_clients.append(client_info)

                except Exception as e:
                    connection_age = time.time() - client_info.get('connected_at', time.time())
                    print(f"❌ フレーム処理エラー [{client_info.get('id', 'unknown')}] {type(e).__name__}: {e}")
                    print(f"   └─ 接続時間: {connection_age:.1f}秒")
                    disconnected_clients.append(client_info)

        except Exception as select_error:
            print(f"⚠️ select処理エラー: {select_error}")
            print("selectが利用できません。MicroPythonのバージョンを確認してください。")
            return

        # 切断されたクライアントを削除
        for client_info in disconnected_clients:
            if client_info in self.clients:
                self.clients.remove(client_info)
                print(f"クライアント削除: {len(self.clients)}個の接続が残存")
            try:
                client_info['socket'].close()
            except Exception as close_error:
                print(f"クライアント切断エラー: {close_error}")

        # メモリクリーンアップ
        if disconnected_clients:
            print(f"切断されたクライアント数: {len(disconnected_clients)}")
            print(f"現在のアクティブ接続数: {len(self.clients)}")
            del disconnected_clients
            gc.collect()  # ガベージコレクション実行

    def check_memory_and_cleanup(self):
        """メモリ監視とクリーンアップ"""
        current_time = time.time()

        # 定期的なメモリチェック
        if current_time - self.last_memory_check > self.memory_check_interval:
            self.last_memory_check = current_time

            free_memory = gc.mem_free()
            print(f"💾 メモリ監視 - 空きメモリ: {free_memory} bytes, 接続数: {len(self.clients)}")

            # メモリが少ない場合は古い接続を切断
            if free_memory < 10000:  # 10KB以下の場合
                print("⚠️ メモリ不足 - 古い接続を切断します")
                if self.clients:
                    # 最も古い接続を切断
                    oldest_client = min(self.clients, key=lambda x: x['connected_at'])
                    try:
                        oldest_client['socket'].close()
                        self.clients.remove(oldest_client)
                        print(f"メモリ不足により古い接続を切断: {oldest_client['addr']}")
                    except Exception as e:
                        print(f"古い接続切断エラー: {e}")

                # 強制ガベージコレクション
                gc.collect()
                print(f"ガベージコレクション後の空きメモリ: {gc.mem_free()} bytes")

        # 詳細ログ出力
        self.log_connection_details()

    def log_connection_details(self):
        """接続の詳細ログを出力"""
        current_time = time.time()

        if current_time - self.last_detailed_log > self.detailed_log_interval:
            self.last_detailed_log = current_time

            if self.clients:
                print(f"📊 接続詳細 ({len(self.clients)}個):")
                for client_info in self.clients:
                    age = current_time - client_info['connected_at']
                    last_ping = current_time - client_info.get('last_ping', current_time)
                    print(f"  [{client_info['id']}] {client_info['addr']} - 接続{age:.1f}s, ping{last_ping:.1f}s前")

    def send_heartbeat(self):
        """全クライアントにハートビートpingを送信"""
        current_time = time.time()

        if current_time - self.last_heartbeat > self.heartbeat_interval:
            self.last_heartbeat = current_time

            if self.clients:
                # ログを簡潔に（接続時間の節目のみ表示）
                connection_age = time.time() - self.clients[0].get('connected_at', time.time())
                if connection_age % 30 < 5:  # 30秒ごとに表示
                    print(f"💓 ハートビート - {len(self.clients)}接続, {connection_age:.0f}秒経過")

                disconnected_clients = []

                for client_info in self.clients[:]:
                    try:
                        # Pingフレームを送信
                        ping_frame = self._create_ping_frame()
                        client_info['socket'].send(ping_frame)
                        client_info['last_ping'] = current_time

                        # タイムアウトチェック（接続から10秒後から監視）
                        if connection_age > 10 and current_time - client_info.get('last_ping', current_time) > self.client_timeout:
                            print(f"⏰ タイムアウト [{client_info['id']}] {client_info['addr']} (接続{connection_age:.1f}s経過)")
                            disconnected_clients.append(client_info)

                    except Exception as e:
                        print(f"ハートビート送信エラー: {e}")
                        disconnected_clients.append(client_info)

                # タイムアウト・エラーのクライアントを削除
                for client_info in disconnected_clients:
                    if client_info in self.clients:
                        self.clients.remove(client_info)
                        print(f"タイムアウト/エラーによりクライアント削除: {client_info['addr']}")
                    try:
                        client_info['socket'].close()
                    except Exception:
                        pass

    def check_wifi_connection(self):
        """WiFi接続状態を監視"""
        current_time = time.time()

        if current_time - self.last_wifi_check > self.wifi_check_interval:
            self.last_wifi_check = current_time

            try:
                wlan = network.WLAN(network.STA_IF)
                if not wlan.isconnected():
                    print("⚠️ WiFi接続が切断されました - 再接続を試みます")
                    # 全クライアントを切断
                    for client_info in self.clients[:]:
                        try:
                            client_info['socket'].close()
                        except Exception:
                            pass
                    self.clients.clear()
                    print("全クライアント切断完了")

                    # WiFi再接続試行は上位レベルで処理
                    return False
                else:
                    # 接続OK
                    signal_strength = wlan.status('rssi') if hasattr(wlan, 'status') else 'N/A'
                    print(f"📶 WiFi接続正常 - 信号強度: {signal_strength} dBm, 接続数: {len(self.clients)}")
                    return True

            except Exception as e:
                print(f"WiFi状態チェックエラー: {e}")
                return False

        return True  # チェック間隔外は正常とみなす

    def send_keepalive_data(self):
        """接続維持のための軽量データを送信（ESP32-S3対策）"""
        if self.clients:
            keepalive_data = {
                "type": "keepalive",
                "timestamp": time.time(),
                "memory": gc.mem_free(),
                "clients": len(self.clients)
            }

            # 軽量データでアイドル状態を回避
            self.broadcast_data(keepalive_data)
            print(f"💚 キープアライブ送信 - メモリ:{gc.mem_free()}B, 接続数:{len(self.clients)}")

    def _create_pong_frame(self, payload=b''):
        """Pongフレームを作成"""
        # Pongフレーム (opcode 0xA)
        frame = struct.pack('!BB', 0x8A, len(payload))
        return frame + payload

    def _create_ping_frame(self, payload=b''):
        """Pingフレームを作成"""
        # Pingフレーム (opcode 0x9)
        frame = struct.pack('!BB', 0x89, len(payload))
        return frame + payload

    def broadcast_data(self, data):
        """全クライアントにデータを送信"""
        if not self.clients:
            return

        try:
            json_data = json.dumps(data)
            frame = self._create_frame(json_data)
        except Exception as e:
            print(f"JSONシリアライズエラー: {e}")
            return

        disconnected_clients = []

        for client_info in self.clients[:]:  # リストのコピーでイテレート
            try:
                client_info['socket'].send(frame)
            except Exception as e:
                print(f"クライアント送信エラー: {type(e).__name__}: {e}")
                disconnected_clients.append(client_info)

        # 切断されたクライアントを削除
        for client_info in disconnected_clients:
            if client_info in self.clients:
                self.clients.remove(client_info)
                print(f"送信エラーによりクライアント削除: {len(self.clients)}個の接続が残存")
            try:
                client_info['socket'].close()
            except Exception as close_error:
                print(f"クライアント切断エラー: {close_error}")

        if disconnected_clients:
            print(f"切断されたクライアント数: {len(disconnected_clients)}")
            print(f"現在のアクティブ接続数: {len(self.clients)}")
            # メモリクリーンアップ
            del disconnected_clients
            gc.collect()