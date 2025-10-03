"""
DHT22/DHT11センサー制御ライブラリ
ESP32-S3 MicroPython用

機能:
- DHT22/DHT11センサーの自動検出
- エラーハンドリングと再試行
- 妥当性チェック
- 安定した読み取り
"""

import machine
import dht
import time

class DHT22Controller:
    """DHT22/DHT11センサーコントローラー"""
    
    def __init__(self, pin, use_pullup=False, auto_detect=True):
        """
        初期化
        
        Args:
            pin: GPIOピン番号
            use_pullup: 内蔵プルアップ抵抗を使用するか
            auto_detect: DHT22が失敗時にDHT11も試すか
        """
        self.pin = pin
        self.use_pullup = use_pullup
        self.auto_detect = auto_detect
        self.sensor = None
        self.sensor_type = None
        self.last_read_time = 0
        self.min_interval = 2.0  # 最小読み取り間隔（秒）
        
        self._initialize_sensor()
    
    def _initialize_sensor(self):
        """センサーを初期化"""
        gpio_pin = machine.Pin(self.pin)
        
        # 内蔵プルアップ設定
        if self.use_pullup:
            gpio_pin = machine.Pin(self.pin, machine.Pin.IN, machine.Pin.PULL_UP)
        
        try:
            # まずDHT22を試す
            self.sensor = dht.DHT22(gpio_pin)
            self.sensor_type = "DHT22"
            print(f"DHT22センサーを初期化しました (GPIO{self.pin})")
        except Exception as e:
            if self.auto_detect:
                try:
                    # DHT11を試す
                    self.sensor = dht.DHT11(gpio_pin)
                    self.sensor_type = "DHT11"
                    print(f"DHT11センサーを初期化しました (GPIO{self.pin})")
                except Exception as e2:
                    print(f"センサー初期化失敗: DHT22={e}, DHT11={e2}")
                    self.sensor = None
                    self.sensor_type = None
            else:
                print(f"DHT22センサー初期化失敗: {e}")
                self.sensor = None
                self.sensor_type = None
    
    def is_ready(self):
        """センサーが利用可能かチェック"""
        return self.sensor is not None
    
    def can_read(self):
        """読み取り可能かチェック（間隔制限）"""
        current_time = time.time()
        return current_time - self.last_read_time >= self.min_interval
    
    def read(self, retry_count=3):
        """
        センサーデータを読み取り
        
        Args:
            retry_count: 失敗時の再試行回数
            
        Returns:
            dict: {"temperature": float, "humidity": float, "success": bool, "error": str}
        """
        if not self.is_ready():
            return {
                "temperature": None,
                "humidity": None,
                "success": False,
                "error": "センサーが初期化されていません"
            }
        
        # 読み取り間隔チェック
        if not self.can_read():
            return {
                "temperature": None,
                "humidity": None,
                "success": False,
                "error": f"読み取り間隔が短すぎます（最小{self.min_interval}秒）"
            }
        
        # 再試行ループ
        for attempt in range(retry_count):
            try:
                self.sensor.measure()
                temperature = self.sensor.temperature()
                humidity = self.sensor.humidity()
                
                # 妥当性チェック
                if not self._validate_reading(temperature, humidity):
                    error_msg = f"無効な値: 温度={temperature}°C, 湿度={humidity}%"
                    if attempt < retry_count - 1:
                        print(f"試行{attempt + 1}失敗: {error_msg} (再試行します)")
                        time.sleep(0.5)
                        continue
                    else:
                        return {
                            "temperature": temperature,
                            "humidity": humidity,
                            "success": False,
                            "error": error_msg
                        }
                
                # 成功
                self.last_read_time = time.time()
                return {
                    "temperature": temperature,
                    "humidity": humidity,
                    "success": True,
                    "error": None
                }
                
            except Exception as e:
                error_msg = f"読み取りエラー: {e}"
                if attempt < retry_count - 1:
                    print(f"試行{attempt + 1}失敗: {error_msg} (再試行します)")
                    time.sleep(0.5)
                    continue
                else:
                    return {
                        "temperature": None,
                        "humidity": None,
                        "success": False,
                        "error": error_msg
                    }
        
        # ここには到達しないはずだが、念のため
        return {
            "temperature": None,
            "humidity": None,
            "success": False,
            "error": "不明なエラー"
        }
    
    def _validate_reading(self, temperature, humidity):
        """読み取り値の妥当性をチェック"""
        if temperature is None or humidity is None:
            return False
        
        # DHT22の仕様範囲
        if self.sensor_type == "DHT22":
            if temperature < -40 or temperature > 80:
                return False
            if humidity < 0 or humidity > 100:
                return False
        
        # DHT11の仕様範囲
        elif self.sensor_type == "DHT11":
            if temperature < 0 or temperature > 50:
                return False
            if humidity < 20 or humidity > 90:
                return False
        
        return True
    
    def get_info(self):
        """センサー情報を取得"""
        return {
            "sensor_type": self.sensor_type,
            "pin": self.pin,
            "use_pullup": self.use_pullup,
            "is_ready": self.is_ready(),
            "min_interval": self.min_interval
        }

# 使用例とテスト関数
def test_dht22():
    """DHT22センサーのテスト"""
    print("=== DHT22センサーテスト開始 ===")
    
    # センサー初期化（GPIO4使用、外部プルアップ）
    dht_controller = DHT22Controller(pin=4, use_pullup=False, auto_detect=True)
    
    # センサー情報表示
    info = dht_controller.get_info()
    print(f"センサー情報: {info}")
    
    if not dht_controller.is_ready():
        print("❌ センサーが利用できません")
        return
    
    # 5回読み取りテスト
    for i in range(5):
        print(f"\n--- 読み取り {i + 1}/5 ---")
        
        # 読み取り可能かチェック
        if not dht_controller.can_read():
            print("⏳ 読み取り間隔待機中...")
            time.sleep(2)
        
        # データ読み取り
        result = dht_controller.read()
        
        if result["success"]:
            print(f"✅ 温度: {result['temperature']:.1f}°C")
            print(f"✅ 湿度: {result['humidity']:.1f}%")
        else:
            print(f"❌ エラー: {result['error']}")
        
        time.sleep(3)  # 次の読み取りまで3秒待機
    
    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    test_dht22()