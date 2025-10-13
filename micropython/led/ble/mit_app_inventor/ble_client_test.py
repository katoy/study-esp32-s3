#*****************************************************
#  BLE クライアントテスト - PICO_LED デバイスの動作確認
#  ESP32-S3 の MicroPython で制御
#  pico_led.py を実行しているデバイスに接続してテスト
#*****************************************************
import bluetooth
import time
from micropython import const

# 定数定義
TARGET_DEVICE_NAME = "PICO_LED"
UART_SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
UART_TX_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")  # サーバーからの送信
UART_RX_UUID = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")  # サーバーへの送信

LED_ON_COMMAND = b'1\x00'
LED_OFF_COMMAND = b'0\x00'

SCAN_TIMEOUT = 5000  # ms
CONNECT_TIMEOUT = 5000  # ms

# IRQイベント定数
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)
_IRQ_GATTC_NOTIFY = const(18)


class BLEClient:
    def __init__(self):
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)

        # 接続状態管理
        self._conn_handle = None
        self._target_addr = None
        self._rx_handle = None
        self._tx_handle = None

        # スキャン状態
        self._scan_complete = False
        self._device_found = False

        # 接続状態
        self._connected = False
        self._services_discovered = False

        print("BLE Client initialized")

    def _irq(self, event, data):
        if event == _IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            name = self._decode_name(adv_data)
            if name == TARGET_DEVICE_NAME:
                print(f"Found target device: {name} at {self._format_addr(addr)}")
                self._target_addr = (addr_type, addr)
                self._device_found = True
                self._ble.gap_scan(None)  # スキャン停止

        elif event == _IRQ_SCAN_DONE:
            self._scan_complete = True

        elif event == _IRQ_PERIPHERAL_CONNECT:
            conn_handle, addr_type, addr = data
            print(f"Connected to device: {self._format_addr(addr)}")
            self._conn_handle = conn_handle
            self._connected = True

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            conn_handle, addr_type, addr = data
            print(f"Disconnected from device: {self._format_addr(addr)}")
            self._conn_handle = None
            self._connected = False
            self._services_discovered = False

        elif event == _IRQ_GATTC_SERVICE_RESULT:
            conn_handle, start_handle, end_handle, uuid = data
            if uuid == UART_SERVICE_UUID:
                print(f"Found UART service: {uuid}")

        elif event == _IRQ_GATTC_SERVICE_DONE:
            print("Service discovery complete")

        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            conn_handle, def_handle, value_handle, properties, uuid = data
            if uuid == UART_RX_UUID:
                self._rx_handle = value_handle
                print(f"Found RX characteristic: {uuid}")
            elif uuid == UART_TX_UUID:
                self._tx_handle = value_handle
                print(f"Found TX characteristic: {uuid}")

        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
            print("Characteristic discovery complete")
            if self._rx_handle and self._tx_handle:
                self._services_discovered = True
                print("All required characteristics found!")

        elif event == _IRQ_GATTC_NOTIFY:
            conn_handle, value_handle, notify_data = data
            if value_handle == self._tx_handle:
                print(f"Received notification: {notify_data}")

        elif event == _IRQ_GATTC_READ_RESULT:
            conn_handle, value_handle, char_data = data
            print(f"Read result: {char_data}")

    def _decode_name(self, adv_data):
        i = 0
        while i < len(adv_data):
            length = adv_data[i]
            if length == 0:
                break
            ad_type = adv_data[i + 1]
            if ad_type == 0x09:  # Complete Local Name
                return bytes(adv_data[i + 2:i + 1 + length]).decode('utf-8')
            i += 1 + length
        return None

    def _format_addr(self, addr):
        return ':'.join(f'{b:02x}' for b in addr)

    def scan_for_device(self):
        print(f"Scanning for {TARGET_DEVICE_NAME}...")
        self._scan_complete = False
        self._device_found = False
        self._ble.gap_scan(SCAN_TIMEOUT, 30000, 30000)

        # スキャン完了を待機
        start_time = time.ticks_ms()
        while not self._scan_complete and time.ticks_diff(time.ticks_ms(), start_time) < SCAN_TIMEOUT + 1000:
            time.sleep_ms(100)

        return self._device_found

    def connect(self):
        if not self._target_addr:
            print("No target device address available")
            return False

        print("Connecting to device...")
        self._connected = False
        self._ble.gap_connect(self._target_addr[0], self._target_addr[1])

        # 接続完了を待機
        start_time = time.ticks_ms()
        while not self._connected and time.ticks_diff(time.ticks_ms(), start_time) < CONNECT_TIMEOUT:
            time.sleep_ms(100)

        return self._connected

    def discover_services(self):
        if not self._connected:
            print("Not connected to device")
            return False

        print("Discovering services...")
        self._services_discovered = False
        self._ble.gattc_discover_services(self._conn_handle)

        # サービス発見完了を待機
        time.sleep_ms(1000)

        print("Discovering characteristics...")
        self._ble.gattc_discover_characteristics(self._conn_handle, 1, 65535)

        # 特性発見完了を待機
        start_time = time.ticks_ms()
        while not self._services_discovered and time.ticks_diff(time.ticks_ms(), start_time) < 3000:
            time.sleep_ms(100)

        return self._services_discovered

    def send_command(self, command):
        if not self._connected or not self._services_discovered:
            print("Device not ready for communication")
            return False

        try:
            print(f"Sending command: {command}")
            self._ble.gattc_write(self._conn_handle, self._rx_handle, command)
            return True
        except Exception as e:
            print(f"Failed to send command: {e}")
            return False

    def disconnect(self):
        if self._connected:
            print("Disconnecting...")
            self._ble.gap_disconnect(self._conn_handle)
            time.sleep_ms(500)

    def is_connected(self):
        return self._connected and self._services_discovered


def test_led_control():
    """LED制御のテスト関数"""
    client = BLEClient()

    try:
        # デバイスをスキャン
        if not client.scan_for_device():
            print("Target device not found!")
            return

        # 接続
        if not client.connect():
            print("Failed to connect to device!")
            return

        # サービス発見
        if not client.discover_services():
            print("Failed to discover services!")
            return

        print("\n=== LED Control Test ===")

        # LED制御テスト
        for i in range(3):
            print(f"\nTest cycle {i + 1}:")

            # LED ON
            print("Turning LED ON...")
            client.send_command(LED_ON_COMMAND)
            time.sleep(2)

            # LED OFF
            print("Turning LED OFF...")
            client.send_command(LED_OFF_COMMAND)
            time.sleep(2)

        print("\nTest completed successfully!")

    except Exception as e:
        print(f"Test failed: {e}")

    finally:
        client.disconnect()
        print("Client disconnected")


# メイン実行
if __name__ == "__main__":
    print("BLE Client Test Starting...")
    test_led_control()