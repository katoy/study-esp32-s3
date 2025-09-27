# sensor_manager.py

import machine
import time
import dht
try:
    import _thread
except ImportError:
    _thread = None

class SensorManager:
    def __init__(self, pin, use_internal_pullup, log_func, valid_temp_range, valid_hum_range, max_history_size):
        self.pin_id = pin
        self.use_internal_pullup = use_internal_pullup
        self.log = log_func
        self.valid_temp_range = valid_temp_range
        self.valid_hum_range = valid_hum_range
        self.max_history_size = max_history_size

        self.sensor = None
        self.lock = _thread.allocate_lock() if _thread else None
        
        self.temperature_history = []
        self.humidity_history = []
        self.last_sensor_data = None
        self.measurement_count = 0
        
        self._initialize_sensor()

    def _initialize_sensor(self):
        self.log("DHT22センサーの初期化を開始します...", "sensor", "info")
        try:
            pin_obj = machine.Pin(self.pin_id, machine.Pin.IN, machine.Pin.PULL_UP) if self.use_internal_pullup else machine.Pin(self.pin_id)
            self.sensor = dht.DHT22(pin_obj)
            time.sleep(2)  # センサーの安定化を待機
            self.log("センサーの準備が完了しました。", "sensor", "info")
        except Exception as e:
            self.log(f"センサーの初期化に失敗: {e}", "sensor", "critical")

    def read_with_retry(self, max_retries=3, retry_delay=3):
        for attempt in range(max_retries):
            try:
                time.sleep_ms(60)
                if self.lock:
                    self.lock.acquire()
                self.sensor.measure()
                temp = self.sensor.temperature()
                hum = self.sensor.humidity()
            finally:
                if self.lock:
                    self.lock.release()

            if self.valid_temp_range[0] <= temp <= self.valid_temp_range[1] and \
               self.valid_hum_range[0] <= hum <= self.valid_hum_range[1]:
                self.measurement_count += 1
                current_time = time.time()

                self.temperature_history.append({'value': temp, 'time': current_time})
                self.humidity_history.append({'value': hum, 'time': current_time})

                if len(self.temperature_history) > self.max_history_size:
                    self.temperature_history.pop(0)
                if len(self.humidity_history) > self.max_history_size:
                    self.humidity_history.pop(0)

                sensor_data = {
                    'temperature': round(temp, 1),
                    'humidity': round(hum, 1),
                    'unix_time': current_time,
                    'measurement_count': self.measurement_count,
                    'retry_attempt': attempt + 1,
                    'status': 'ok'
                }
                self.last_sensor_data = sensor_data
                return sensor_data
            else:
                self.log(f"無効なセンサーデータ (試行 {attempt + 1}): T={temp}, H={hum}", "sensor", "warning")

            if attempt < max_retries - 1:
                self.log(f"{retry_delay}秒後に再試行します...", "sensor", "info")
                time.sleep(retry_delay)

        self.log("センサー読み取りの全再試行が失敗しました。", "sensor", "error")
        return None

    def check_sensor_status(self):
        try:
            self.sensor.measure()
            temp = self.sensor.temperature()
            hum = self.sensor.humidity()
            return 'OK' if self.valid_temp_range[0] <= temp <= self.valid_temp_range[1] and \
                           self.valid_hum_range[0] <= hum <= self.valid_hum_range[1] else 'Warning'
        except Exception:
            return 'Error'