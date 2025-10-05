# main.py - ESP32 LED Light Sensor (Simple & Working Version)
from machine import Pin
import time

# ESP32/ESP32-S3 両対応設定（GPIO18/19は両方で動作）
CHARGE_PIN = 18  # GPIO18 - 充電用（ESP32/S3両対応）
SENSE_PIN = 19   # GPIO19 - センサー用（ESP32/S3両対応）
TIMEOUT_US = 100000  # 100ms タイムアウト
MEASUREMENT_INTERVAL = 1  # 測定間隔（秒）

# 明るさ判定の閾値
VERY_BRIGHT_THRESHOLD = 500    # 明るい光（スマホライトなど）
BRIGHT_THRESHOLD = 2000        # 通常の室内照明
DIM_THRESHOLD = 8000           # 薄暗い環境
DARK_THRESHOLD = 20000         # 暗い環境

def read_light_level():
    """
    LEDを光センサーとして使い、光のレベルを測定する
    戻り値: 放電にかかった時間（マイクロ秒）。数値が小さいほど明るい。
           エラー時は -1 を返す。
    """
    try:
        # LED充電: 両方を出力モードにして充電
        charge_pin = Pin(CHARGE_PIN, Pin.OUT)
        sense_pin = Pin(SENSE_PIN, Pin.OUT)

        # 強力充電: charge_pin=HIGH, sense_pin=LOW
        charge_pin.value(1)
        sense_pin.value(0)
        time.sleep_ms(50)  # 十分な充電時間

        # 測定モードに切り替え（両方を入力モード）
        sense_pin = Pin(SENSE_PIN, Pin.IN)
        charge_pin = Pin(CHARGE_PIN, Pin.IN)

        # 充電状態確認
        initial_value = sense_pin.value()
        if initial_value == 0:
            return -2  # 充電失敗

        # 放電時間測定
        start_time = time.ticks_us()
        while sense_pin.value() == 1:
            elapsed = time.ticks_diff(time.ticks_us(), start_time)
            if elapsed > TIMEOUT_US:
                return TIMEOUT_US  # タイムアウト

        discharge_time = time.ticks_diff(time.ticks_us(), start_time)
        return discharge_time

    except Exception as e:
        print(f"測定エラー: {e}")
        return -1
    finally:
        # GPIO クリーンアップ
        try:
            charge_pin = Pin(CHARGE_PIN, Pin.OUT)
            sense_pin = Pin(SENSE_PIN, Pin.OUT)
            charge_pin.value(0)
            sense_pin.value(0)
        except:
            pass

def get_light_description(light_level):
    """明るさレベルの説明を返す"""
    if light_level < 0:
        return "エラー ❌"
    elif light_level < VERY_BRIGHT_THRESHOLD:
        return "Very Bright ☀️"
    elif light_level < BRIGHT_THRESHOLD:
        return "Bright"
    elif light_level < DIM_THRESHOLD:
        return "Dim"
    elif light_level < DARK_THRESHOLD:
        return "Dark"
    else:
        return "Very Dark 🌙"

def gpio_test():
    """GPIO基本動作テスト"""
    print("🔧 GPIO動作テスト...")

    # GPIO18 テスト
    test_pin18 = Pin(18, Pin.OUT)
    test_pin18.value(1)
    time.sleep_ms(10)
    test_pin18_read = Pin(18, Pin.IN).value()

    # GPIO19 テスト
    test_pin19 = Pin(19, Pin.OUT)
    test_pin19.value(0)
    time.sleep_ms(10)
    test_pin19_read = Pin(19, Pin.IN).value()

    print(f"GPIO18: 設定=HIGH, 読み取り={test_pin18_read}")
    print(f"GPIO19: 設定=LOW, 読み取り={test_pin19_read}")

    if test_pin18_read == 1 and test_pin19_read == 0:
        print("✅ GPIO正常動作")
        return True
    else:
        print("❌ GPIO問題あり")
        # 代替ピン自動検出
        print("🔍 代替ピン検索中...")
        alt_pins = [(2, 15), (12, 13), (21, 22), (32, 33)]
        for charge, sense in alt_pins:
            try:
                cp = Pin(charge, Pin.OUT)
                sp = Pin(sense, Pin.OUT)
                cp.value(1)
                sp.value(0)
                time.sleep_ms(5)
                cr = Pin(charge, Pin.IN).value()
                sr = Pin(sense, Pin.IN).value()
                print(f"  テスト GPIO{charge}/{sense}: {cr}/{sr}")
                if cr == 1 and sr == 0:
                    print(f"  ✅ GPIO{charge}/{sense} 動作OK!")
                    print(f"  📝 配線を GPIO{charge}(+) / GPIO{sense}(-) に変更してください")
                    return False  # 配線変更が必要
            except Exception:
                continue
        return False

def main():
    """メイン実行関数"""
    print("=" * 50)
    print("🔴 ESP32/ESP32-S3 LED Light Sensor")
    print("=" * 50)
    print("📡 使用ピン: GPIO18(充電) / GPIO19(センサー)")
    print("🔴 赤色LED必須")
    print("⚡ ESP32/ESP32-S3 両対応")
    print()

    # GPIO動作確認
    if not gpio_test():
        print("⚠️ GPIO問題により正常動作しない可能性があります")

    print()
    print("📊 光センサー測定開始...")
    print("💡 LEDに手をかざしたり、ライトを当てたりして値の変化を確認してください")
    print("🛑 停止: Ctrl+C")
    print()

    # 連続測定
    measurement_count = 0
    try:
        while True:
            measurement_count += 1

            # 光レベル測定
            light_value = read_light_level()

            # 結果表示
            if light_value >= 0:
                description = get_light_description(light_value)
                print(f"[{measurement_count:3d}] Light: {light_value:5d}μs -> {description}")
            else:
                print(f"[{measurement_count:3d}] 測定失敗 (エラーコード: {light_value})")

            # 測定間隔
            time.sleep(MEASUREMENT_INTERVAL)

    except KeyboardInterrupt:
        print()
        print("🛑 測定停止")
        print("📊 測定完了!")
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")

# プログラム起動
if __name__ == "__main__":
    main()