"""
ESP32-S3 DHT センサー診断ツール

目的:
- GPIO候補・内部プルアップの有無・センサー種別（DHT22/DHT11）を総当たりで試し、
  読み取りが成功する組み合わせを見つける。

使い方:
- このファイルをThonnyで開いて実行するだけです。
- 最初に見つかった成功パターンを表示し、実運用の設定例を出力します。
"""

import time
import machine
import dht


def _sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except Exception:
        time.sleep(ms / 1000)


GPIO_CANDIDATES = [4, 5, 13, 14, 15, 16, 17, 18, 19, 21]
PULLUP_OPTIONS = [False, True]
SENSOR_TYPES = [("DHT22", dht.DHT22), ("DHT11", dht.DHT11)]


def make_sensor(pin_no, use_pullup, sensor_cls):
    if use_pullup:
        pin = machine.Pin(pin_no, machine.Pin.IN, machine.Pin.PULL_UP)
    else:
        pin = machine.Pin(pin_no)
    return sensor_cls(pin)


def read_once(sensor):
    try:
        _sleep_ms(60)
        sensor.measure()
        t = sensor.temperature()
        h = sensor.humidity()
        if not (-40 <= t <= 80) or not (0 <= h <= 100):
            return None
        return (t, h)
    except Exception:
        return None


def main():
    print("==============================")
    print("DHT Diagnose (ESP32-S3)")
    print("試行: GPIO={}, PullUp={}, Type={}".format(GPIO_CANDIDATES, PULLUP_OPTIONS, [n for n, _ in SENSOR_TYPES]))
    print("==============================")

    # 起動直後安定待ち
    time.sleep(2)

    for pin in GPIO_CANDIDATES:
        for use_pullup in PULLUP_OPTIONS:
            for name, cls in SENSOR_TYPES:
                print("\n-- 試行: GPIO{} pullup={} type={} --".format(pin, use_pullup, name))
                try:
                    sensor = make_sensor(pin, use_pullup, cls)
                    ok = False
                    for attempt in range(3):
                        res = read_once(sensor)
                        if res:
                            t, h = res
                            ok = True
                            print("成功: 気温 {:.1f}°C 湿度 {:.1f}% (attempt {})".format(t, h, attempt + 1))
                            break
                        else:
                            print("…失敗 (attempt {})".format(attempt + 1))
                            time.sleep(1)
                    if ok:
                        print("\n推奨設定:")
                        print("- DHT_PIN = {}".format(pin))
                        print("- USE_INTERNAL_PULLUP = {}".format(use_pullup))
                        print("- センサー種別 = {} (dht.{})".format(name, name))
                        print("\nこの組み合わせを dht22_simple.py や main.py に反映してください。")
                        return
                except Exception as e:
                    print("初期化エラー:", e)

    print("\nすべての組み合わせで読み取りに失敗しました。以下を確認してください:")
    print("- 配線: VCC=3.3V, GND共通, DATAは候補GPIOへ")
    print("- プルアップ: DATA-3.3V間に 4.7kΩ〜10kΩ。内部/外部のどちらか一方を使用")
    print("- センサー種別: 実体が DHT11 の可能性 → DHT11でも自動試行しています")
    print("- ケーブル長: 短くする / ノイズ対策")
    print("- 別のGPIOや別個体のセンサーで再度テスト")


if __name__ == "__main__":
    main()
