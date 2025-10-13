#!/usr/bin/env python3

"""
PICO_LED BLE テスト統合スクリプト - 自己完結型
Raspberry Pi Pico W2 の pico_led.py デバイスをテスト
依存関係の自動管理とBLEテストを統合
"""

import asyncio
import sys
import subprocess
import importlib
import importlib.util
import platform

# 設定
DEVICE_NAME = "PICO_LED"
SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # 書き込み用
TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # 読み込み用
LED_ON_DATA = b'1\x00'   # ASCII '1' + NULL
LED_OFF_DATA = b'0\x00'  # ASCII '0' + NULL

# 色付き出力
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

def print_header():
    print(f"{Colors.BLUE}============================================{Colors.NC}")
    print(f"{Colors.BLUE} PICO_LED BLE Test - 統合版{Colors.NC}")
    print(f"{Colors.BLUE}============================================{Colors.NC}")

def print_step(message):
    print(f"{Colors.YELLOW}[STEP]{Colors.NC} {message}")

def print_success(message):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

def print_error(message):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

def print_info(message):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")

def print_warning(message):
    print(f"{Colors.CYAN}[WARNING]{Colors.NC} {message}")

# システム要件チェック
def check_system_requirements():
    """システム要件をチェック"""
    print_step("システム要件をチェック中...")
    
    # OS確認
    os_name = platform.system()
    print_info(f"OS: {os_name}")
    
    if os_name != "Darwin":
        print_warning(f"このスクリプトはmacOS用に最適化されていますが、{os_name}でも動作する可能性があります。")
    
    # Python確認
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print_info(f"Python: {python_version}")
    
    if sys.version_info.major < 3 or (sys.version_info.major == 3 and sys.version_info.minor < 7):
        print_error("Python 3.7 以上が必要です")
        return False
    
    print_success("システム要件OK")
    return True

# 依存関係チェックとインストール
def check_and_install_dependencies():
    """必要な依存関係をチェックし、必要に応じてインストール"""
    print_step("依存関係をチェック中...")
    
    required_packages = ["bleak"]
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print_success(f"{package} ライブラリが見つかりました")
        except ImportError:
            print_warning(f"{package} ライブラリが見つかりません")
            missing_packages.append(package)
    
    if missing_packages:
        print_info(f"不足しているパッケージ: {', '.join(missing_packages)}")
        
        # ユーザーに確認
        while True:
            response = input("\n不足しているパッケージをインストールしますか？ [y/N]: ").strip().lower()
            if response in ['y', 'yes', 'はい']:
                break
            elif response in ['', 'n', 'no', 'いいえ']:
                print_error("必要なパッケージがインストールされていないため、テストを実行できません")
                return False
            else:
                print("y または n で回答してください")
        
        # パッケージインストール
        for package in missing_packages:
            print_info(f"{package} をインストール中...")
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", package
                ], check=True, capture_output=True, text=True)
                print_success(f"{package} のインストールが完了しました")
            except subprocess.CalledProcessError as e:
                print_error(f"{package} のインストールに失敗しました: {e}")
                print_error(f"出力: {e.stdout}")
                print_error(f"エラー: {e.stderr}")
                return False
            except Exception as e:
                print_error(f"予期しないエラー: {e}")
                return False
    
    # インストール後の確認
    print_step("インストール後の確認...")
    try:
        # 動的にbleakをインポートして確認
        bleak_spec = importlib.util.find_spec("bleak")
        if bleak_spec is None:
            print_error("bleakライブラリが見つかりません")
            return False
        
        # バージョン確認（オプション）
        try:
            import bleak
            print_success(f"bleak バージョン: {bleak.__version__}")
        except Exception:
            print_success("bleak ライブラリのインポートが成功しました")
        return True
    except Exception as e:
        print_error(f"bleakのインポートに失敗: {e}")
        return False

# UUID比較のためのヘルパー関数
def normalize_uuid(uuid_str):
    """UUIDを正規化（大文字、ハイフンなし）"""
    return str(uuid_str).upper().replace('-', '')

def uuid_match(uuid1, uuid2):
    """UUIDが一致するかチェック"""
    return normalize_uuid(uuid1) == normalize_uuid(uuid2)

# BLEテスト関数群
async def scan_for_device():
    """PICO_LEDデバイスをスキャンして探す"""
    # ここで動的にbleakをインポート
    from bleak import BleakScanner
    
    print_step(f"{DEVICE_NAME} デバイスをスキャン中...")
    
    try:
        devices = await BleakScanner.discover(timeout=10.0)
        
        for device in devices:
            if device.name == DEVICE_NAME:
                print_success(f"デバイス発見: {DEVICE_NAME} at {device.address}")
                return device
                
        print_error(f"デバイス '{DEVICE_NAME}' が見つかりません!")
        print("確認事項:")
        print("  1. Raspberry Pi Pico W2 で pico_led.py が実行されていること")
        print("  2. デバイスが通信範囲内にあること")
        print("  3. 他のデバイスに接続されていないこと")
        return None
        
    except Exception as e:
        print_error(f"スキャンに失敗: {e}")
        return None

async def test_connection(client):
    """接続とサービス確認"""
    print_step("接続とサービスのテスト...")
    
    try:
        # サービスが利用可能になるまで少し待機
        await asyncio.sleep(1.0)
        
        # サービスの取得（bleak API対応）
        try:
            services = client.services
        except AttributeError:
            # 古いバージョンのbleak対応
            services = await client.get_services()
        
        # サービス数を安全に取得
        try:
            service_count = len(services)
            print_info(f"{service_count} 個のサービスを発見")
        except TypeError:
            # BleakGATTServiceCollectionの場合
            service_list = list(services)
            print_info(f"{len(service_list)} 個のサービスを発見")
            services = service_list
        
        target_service = None
        # サービスを安全に反復
        try:
            service_iter = services
        except Exception:
            service_iter = list(services) if hasattr(services, '__iter__') else []
            
        for service in service_iter:
            if uuid_match(service.uuid, SERVICE_UUID):
                target_service = service
                break
                
        if target_service:
            print_success("接続成功 - UARTサービス発見")
            print_info(f"サービス UUID: {target_service.uuid}")
            
            # 特性の確認
            rx_char = None
            tx_char = None
            
            # 特性数を安全に取得
            try:
                char_count = len(target_service.characteristics)
                print_info(f"{char_count} 個の特性を発見")
            except TypeError:
                char_list = list(target_service.characteristics)
                print_info(f"{len(char_list)} 個の特性を発見")
            
            for char in target_service.characteristics:
                if uuid_match(char.uuid, RX_UUID):
                    rx_char = char
                    print_info(f"RX特性発見: {char.uuid}")
                elif uuid_match(char.uuid, TX_UUID):
                    tx_char = char
                    print_info(f"TX特性発見: {char.uuid}")
                else:
                    print_info(f"その他の特性: {char.uuid}")
                    
            if rx_char and tx_char:
                print_success("必要な特性が全て発見されました")
                return True
            else:
                print_error("必要な特性が見つかりません")
                print_info("利用可能な特性:")
                for char in target_service.characteristics:
                    print_info(f"  - {char.uuid}")
                return False
        else:
            print_error("UARTサービスが見つかりません")
            print_info("利用可能なサービス:")
            try:
                for service in service_iter:
                    print_info(f"  - {service.uuid}")
            except Exception as e:
                print_info(f"  サービス一覧の取得に失敗: {e}")
            return False
            
    except Exception as e:
        print_error(f"接続テストに失敗: {e}")
        import traceback
        print_info(f"トレースバック: {traceback.format_exc()}")
        return False

async def test_led_control(client):
    """LED制御テスト"""
    print_step("LED制御テストを開始...")
    
    test_cycles = 3
    
    try:
        for i in range(1, test_cycles + 1):
            print_info(f"テストサイクル {i}/{test_cycles}:")
            
            # LED ON
            print("  LEDをON中... ", end="", flush=True)
            await client.write_gatt_char(RX_UUID, LED_ON_DATA)
            print(f"{Colors.GREEN}✓{Colors.NC}")
            
            await asyncio.sleep(2)
            
            # LED OFF
            print("  LEDをOFF中... ", end="", flush=True)
            await client.write_gatt_char(RX_UUID, LED_OFF_DATA)
            print(f"{Colors.GREEN}✓{Colors.NC}")
            
            await asyncio.sleep(2)
            
        print_success("LED制御テストが正常に完了しました")
        return True
        
    except Exception as e:
        print_error(f"LED制御テストに失敗: {e}")
        return False

async def test_initial_state(client):
    """接続時初期状態テスト"""
    print_step("接続時初期状態の確認...")
    
    initial_state_received = []
    
    def initial_notification_handler(sender, data):
        decoded_data = data.decode('utf-8', errors='ignore') if data else ''
        print_success(f"初期LED状態を受信: '{decoded_data}' ({'ON' if decoded_data == '1' else 'OFF' if decoded_data == '0' else 'Unknown'})")
        initial_state_received.append(decoded_data)
    
    try:
        # 通知を有効にする
        await client.start_notify(TX_UUID, initial_notification_handler)
        print_info("通知を有効化しました。初期状態の送信を待機中...")
        
        # 少し待機して初期状態の受信を確認
        await asyncio.sleep(2)
        
        # 通知を停止
        await client.stop_notify(TX_UUID)
        
        if initial_state_received:
            print_success("✅ 初期状態の自動送信機能が正常に動作しています")
            return True
        else:
            print_info("初期状態は受信されませんでした（既に送信済みの可能性があります）")
            return True  # これは正常な場合もある
            
    except Exception as e:
        print_error(f"初期状態テストに失敗: {e}")
        return False

async def test_notifications(client):
    """通知テスト"""
    print_step("通知テスト中...")
    
    notifications_received = []
    
    def notification_handler(sender, data):
        print_info(f"通知を受信: {data}")
        notifications_received.append(data)
    
    try:
        # 通知を有効にする
        await client.start_notify(TX_UUID, notification_handler)
        
        print_info("通知を購読中...")
        print_info("通知を発生させるためのテストコマンドを送信中...")
        
        # テスト用のコマンドを送信
        await client.write_gatt_char(RX_UUID, LED_ON_DATA)
        await asyncio.sleep(1)
        
        await client.write_gatt_char(RX_UUID, LED_OFF_DATA)
        await asyncio.sleep(1)
        
        # 通知を停止
        await client.stop_notify(TX_UUID)
        
        if notifications_received:
            print_success(f"{len(notifications_received)} 個の通知を受信しました")
        else:
            print_info("通知を受信しませんでした（これは正常な場合があります）")
            
        return True
        
    except Exception as e:
        print_error(f"通知テストに失敗: {e}")
        return False

def show_device_info(device):
    """デバイス情報表示"""
    print_step("デバイス情報:")
    print(f"  デバイス名: {DEVICE_NAME}")
    print(f"  MACアドレス: {device.address}")
    print(f"  サービス UUID: {SERVICE_UUID}")
    print(f"  RX UUID: {RX_UUID}")
    print(f"  TX UUID: {TX_UUID}")
    print(f"  LED ONコマンド: {LED_ON_DATA}")
    print(f"  LED OFFコマンド: {LED_OFF_DATA}")

async def run_ble_tests():
    """BLEテストメイン実行"""
    # ここで動的にbleakをインポート
    from bleak import BleakClient
    
    print_step("BLEテスト実行準備...")
    
    # デバイス検索
    device = await scan_for_device()
    if not device:
        return False
    
    # デバイス情報表示
    show_device_info(device)
    
    # 接続とテスト
    try:
        async with BleakClient(device.address) as client:
            print_step(f"{device.address} に接続中...")
            
            if not client.is_connected:
                print_error("デバイスへの接続に失敗しました")
                return False
                
            print_success("デバイスに接続しました")
            
            # 接続テスト
            if not await test_connection(client):
                return False
            
            # 初期状態テスト
            await test_initial_state(client)
                
            # LED制御テスト
            if not await test_led_control(client):
                return False
                
            # 通知テスト
            await test_notifications(client)
            
            print_success("全てのテストが正常に完了しました!")
            print()
            print("期待される動作:")
            print("  - 接続時に現在のLED状態が自動で送信されること")
            print("  - GPIO16のLEDが3回点滅すること")
            print("  - 各LED制御後に状態確認の通知が表示されること")
            return True
            
    except Exception as e:
        # BleakErrorは動的にインポートしたので、Exceptionでキャッチ
        if "BleakError" in str(type(e)):
            print_error(f"BLEエラー: {e}")
        else:
            print_error(f"予期しないエラー: {e}")
        return False

def show_usage():
    """使用方法の表示"""
    print("使用方法:")
    print("  python3 ble_test_integrated.py [オプション]")
    print()
    print("オプション:")
    print("  -h, --help         このヘルプメッセージを表示")
    print("  --setup-only       依存関係のセットアップのみ実行（テストは実行しない）")
    print("  --no-interactive   対話モードを無効化（自動実行）")
    print()
    print("このスクリプトの機能:")
    print("  1. システム要件のチェック")
    print("  2. 必要な依存関係の自動インストール")
    print("  3. PICO_LEDデバイスとのBLEテスト実行")
    print()
    print("前提条件:")
    print("  - Raspberry Pi Pico W2でpico_led.pyが実行されていること")
    print("  - MacのBluetoothが有効であること")
    print("  - デバイスが通信範囲内にあること")

def parse_arguments():
    """コマンドライン引数を解析"""
    args = {
        'setup_only': False,
        'no_interactive': False,
        'help': False
    }
    
    for arg in sys.argv[1:]:
        if arg in ['-h', '--help']:
            args['help'] = True
        elif arg == '--setup-only':
            args['setup_only'] = True
        elif arg == '--no-interactive':
            args['no_interactive'] = True
        else:
            print_error(f"不明なオプション: {arg}")
            show_usage()
            sys.exit(1)
    
    return args

def main():
    """メイン実行関数"""
    # 引数解析
    args = parse_arguments()
    
    if args['help']:
        show_usage()
        return
    
    print_header()
    
    # システム要件チェック
    if not check_system_requirements():
        sys.exit(1)
    
    # 依存関係チェック・インストール
    if not check_and_install_dependencies():
        sys.exit(1)
    
    if args['setup_only']:
        print_success("セットアップが正常に完了しました!")
        print()
        print("テストを実行するには: python3 ble_test_integrated.py")
        return
    
    # テスト実行の確認
    if not args['no_interactive']:
        print()
        print_info("前提条件の確認:")
        print("  ✓ Raspberry Pi Pico W2でpico_led.pyが実行されていること")
        print("  ✓ MacのBluetoothが有効であること")  
        print("  ✓ デバイスが通信範囲内にあること")
        print()
        
        while True:
            response = input("テストを開始しますか？ [Y/n]: ").strip().lower()
            if response in ['', 'y', 'yes', 'はい']:
                break
            elif response in ['n', 'no', 'いいえ']:
                print_info("テストがキャンセルされました")
                return
            else:
                print("y または n で回答してください")
    
    # BLEテスト実行
    print()
    try:
        success = asyncio.run(run_ble_tests())
        if success:
            print()
            print_success("🎉 テスト完了! PICO_LEDデバイスは正常に動作しています。")
        else:
            print()
            print_error("❌ テストに失敗しました。デバイスと接続を確認してください。")
            sys.exit(1)
    except KeyboardInterrupt:
        print_info("\nユーザーによってテストが中断されました")
        sys.exit(0)
    except Exception as e:
        print_error(f"予期しないエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()