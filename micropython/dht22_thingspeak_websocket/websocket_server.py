# websocket_server.py - WebSocket server implementation for ESP32 MicroPython

import struct
import hashlib
import binascii
try:
    import _thread
except ImportError:
    _thread = None

class WebSocketServer:
    def __init__(self, log_func):
        self.log = log_func
        self.clients = []
        self.lock = _thread.allocate_lock() if _thread else None
        
    def _make_websocket_key_accept(self, key):
        """WebSocket接続のためのAcceptキーを生成"""
        WEBSOCKET_MAGIC = "258EAFA5-E959-4D58-9C62-E3C0C1C0438B"
        accept = key + WEBSOCKET_MAGIC
        sha1 = hashlib.sha1(accept.encode()).digest()
        return binascii.b2a_base64(sha1).decode().strip()
    
    def _parse_websocket_frame(self, data):
        """WebSocketフレームを解析"""
        if len(data) < 2:
            return None, None
            
        # 最初の2バイトを解析
        byte1, byte2 = data[0], data[1]
        opcode = byte1 & 0x0f
        masked = (byte2 >> 7) & 1
        payload_len = byte2 & 0x7f
        
        header_len = 2
        
        # 拡張ペイロード長
        if payload_len == 126:
            if len(data) < 4:
                return None, None
            payload_len = struct.unpack(">H", data[2:4])[0]
            header_len = 4
        elif payload_len == 127:
            if len(data) < 10:
                return None, None
            payload_len = struct.unpack(">Q", data[2:10])[0]
            header_len = 10
            
        # マスクキー
        if masked:
            if len(data) < header_len + 4:
                return None, None
            mask_key = data[header_len:header_len + 4]
            header_len += 4
        else:
            mask_key = None
            
        # ペイロードデータ
        if len(data) < header_len + payload_len:
            return None, None
            
        payload = data[header_len:header_len + payload_len]
        
        # マスク解除
        if masked and mask_key:
            payload = bytes([payload[i] ^ mask_key[i % 4] for i in range(len(payload))])
            
        return opcode, payload
    
    def _create_websocket_frame(self, opcode, payload):
        """WebSocketフレームを作成"""
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
            
        frame = bytearray()
        
        # FIN + opcode
        frame.append(0x80 | opcode)
        
        # ペイロード長
        payload_len = len(payload)
        if payload_len < 126:
            frame.append(payload_len)
        elif payload_len < 65536:
            frame.append(126)
            frame.extend(struct.pack(">H", payload_len))
        else:
            frame.append(127)
            frame.extend(struct.pack(">Q", payload_len))
            
        # ペイロードデータ
        frame.extend(payload)
        
        return bytes(frame)
    
    def handle_websocket_upgrade(self, request_data, client_socket):
        """WebSocket接続のアップグレード処理"""
        try:
            # HTTPヘッダーを解析
            lines = request_data.decode('utf-8').split('\r\n')
            headers = {}
            
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            # WebSocket必須ヘッダーの確認
            if (headers.get('upgrade', '').lower() != 'websocket' or 
                headers.get('connection', '').lower() != 'upgrade' or
                'sec-websocket-key' not in headers):
                return False
            
            # Acceptキーを生成
            websocket_key = headers['sec-websocket-key']
            accept_key = self._make_websocket_key_accept(websocket_key)
            
            # WebSocket応答を送信
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n" 
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept_key}\r\n"
                "\r\n"
            )
            
            client_socket.send(response.encode())
            
            # クライアントリストに追加
            if self.lock:
                self.lock.acquire()
            try:
                self.clients.append(client_socket)
                self.log(f"WebSocketクライアントが接続しました (総数: {len(self.clients)})", "websocket", "info")
            finally:
                if self.lock:
                    self.lock.release()
            
            return True
            
        except Exception as e:
            self.log(f"WebSocket接続処理でエラー: {e}", "websocket", "error")
            return False
    
    def broadcast_message(self, message):
        """全てのWebSocketクライアントにメッセージを送信"""
        if not self.clients:
            return
            
        # テキストフレーム (opcode 1) として送信
        frame = self._create_websocket_frame(1, message)
        
        if self.lock:
            self.lock.acquire()
        try:
            disconnected_clients = []
            
            for client in self.clients:
                try:
                    client.send(frame)
                except Exception as e:
                    self.log(f"WebSocketクライアントへの送信に失敗: {e}", "websocket", "warning")
                    disconnected_clients.append(client)
            
            # 切断されたクライアントを削除
            for client in disconnected_clients:
                self.clients.remove(client)
                try:
                    client.close()
                except Exception:
                    pass
            
            if disconnected_clients:
                self.log(f"WebSocketクライアント {len(disconnected_clients)} 件を削除 (残り: {len(self.clients)})", "websocket", "info")
                
        finally:
            if self.lock:
                self.lock.release()
    
    def handle_websocket_message(self, client_socket, data):
        """WebSocketメッセージの処理"""
        try:
            opcode, payload = self._parse_websocket_frame(data)
            
            if opcode is None:
                return True  # フレーム不完全、継続
            
            if opcode == 8:  # Close frame
                self.log("WebSocketクライアントからの終了要求を受信", "websocket", "info")
                self.remove_client(client_socket)
                return False
            elif opcode == 9:  # Ping frame
                # Pong frame (opcode 10) で応答
                pong_frame = self._create_websocket_frame(10, payload)
                client_socket.send(pong_frame)
                return True
            elif opcode == 10:  # Pong frame
                # Pingへの応答、特に処理不要
                return True
            elif opcode == 1:  # Text frame
                # クライアントからのテキストメッセージ（必要に応じて処理）
                message = payload.decode('utf-8')
                self.log(f"WebSocketメッセージ受信: {message[:50]}", "websocket", "debug")
                return True
            
            return True
            
        except Exception as e:
            self.log(f"WebSocketメッセージ処理でエラー: {e}", "websocket", "error")
            return False
    
    def remove_client(self, client_socket):
        """クライアントをリストから削除"""
        if self.lock:
            self.lock.acquire()
        try:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
                self.log(f"WebSocketクライアントが切断されました (残り: {len(self.clients)})", "websocket", "info")
        finally:
            if self.lock:
                self.lock.release()
        
        try:
            client_socket.close()
        except Exception:
            pass
    
    def get_client_count(self):
        """接続中のクライアント数を取得"""
        if self.lock:
            self.lock.acquire()
        try:
            return len(self.clients)
        finally:
            if self.lock:
                self.lock.release()