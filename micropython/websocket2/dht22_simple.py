"""
ESP32-S3 + DHT22 超シンプル読み取りプログラム

使い方:
- Thonny でこのファイルを開いて実行
- 配線に合わせて DHT_PIN と USE_INTERNAL_PULLUP を必要に応じて変更

表示形式: 「気温 27.6°C 湿度 50.1%」を1行で出力
"""

import machine
import time
import dht

# 設定 ------------------------------------------------------
DHT_PIN = 4                  # DATA を接続した GPIO 番号
USE_INTERNAL_PULLUP = False  # 外付けプルアップを使う場合は False（推奨）
READ_INTERVAL_SEC = 5        # 読み取り間隔（秒）
AUTO_TRY_DHT11 = True        # DHT22が失敗時にDHT11も試す


def _sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except Exception:
        time.sleep(ms / 1000)


def make_sensor(cls):
    if USE_INTERNAL_PULLUP:
        pin = machine.Pin(DHT_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
    else:
        pin = machine.Pin(DHT_PIN)
    return cls(pin)


def read_once(sensor):
    """1回だけ読み取り。成功時は (temp_c, hum_pct)、失敗時は None を返す。"""
    try:
        _sleep_ms(60)  # 測定直前のごく短い待機で安定化
        sensor.measure()
        t = sensor.temperature()
        h = sensor.humidity()
        # 簡易妥当性チェック
        if not (-40 <= t <= 80) or not (0 <= h <= 100):
            print("⚠️ 無効データ: t=", t, " h=", h)
            return None
        return (t, h)
    except Exception as e:
        print("❌ 読み取りエラー:", e)
        return None


def main():
    print("==============================")
    print("DHT22 Simple Reader (ESP32-S3)")
    print("PIN=GPIO{}  internal_pullup={}".format(DHT_PIN, USE_INTERNAL_PULLUP))
    print("==============================")

    sensor = make_sensor(dht.DHT22)
    # 起動直後は不安定になりやすいので少し待つ
    time.sleep(4)

    count = 0
    try:
        while True:
            count += 1
            result = read_once(sensor)
            if result is not None:
                t, h = result
                print("#{} 気温 {:.1f}°C 湿度 {:.1f}%".format(count, t, h))
            else:
                if AUTO_TRY_DHT11:
                    # DHT22失敗時にDHT11で再試行（その回だけ）
                    print("#{} DHT22失敗 → DHT11を試します".format(count))
                    sensor = make_sensor(dht.DHT11)
                    time.sleep(1)
                    result = read_once(sensor)
                    if result is not None:
                        t, h = result
                        print("#{} (DHT11) 気温 {:.1f}°C 湿度 {:.1f}%".format(count, t, h))
                        # 次回は再びDHT22に戻す
                        sensor = make_sensor(dht.DHT22)
                    else:
                        print("#{} センサー読み取り失敗".format(count))

            time.sleep(READ_INTERVAL_SEC)
    except KeyboardInterrupt:
        print("\n停止しました")


if __name__ == "__main__":
    main()
