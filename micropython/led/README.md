# ESP32-S3-Zero LED制御プロジェクト

このプロジェクトは、ESP32-S3-Zeroボード上のWS2812 RGB LEDを制御するためのMicroPythonサンプルコード集です。

## ボード情報

- https://www.waveshare.com/wiki/ESP32-S3-Zero#Hardware_Connection
- WS2812 RGB LED（GPIO21に接続）

## ファイル構成と機能

### `led.py`
基本的なWS2812 LED制御のサンプルコード
- **機能**: 赤、緑、青の順に1秒ずつ点灯し、1秒消灯を繰り返す
- **特徴**: シンプルなNeoPixel制御の基本例
- **用途**: WS2812 LEDの動作確認や基本的な制御方法の学習

### `led-pwm.py`
高度なWS2812 LED制御のサンプルコード
- **機能**: 虹色（レインボー）アニメーションを実行
- **特徴**:
  - 色相環による滑らかな色変化
  - 明るさ調整機能
  - エラーハンドリング（Ctrl-C時の適切な終了処理）
  - 設定パラメーターによる調整が可能
- **用途**: 美しい視覚効果の実装や高度なLED制御の学習

### `mem-size.py`
ESP32-S3のメモリ情報を表示するユーティリティ
- **機能**: フラッシュサイズとPSRAMの情報を表示
- **特徴**:
  - フラッシュメモリサイズの確認
  - ヒープ領域の詳細情報
  - PSRAM（外部メモリ）の検出と容量表示
- **用途**: デバッグやメモリ使用量の監視、ハードウェア仕様の確認



```
/Applications/Thonny.app/Contents/Frameworks/Python.framework/Versions/3.10/bin/python3.10 -u -m esptool \
  --port /dev/cu.usbmodem11201 --chip esp32s3 --before usb_reset --after no_reset \
  erase_flash
```

```
/Applications/Thonny.app/Contents/Frameworks/Python.framework/Versions/3.10/bin/python3.10 -u -m esptool \
  --port /dev/cu.usbmodem11201 --chip esp32s3 --baud 460800 \
  --before usb_reset --after hard_reset \
  write_flash -z 0x0 /Users/katoy/Downloads/ESP32_GENERIC_S3-SPIRAM_OCT-20250911-v1.26.1.bin
```


## 使用方法

1. Thonny IDEまたは他のMicroPython対応エディタでファイルを開く
2. ESP32-S3-ZeroボードにMicroPythonファームウェアが書き込まれていることを確認
3. 各ファイルをボードに転送して実行

### 実行例
```python
# led.py の実行
exec(open('led.py').read())

# led-pwm.py の実行（虹色アニメーション）
exec(open('led-pwm.py').read())

# メモリ情報の確認
exec(open('mem-size.py').read())
```

## MicroPythonファームウェアの書き込み

### フラッシュメモリの消去
```bash
/Applications/Thonny.app/Contents/Frameworks/Python.framework/Versions/3.10/bin/python3.10 -u -m esptool \
  --port /dev/cu.usbmodem11201 --chip esp32s3 --before usb_reset --after no_reset \
  erase_flash
```

### ファームウェアの書き込み
```bash
/Applications/Thonny.app/Contents/Frameworks/Python.framework/Versions/3.10/bin/python3.10 -u -m esptool \
  --port /dev/cu.usbmodem11201 --chip esp32s3 --baud 460800 \
  --before usb_reset --after hard_reset \
  write_flash -z 0x0 /Users/katoy/Downloads/ESP32_GENERIC_S3-SPIRAM_OCT-20250911-v1.26.1.bin
```

## 参考資料

- https://noriwtn.com/servofs90r-arduino/
  Arduinoで連続回転サーボFS90Rを動かしてみる
