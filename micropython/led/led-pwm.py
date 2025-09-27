"""
ESP32-S3-Zero 内蔵 WS2812 (NeoPixel, GPIO21) 制御デモ。

機能:
- 0〜255 の色相っぽい値を巡回させ、虹色に変化させます。
- 明るさは dim_color() で一括スケーリングします。
- プログラム終了時（Ctrl-C 含む）は必ず LED を消灯します。

使い方:
- Thonny 等で本スクリプトを保存し実行（main.py にすると起動時自動実行）。
- 定数 BRIGHTNESS, STEP, SLEEP_SEC をお好みで調整してください。
"""

import time
from machine import Pin
import neopixel

# ===== 設定（リンター対策で魔法数を排除） =====
PIN_WS2812 = 21       # 内蔵 NeoPixel の信号ピン
NUM_PIXELS = 1        # 内蔵は 1 個
BRIGHTNESS = 0.30     # 明るさ（0.0〜1.0）
STEP = 5              # 色インデックスの増分（大きいほどカクカク速く）
SLEEP_SEC = 0.05      # 変化の待ち時間（秒）

# NeoPixel インスタンス
np = neopixel.NeoPixel(Pin(PIN_WS2812), NUM_PIXELS)


def wheel(pos: int) -> tuple[int, int, int]:
    """
    0〜255 の値を RGB タプルに変換する簡易関数。
    値は 0〜255 にクランプ。戻り値は (R, G, B) 各 0〜255。
    """
    # 入力をクランプ
    if pos < 0:
        pos = 0
    elif pos > 255:
        pos = 255

    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def dim_color(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """
    RGB を factor 倍に減衰させ、0〜255 に丸める。
    """
    r, g, b = color
    r = int(r * factor)
    g = int(g * factor)
    b = int(b * factor)

    # 0〜255 にクリップ
    if r < 0:
        r = 0
    elif r > 255:
        r = 255
    if g < 0:
        g = 0
    elif g > 255:
        g = 255
    if b < 0:
        b = 0
    elif b > 255:
        b = 255

    return (r, g, b)


def set_pixel(rgb: tuple[int, int, int]) -> None:
    """1 個の NeoPixel に色を設定して送信する。"""
    np[0] = rgb
    np.write()


def main() -> None:
    """虹色アニメーションのメインループ。"""
    i = 0
    while True:
        set_pixel(dim_color(wheel(i), BRIGHTNESS))
        time.sleep(SLEEP_SEC)
        i += STEP
        if i >= 256:
            i = 0


if __name__ == "__main__":
    try:
        main()
    finally:
        # どんな終了経路でも消灯しておく（Ctrl-C, 例外, 正常終了）
        set_pixel((0, 0, 0))
