# ESP32-S3 DHT22 問題診断用コマンド集
# 以下のコマンドを一つずつREPLで実行してください

print("=== ESP32-S3 DHT22 診断開始 ===")

# 1. 基本的なピン出力テスト
import machine
import time

def test_gpio_output(pin_num):
    print(f"\nGPIO{pin_num} 出力テスト:")
    try:
        pin = machine.Pin(pin_num, machine.Pin.OUT)
        pin.value(1)
        print(f"  GPIO{pin_num} = HIGH")
        time.sleep(1)
        pin.value(0)
        print(f"  GPIO{pin_num} = LOW")
        print(f"  ✓ GPIO{pin_num} 出力OK")
        return True
    except Exception as e:
        print(f"  ✗ GPIO{pin_num} 出力エラー: {e}")
        return False

# GPIO1のテスト
test_gpio_output(1)

# 2. 複数ピンでのDHT22テスト
import dht

def test_dht22_pin(pin_num):
    print(f"\nDHT22テスト GPIO{pin_num}:")
    try:
        sensor = dht.DHT22(machine.Pin(pin_num, machine.Pin.OUT, machine.Pin.PULL_UP))
        print(f"  初期化成功")

        # 3回測定テスト
        for i in range(3):
            try:
                sensor.measure()
                temp = sensor.temperature()
                humi = sensor.humidity()
                print(f"  測定{i+1}: 温度={temp}°C, 湿度={humi}% ✓")
                return True
            except Exception as e:
                print(f"  測定{i+1}: エラー - {e}")
                time.sleep(3)  # DHT22復旧待機
        return False
    except Exception as e:
        print(f"  初期化エラー: {e}")
        return False

# 推奨ピンでのテスト
test_pins = [1, 2, 4, 5, 15, 16]
working_pins = []

for pin in test_pins:
    if test_dht22_pin(pin):
        working_pins.append(pin)

print(f"\n=== 結果 ===")
print(f"動作するピン: {working_pins}")

if not working_pins:
    print("\n✗ 全てのピンで失敗 - ハードウェア問題の可能性:")
    print("  1. DHT22センサーの故障")
    print("  2. プルアップ抵抗の不備（4.7KΩ-10KΩ必要）")
    print("  3. 配線の接続不良")
    print("  4. 電源供給の問題（3.3V不安定）")
else:
    print(f"\n✓ GPIO{working_pins[0]} が推奨です")