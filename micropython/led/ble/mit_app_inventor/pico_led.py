#*****************************************************
#  BLE 通信で Raspberry Pi Pico W2 と MIT App Inventor と通信する。
#  LED 状態の表示と LED の制御
#  Raspberry Pi Pico W2 の MicroPython で制御
#  ble_advertising.py と ble_simple_peripheral.py
#  の Raspberry Pi Pico W2 へ Upload することが必要です。
#  PICO_LED というデバイス名で自動接続される。
#*****************************************************
import machine
import bluetooth
from ble_simple_peripheral import BLESimplePeripheral
import time

# 定数定義
LED_PIN_1 = 16
LED_ON_COMMAND = b'1\x00'
LED_OFF_COMMAND = b'0\x00'
BLE_DEVICE_NAME = "PICO_LED"
LOOP_DELAY = 0.1  # seconds

# BLEのオブジェクトの生成
ble = bluetooth.BLE()
# BLESimplePeripheralをBLEオブジェクトとしてインスタンス生成
sp = BLESimplePeripheral(ble, BLE_DEVICE_NAME)
# 各インスタンス生成
led_1 = machine.Pin(LED_PIN_1, machine.Pin.OUT)

#**** BLE の受信処理関数 *****
def on_rx(data):
    try:
        # 受信データをログ出力（デバッグ用）
        print("Data received: ", data)

        if data == LED_ON_COMMAND:
            led_1.value(1)
        elif data == LED_OFF_COMMAND:
            led_1.value(0)
        else:
            print(f"Unknown command: {data}")
            return

        # 送信データの編集
        resp = '1' if led_1.value() else '0'
        sp.send(resp)  # 送信実行

    except Exception as e:
        print(f"Error in on_rx: {e}")

#***** メインループ ************
callback_set = False
previous_connected = False  # 前回の接続状態を記録

while True:
    current_connected = sp.is_connected()

    if current_connected:  # BLE接続が完了していたら
        if not callback_set:
            sp.on_write(on_rx)  # 受信のCallback関数定義（一度だけ）
            callback_set = True

        # 新しく接続された場合、現在のLED状態を送信
        if not previous_connected:
            try:
                current_led_state = '1' if led_1.value() else '0'
                sp.send(current_led_state)
                print(f"Connection established. Current LED state sent: {current_led_state}")
            except Exception as e:
                print(f"Error sending initial LED state: {e}")
    else:
        callback_set = False

    previous_connected = current_connected
    time.sleep(LOOP_DELAY)  # CPU負荷軽減
