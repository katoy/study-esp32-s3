# thingspeak.py - ThingSpeak Client for MicroPython

import time
try:
    import urequests
except ImportError:
    pass # Availability is handled by the main script

class ThingSpeakClient:
    def __init__(self, api_key, channel_id, interval_ms, enabled, log_func, api_url, jst_offset, urequests_available):
        self.api_key = api_key
        self.channel_id = channel_id
        self.interval_ms = interval_ms
        self.enabled = enabled
        self.log = log_func
        self.api_url = api_url
        self.jst_offset = jst_offset
        self.urequests_available = urequests_available
        
        self.last_send_time = 0
        self.last_send_slot = None

    def send_data(self, data, force_send=False):
        """ThingSpeakにデータを送信します。"""
        if not (self.enabled and self.api_key and self.urequests_available):
            return

        now_utc = time.time()
        now_jst = now_utc + self.jst_offset
        interval_sec = max(self.interval_ms // 1000, 1)
        current_slot = int(now_jst // interval_sec)

        if not force_send and self.last_send_slot is not None and current_slot == self.last_send_slot:
            return

        try:
            if 'temperature' not in data or 'humidity' not in data:
                raise ValueError("データ形式が不正です。'temperature'と'humidity'キーが必要です。")

            url = f"{self.api_url}/update?api_key={self.api_key}&field1={data['temperature']}&field2={data['humidity']}"
            
            self.log(f"ThingSpeakへ送信開始: T={data['temperature']:.1f}, H={data['humidity']:.1f}", 'cloud', 'info')
            response = urequests.get(url)
            
            if response.status_code == 200:
                entry_id = response.text.strip()
                self.log(f"ThingSpeakへの送信成功 (エントリーID: {entry_id})", 'cloud', 'success')
            else:
                self.log(f"ThingSpeakへの送信失敗: HTTP {response.status_code} - {response.text}", 'cloud', 'error')
            
            response.close()
            self.last_send_time = time.ticks_ms()
            self.last_send_slot = current_slot

        except Exception as e:
            self.log(f"ThingSpeakへの送信中に例外が発生しました: {e}", 'cloud', 'error')

    def background_worker(self, sensor_manager):
        """バックグラウンドで定期的にThingSpeakにデータを送信します。"""
        self.log("ThingSpeakバックグラウンド送信スレッドを開始しました。", "cloud", "info")
        while True:
            try:
                now_utc = time.time()
                now_jst = now_utc + self.jst_offset
                interval_sec = max(self.interval_ms // 1000, 1)
                remainder = int(now_jst % interval_sec)
                sleep_sec = interval_sec - remainder if remainder != 0 else interval_sec
                time.sleep(sleep_sec)

                self.log("バックグラウンド送信トリガー", "cloud", "debug")
                sensor_data = sensor_manager.read_with_retry()
                if sensor_data:
                    self.send_data(sensor_data, force_send=True)

            except Exception as e:
                self.log(f"バックグラウンド送信スレッドでエラーが発生しました: {e}", "cloud", "error")
                time.sleep(60) # エラー発生時は60秒待機