import time
from machine import Pin
import neopixel

# WS2812 は GPIO21 に接続とされている
PIN = 21
NUM_PIXELS = 1  # LED が1つなら1

np = neopixel.NeoPixel(Pin(PIN), NUM_PIXELS)

def rgb(r, g, b):
    np[0] = (r, g, b)
    np.write()

while True:
    # 赤にする
    rgb(255, 0, 0)
    time.sleep(1)
    # 緑
    rgb(0, 255, 0)
    time.sleep(1)
    # 青
    rgb(0, 0, 255)
    time.sleep(1)
    # 消灯
    rgb(0, 0, 0)
    time.sleep(1)
