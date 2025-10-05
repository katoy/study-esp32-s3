# simple_test.py - 簡単な光センサーテスト（入力待ちなし）
from machine import Pin
import time

# ESP32/ESP32-S3 両対応設定（GPIO18/19は両方で動作）
CHARGE_PIN = 18  # GPIO18 - ESP32/S3両対応
SENSE_PIN = 19   # GPIO19 - ESP32/S3両対応
TIMEOUT_US = 100000  # 100ms

def read_light_simple():
    """簡単な光レベル測定（診断機能付き）"""
    try:
        # 両方を出力モードで充電
        charge_pin = Pin(CHARGE_PIN, Pin.OUT)
        sense_pin = Pin(SENSE_PIN, Pin.OUT)

        # 強力充電: charge_pin=HIGH, sense_pin=LOW
        charge_pin.value(1)
        sense_pin.value(0)
        time.sleep_ms(50)  # 十分な充電時間

        # 測定モードに切り替え
        sense_pin = Pin(SENSE_PIN, Pin.IN)
        charge_pin = Pin(CHARGE_PIN, Pin.IN)

        # 充電状態確認
        initial_value = sense_pin.value()
        if initial_value == 0:
            print(f"⚠️ 充電失敗: sense_pin = {initial_value}")
            return -2

        # 放電測定
        start_time = time.ticks_us()
        while sense_pin.value() == 1:
            elapsed = time.ticks_diff(time.ticks_us(), start_time)
            if elapsed > TIMEOUT_US:
                return TIMEOUT_US  # タイムアウト

        discharge_time = time.ticks_diff(time.ticks_us(), start_time)
        return discharge_time

    except Exception as e:
        print(f"エラー: {e}")
        return -1
    finally:
        # クリーンアップ
        try:
            charge_pin = Pin(CHARGE_PIN, Pin.OUT)
            sense_pin = Pin(SENSE_PIN, Pin.OUT)
            charge_pin.value(0)
            sense_pin.value(0)
        except:
            pass

def get_brightness_level(value):
    """明るさレベルを判定"""
    if value < 500:
        return "Very Bright ☀️"
    elif value < 2000:
        return "Bright"
    elif value < 8000:
        return "Dim"
    elif value < 20000:
        return "Dark"
    else:
        return "Very Dark 🌙"

print("🔴 ESP32/ESP32-S3 + Red LED Light Sensor Test")
print("=============================================")

# 基本GPIO診断
print("🔧 GPIO診断中...")
test_pin18 = Pin(18, Pin.OUT)
test_pin19 = Pin(19, Pin.OUT)

test_pin18.value(1)
test_pin19.value(0)
time.sleep_ms(10)

test_pin18_read = Pin(18, Pin.IN).value()
test_pin19_read = Pin(19, Pin.IN).value()

print(f"GPIO18: 設定=HIGH, 読み取り={test_pin18_read}")
print(f"GPIO19: 設定=LOW, 読み取り={test_pin19_read}")

if test_pin18_read == 1 and test_pin19_read == 0:
    print("✅ GPIO正常動作")
else:
    print("❌ GPIO問題あり - さらに異なるピンを試す必要")
    # 代替ピンテスト
    alt_pins = [(2, 15), (12, 13), (25, 26), (32, 33)]
    for charge, sense in alt_pins:
        try:
            cp = Pin(charge, Pin.OUT)
            sp = Pin(sense, Pin.OUT)
            cp.value(1)
            sp.value(0)
            time.sleep_ms(5)
            cr = Pin(charge, Pin.IN).value()
            sr = Pin(sense, Pin.IN).value()
            print(f"  代替テスト GPIO{charge}/{sense}: {cr}/{sr}")
            if cr == 1 and sr == 0:
                print(f"  ✅ GPIO{charge}/{sense} 動作OK - このピンを使用推奨")
                break
        except:
            continue

print("Cover LED with hand or shine light to see changes")
print("Press Ctrl+C to stop")
print()

# 連続測定
measurement_count = 0
while True:
    try:
        light_value = read_light_simple()
        measurement_count += 1

        if light_value > 0:
            brightness = get_brightness_level(light_value)
            print(f"[{measurement_count:3d}] Light: {light_value:5d}μs -> {brightness}")
        else:
            print(f"[{measurement_count:3d}] Measurement failed")

        time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Test stopped")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)

print("Test completed!")