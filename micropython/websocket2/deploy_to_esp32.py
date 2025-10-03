#!/usr/bin/env python3
"""
🚀 ESP32-S3 DHT22監視システム 高機能デプロイツール v3.0
=========================================================

ESP32-S3 MicroPython環境への統合システムデプロイメントを自動化するツールです。

📦 主要機能:
- 🔄 差分更新（SHA256ハッシュ比較）
- 🛠️ 自動リトライ＆エラー復旧
- 🔌 ハードウェアリセット制御
- 🆘 緊急復旧モード（フラッシュ消去）
- 📊 デバイス状態監視
- 🧹 不要ファイルクリーンアップ

使い方:
  python3 deploy_to_esp32.py --verify          # 差分更新
  python3 deploy_to_esp32.py --force           # 全ファイル強制更新
  python3 deploy_to_esp32.py --reset           # リセット後デプロイ
  python3 deploy_to_esp32.py --emergency       # 緊急復旧モード
"""

import argparse
import hashlib
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


@dataclass
class DeployConfig:
    """デプロイメント設定"""
    # デバイス設定
    default_port: str = "/dev/cu.usbmodem14101"

    # リトライ設定
    default_retries: int = 3
    default_timeout: int = 10
    retry_wait: float = 2.0

    # ファイル設定
    required_files: List[Path] = None
    safe_mode_files: List[Path] = None
    root_allowlist: set = None

    def __post_init__(self):
        if self.required_files is None:
            self.required_files = [
                # コアシステム
                Path("main.py"),
                Path("simple_websocket.py"),
                Path("thingspeak.py"),
                Path("dht22_lib.py"),
                Path("wifi_config.py"),
                # WebUI
                Path("static/index.html"),
                Path("static/style.css"),
                Path("static/app.js"),
            ]

        if self.safe_mode_files is None:
            self.safe_mode_files = [
                Path("main.py"),
                Path("wifi_config.py"),
            ]

        if self.root_allowlist is None:
            self.root_allowlist = {
                "main.py", "simple_websocket.py", "thingspeak.py",
                "dht22_lib.py", "wifi_config.py", "static",
                "webrepl.py", "webrepl_cfg.py", "boot.py"
            }


@dataclass
class AppState:
    """アプリケーション状態管理"""
    root: Path = Path(__file__).resolve().parent
    args: Optional[argparse.Namespace] = None
    config: DeployConfig = None

    def __post_init__(self):
        if self.config is None:
            self.config = DeployConfig()


class DeploymentError(Exception):
    """デプロイメント専用例外"""
    pass


class ConnectionError(DeploymentError):
    """接続エラー"""
    pass


class HashError(DeploymentError):
    """ハッシュ計算エラー"""
    pass


# グローバル状態
state = AppState()


def run_cmd(cmd_args, dry_run=False, check=True):
    """コマンド実行ヘルパー"""
    if dry_run:
        print("(dry-run) $", " ".join(map(str, cmd_args)))
        return subprocess.CompletedProcess(cmd_args, 0, "", "")
    return subprocess.run(cmd_args, check=check, text=True, capture_output=True)


def reset_device(port):
    """ESP32デバイスのハードウェアリセット（DTR/RTS制御）"""
    if not SERIAL_AVAILABLE:
        print("[INFO] serialライブラリが利用できません。手動リセットを実行してください。")
        return

    try:
        print("[RESET] ESP32をハードウェアリセット中...")
        with serial.Serial(port, 115200, timeout=1) as ser:
            ser.dtr = False
            ser.rts = True
            time.sleep(0.1)
            ser.rts = False
            time.sleep(0.5)
        print("[INFO] リセット完了")
    except Exception as e:
        print(f"[WARN] リセットに失敗しましたが続行します: {e}")


def check_device(dry_run=False):
    """デバイス接続確認"""
    print("[STEP] デバイス接続を確認中...")
    try:
        mp(["version"], dry_run=dry_run)
        print("[OK] デバイスが応答しました")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] デバイスに接続できません: {e}")
        raise

def mp(args_mp, port=None, dry_run=False, check=True):
    """mpremote 実行ラッパー。必要に応じて connect <port> を前置する。"""
    base = ["mpremote"]
    # デバイス列挙は connect 不要。それ以外は port 指定時に connect を付与
    if port and args_mp and args_mp[0] not in ("devs",):
        base += ["connect", port]
    return run_cmd(base + args_mp, dry_run=dry_run, check=check)

def mp_with_retry(args_mp, port=None, dry_run=False, check=True):
    """リトライ機構付きmpremote実行"""
    config = state.config
    tries = max(1, config.default_retries)
    wait = float(config.retry_wait)

    for attempt in range(1, tries + 1):
        try:
            return mp(args_mp, port=port, dry_run=dry_run, check=check)
        except subprocess.CalledProcessError as e:
            if attempt < tries:
                cmd_str = " ".join(args_mp)
                print(f"[RETRY] mpremote {cmd_str} (試行 {attempt}/{tries}) → {wait}秒後に再試行...")

                # "could not enter raw repl" エラーの場合はより強力なリセットを試行
                if "could not enter raw repl" in str(e):
                    print("[INFO] Raw REPLエラーを検出、強制リセットを実行...")
                    interrupt_esp32_program(port)
                    time.sleep(1)
                    hardware_reset_esp32(port)
                    time.sleep(2)

                time.sleep(wait)
            else:
                raise

def interrupt_esp32_program(port=None):
    """ESP32の実行中プログラムにCtrl+C割り込みを送信"""
    if not SERIAL_AVAILABLE or not port:
        return False

    try:
        print("[INFO] ESP32プログラムに割り込み信号送信中...")
        with serial.Serial(port, 115200, timeout=2) as ser:
            # Ctrl+C (ASCII 3) を複数回送信
            for _ in range(3):
                ser.write(b'\x03')  # Ctrl+C
                time.sleep(0.1)

            # 少し待機してREPLプロンプトを確認
            time.sleep(1)
            ser.write(b'\r\n')  # Enter
            time.sleep(0.5)

            # レスポンスを読み取り
            response = ser.read_all()
            if b'>>>' in response or b'MicroPython' in response:
                print("[SUCCESS] REPLに戻りました")
                return True

        print("[INFO] 割り込み送信完了")
        return True
    except Exception as e:
        print(f"[WARNING] 割り込み送信に失敗: {e}")
        return False

def hardware_reset_esp32(port=None):
    """ESP32にハードウェアリセットを送信（DTR/RTS制御）"""
    if not SERIAL_AVAILABLE:
        print("[WARNING] pyserialが利用できません。 pip install pyserial でインストールしてください")
        return False

    if not port:
        print("[WARNING] ポートが指定されていません")
        return False

    try:
        print("[INFO] ESP32のハードウェアリセットを実行中...")

        # まず割り込み信号を試行
        if interrupt_esp32_program(port):
            time.sleep(1)

        # ESP32のリセット信号（DTR/RTSライン制御）
        with serial.Serial(port, 115200, timeout=1) as ser:
            # ブートローダーモードに入れるための信号
            ser.dtr = False
            ser.rts = True
            time.sleep(0.1)
            ser.rts = False
            time.sleep(0.5)
            ser.dtr = True
            time.sleep(0.1)

        time.sleep(3)  # リセット完了を待機
        print("[INFO] ハードウェアリセット完了")
        return True
    except Exception as e:
        print(f"[WARNING] ハードウェアリセットに失敗しました: {e}")
        return False

def list_devices(dry_run=False):
    """利用可能なデバイスをリスト表示"""
    try:
        res = run_cmd(["mpremote", "devs"], dry_run=dry_run, check=False)
        if res.stdout:
            print("[INFO] 検出デバイス:\n" + res.stdout.strip())
        else:
            print("[INFO] 検出デバイスはありませんでした")
    except Exception:
        pass

def handle_connection_error(e: subprocess.CalledProcessError, port=None, dry_run=False):
    """mpremote接続エラーを処理し、原因を特定してユーザーに案内する"""
    # 1. ホスト側のポートロックをlsofで確認
    try:
        if port and sys.platform != "win32":
            lsof_res = run_cmd(["lsof", port], check=False, dry_run=dry_run)
            if lsof_res.stdout and lsof_res.stdout.strip():
                print(f"\n[ERROR] ポート '{port}' は、以下のプロセスによって使用中のようです。")
                print("--- lsof output ---")
                print(lsof_res.stdout.strip())
                print("-----------------")
                print("このプロセスを終了してから、再度スクリプトを実行してください。\n")
                sys.exit(1)
    except Exception:
        pass

    # 2. Thonnyのプロセスが起動しているか確認
    try:
        ps_res = run_cmd(["ps", "aux"], dry_run=dry_run, check=False)
        if ps_res.stdout and "thonny" in ps_res.stdout.lower():
            print("\n[ERROR] Thonnyのプロセスが実行中です。")
            print("ポートはロックされていませんが、Thonnyがバックグラウンドでデバイスと通信しようとしている可能性があります。")
            print("Thonnyを完全に終了（Quit）してから、再度スクリプトを実行してください。\n")
            sys.exit(1)
    except Exception:
        pass

    # 3. デバイス側のロックアップを疑い、ソフトリセットで復旧を試みる
    if "could not enter raw repl" in (e.stderr or "").lower():
        print("[INFO] デバイスが応答しないため、ソフトリブートを試みます…")
        try:
            mp(["soft-reset"], check=True, dry_run=dry_run)
            if not dry_run:
                time.sleep(2)
            print("[OK] ソフトリブートに成功しました。処理を続行できます。もう一度実行してください。")
            sys.exit(0) # ユーザーに再実行を促す
        except subprocess.CalledProcessError as e2:
            if "could not enter raw repl" in (e2.stderr or ""):
                print("\n[FATAL] ソフトリブートも失敗しました。デバイスが完全に応答しない状態です。")
                print("--- 手動での復旧手順 ---")
                print("1. ESP32ボードの【BOOT】ボタン（または【IO0】）を押したままにします。")
                print("2. そのままの状態で、【RST】ボタン（または【EN】）を一度だけ押して離します。")
                print("3. その後、【BOOT】ボタンを離します。")
                print("4. これでデバイスがブートローダーモードで待機状態になります。")
                print("5. もう一度、このデプロイスクリプトを実行してください。")
                print("\n上記の手順で解決しない場合は、USBケーブルを一度抜き差ししてから、再度お試しください。\n")
                sys.exit(1)

    # 上記のいずれにも当てはまらない場合
    print("[ERROR] 不明なエラーでmpremoteが失敗しました。")
    list_devices()
    raise e

def show_file_transfer_troubleshooting(local_path, remote_path, error):
    """ファイル転送失敗時の詳細なトラブルシューティングガイドを表示"""
    stderr = (error.stderr or "").lower()

    print("\n" + "="*60)
    print("🚨 ファイル転送エラー - 詳細診断と対処法")
    print("="*60)

    # エラー分類と対処法
    if "could not enter raw repl" in stderr:
        print("📋 エラー分類: Raw REPLアクセス失敗")
        print("\n🔧 対処法:")
        print("1. ESP32を手動リセット:")
        print("   - BOOTボタンを押しながらRSTボタンを押して離す")
        print("   - その後BOOTボタンを離す")
        print("2. USBケーブルを抜き差し")
        print("3. 他のアプリケーション（Thonny、Arduino IDE等）を終了")
        print("4. デバイスを再接続してから再実行")

    elif "permission denied" in stderr or "device not found" in stderr:
        print("📋 エラー分類: デバイスアクセス権限エラー")
        print("\n🔧 対処法:")
        print("1. シリアルポートの確認:")
        print("   ls -la /dev/cu.usbmodem*")
        print("2. 権限の確認:")
        print(f"   sudo chmod 666 {getattr(ARGS, 'port', '/dev/cu.usbmodem*')}")
        print("3. デバイスリストの確認:")
        print("   mpremote devs")

    elif "no space left" in stderr or "disk full" in stderr:
        print("📋 エラー分類: ESP32ストレージ不足")
        print("\n🔧 対処法:")
        print("1. 不要ファイルの削除:")
        print("   mpremote fs ls")
        print("   mpremote fs rm <不要ファイル>")
        print("2. フラッシュメモリのクリーンアップ:")
        print("   mpremote fs rmdir static  # 必要に応じて")
        print("3. 緊急復旧モードでの最小ファイル転送:")
        print("   python3 deploy_to_esp32.py --emergency")

    elif "timeout" in stderr:
        print("📋 エラー分類: 通信タイムアウト")
        print("\n🔧 対処法:")
        print("1. USBケーブルの確認（データ転送対応ケーブル使用）")
        print("2. 別のUSBポートを試す")
        print("3. タイムアウト値の増加:")
        print("   python3 deploy_to_esp32.py --timeout 30")

    else:
        print("📋 エラー分類: 一般的な転送エラー")
        print("\n🔧 基本的な対処法:")
        print("1. デバイスの物理的な確認:")
        print("   - USBケーブルの接続")
        print("   - ESP32の電源LED点灯確認")
        print("2. 通信の確認:")
        print("   mpremote devs")
        print("   mpremote exec 'print(\"Hello\")'")
        print("3. デバイスリセット:")
        print("   python3 deploy_to_esp32.py --reset")

    print(f"\n📁 問題のファイル: {local_path}")
    print(f"📁 転送先: {remote_path}")
    print(f"⚠️  ファイルサイズ: {local_path.stat().st_size if local_path.exists() else 'ファイルなし'} バイト")

    print("\n💡 追加の診断コマンド:")
    print(f"   lsof {getattr(ARGS, 'port', '/dev/cu.usbmodem*')}")
    print("   ps aux | grep -i thonny")
    print("   mpremote exec 'import os; print(os.listdir())'")

    print("\n🔄 再実行コマンド:")
    print("   python3 deploy_to_esp32.py --force --debug")
    print("   python3 deploy_to_esp32.py --emergency  # 最小ファイルのみ")

    print("\n" + "="*60)

def check_port_available(port=None, dry_run=False):
    """ポート疎通とデバイス応答性を確認する"""
    try:
        print("[CHECK] デバイス疎通チェック...")
        mp(["exec", "print('OK')"], port=port, dry_run=dry_run, check=True)
        print("[OK] デバイスと通信できます。")
    except subprocess.CalledProcessError as e:
        handle_connection_error(e, port=port, dry_run=dry_run)

def get_local_hash(filepath: Path) -> str:
    """ローカルファイルのSHA256ハッシュを計算"""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def get_remote_hash(remote_path: str, port=None, dry_run=False, debug=False) -> str | None:
    """リモートファイルのSHA256ハッシュを計算"""
    # ":"プレフィックスを除去してパスを正規化
    clean_path = remote_path.lstrip(":")
    path_parts = clean_path.split("/") if clean_path else []

    if len(path_parts) <= 1:
        # ルートディレクトリのファイル
        parent_dir_str = ""
        base_name = path_parts[0] if path_parts else ""
    else:
        # サブディレクトリのファイル
        parent_dir_str = "/".join(path_parts[:-1])
        base_name = path_parts[-1]

    # 親ディレクトリのファイルリストで存在確認
    ls_path = ":/"+parent_dir_str if parent_dir_str else ":/"
    files_in_dir = remote_ls(ls_path, port=port, dry_run=dry_run)

    # デバッグモード時のログ出力
    if debug:
        print(f"[DEBUG] remote_path='{remote_path}' → clean_path='{clean_path}', parent_dir='{parent_dir_str}', base_name='{base_name}'")
        print(f"[DEBUG] ls_path='{ls_path}', files_in_dir={files_in_dir}")

    if base_name not in files_in_dir:
        if debug:
            print(f"[DEBUG] ファイル '{base_name}' が '{ls_path}' に見つかりません")
        return None

    # ハッシュ計算のためのパス構築
    file_path_for_hash = f"{parent_dir_str}/{base_name}" if parent_dir_str else base_name

    # MicroPython互換のハッシュ計算コード
    code = f"""
try:
    import hashlib, binascii

    # ファイル読み込み
    with open('{file_path_for_hash}', 'rb') as f:
        data = f.read()

    # ハッシュ計算（MicroPython確実版）
    h = hashlib.sha256(data)
    digest = h.digest()
    hex_hash = binascii.hexlify(digest)

    # バイト文字列を文字列に変換
    if hasattr(hex_hash, 'decode'):
        result = hex_hash.decode('ascii')
    else:
        result = str(hex_hash, 'ascii')

    print(result)

except Exception as e:
    print('HASH_ERROR:', e)
"""

    if debug:
        print(f"[DEBUG] ハッシュ計算対象: '{file_path_for_hash}'")
    res = mp_with_retry(["exec", code], port=port, dry_run=dry_run, check=False)

    remote_hash = (res.stdout or "").strip()

    if remote_hash.startswith('HASH_ERROR') or not remote_hash:
        print(f"[WARN] デバイス上のハッシュ計算に失敗: {remote_path} ({remote_hash})")
        return "error"
    return remote_hash

def remote_ls(path="/", port=None, dry_run=False):
    """リモートディレクトリの一覧を取得"""
    res = mp_with_retry(["fs", "ls", path], port=port, dry_run=dry_run, check=False)
    out = res.stdout.strip()
    if not out:
        return []
    files = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and parts[0].isdigit():
            files.append(parts[1].rstrip('/'))
    return files

def ensure_dir_remote(path, port=None, dry_run=False):
    """リモートディレクトリが存在しない場合は作成"""
    mp_with_retry(["fs", "mkdir", path], port=port, dry_run=dry_run, check=False)

def validate_local_files():
    """ローカルファイルの存在確認"""
    # セーフモード時は最小限のファイルのみチェック
    if getattr(ARGS, 'safe_mode', False):
        files = list(SAFE_MODE_FILES)
        print("[INFO] セーフモード：最小限ファイルのみ転送")
    else:
        files = list(REQUIRED_FILES)

    if getattr(ARGS, 'with_boot', False):
        files.append(Path("boot.py"))

    missing = [str(p) for p in files if not (ROOT / p).exists()]
    if missing:
        print("[ERROR] ローカルに不足ファイルがあります:", *missing, sep="\n - ")
        sys.exit(1)

    print(f"[OK] 全必須ファイル ({len(files)}個) の存在を確認しました")

def upload_required_files():
    """必須ファイルのアップロード (差分更新対応)"""
    if getattr(ARGS, 'verify', False):
        print("[STEP] 差分更新を開始します（--verify）…")
        is_sync_mode = True
    elif getattr(ARGS, 'force', False):
        print("[STEP] 全てのファイルを強制アップロードします（--force）…")
        is_sync_mode = False
    else:
        print("[STEP] 必要ファイルをアップロードします…")
        is_sync_mode = False

    # セーフモード時は最小限のファイルのみ転送
    if getattr(ARGS, 'safe_mode', False):
        targets = list(SAFE_MODE_FILES)
        print("[INFO] セーフモード実行中...")
    else:
        targets = list(REQUIRED_FILES)

    if getattr(ARGS, 'with_boot', False):
        targets.insert(0, Path("boot.py"))

    # 必要なディレクトリを作成
    ensure_dir_remote(":/static")

    uploaded_count = 0
    skipped_count = 0

    for rel_path in targets:
        local_path = ROOT / rel_path
        remote_path = ":" + rel_path.as_posix()

        if is_sync_mode:
            # ハッシュ比較による差分更新
            remote_hash = get_remote_hash(remote_path)
            if remote_hash == "error":
                print(f"[WARN] {remote_path} のハッシュ比較をスキップします。")
                continue
            local_hash = get_local_hash(local_path)
            if remote_hash == local_hash:
                print(f"[SKIP]   {remote_path} (変更なし)")
                skipped_count += 1
                continue
            elif remote_hash is None:
                print(f"[CREATE] {local_path} -> {remote_path}")
            else:
                print(f"[UPDATE] {local_path} -> {remote_path}")
        else:
            print(f"[PUT]    {local_path} -> {remote_path}")

        try:
            # ファイル転送はリトライなしで実行（失敗時は即座に終了）
            mp(["cp", str(local_path), remote_path], port=ARGS.port, dry_run=ARGS.dry_run, check=True)
            uploaded_count += 1
        except subprocess.CalledProcessError as e:
            print(f"\n❌ ファイル転送エラー: {local_path} -> {remote_path}")
            print(f"   エラー詳細: {e}")
            if e.stderr:
                print(f"   標準エラー: {e.stderr.strip()}")

            # 詳細な対処法を表示
            show_file_transfer_troubleshooting(local_path, remote_path, e)

            # 即座に終了（リトライしない）
            sys.exit(1)

    print(f"\n📊 アップロード結果: {uploaded_count}個アップロード, {skipped_count}個スキップ")


def main():
    """メイン関数"""
    global ARGS, REQUIRED_FILES, SAFE_MODE_FILES, ROOT

    config = state.config

    parser = argparse.ArgumentParser(
        description="🚀 ESP32-S3 MicroPython デプロイメントツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本的な差分更新
  %(prog)s --verify

  # 強制全ファイル更新
  %(prog)s --force

  # 緊急復旧（最小ファイルのみ）
  %(prog)s --emergency

  # デバッグモード
  %(prog)s --verify --debug

オプションカテゴリ:
  接続設定    : --port
  更新モード  : --verify, --force, --emergency
  制御オプション: --no-reset, --dry-run, --with-boot
  診断・調整  : --debug, --timeout
  廃止予定    : --keep-going (ファイル転送失敗時は常に停止)
        """
    )

    # === 接続設定 ===
    connection_group = parser.add_argument_group('接続設定')
    connection_group.add_argument(
        "--port", "-p",
        default=config.default_port,
        metavar="DEVICE",
        help=f"ESP32のシリアルポート (デフォルト: {config.default_port})"
    )

    # === 更新モード ===
    mode_group = parser.add_argument_group('更新モード（排他的）')
    mode_mutex = mode_group.add_mutually_exclusive_group()
    mode_mutex.add_argument(
        "--verify", "-v",
        action="store_true",
        help="【推奨】SHA256ハッシュによる差分更新（変更ファイルのみ転送）"
    )
    mode_mutex.add_argument(
        "--force", "-f",
        action="store_true",
        help="全ファイルを強制的に再転送（ハッシュ比較なし）"
    )
    mode_mutex.add_argument(
        "--emergency", "-e",
        action="store_true",
        help="緊急復旧モード（最小限の必須ファイルのみ転送）"
    )

    # === 制御オプション ===
    control_group = parser.add_argument_group('制御オプション')
    control_group.add_argument(
        "--no-reset",
        action="store_true",
        help="デプロイ開始時のハードウェアリセットをスキップ"
    )
    control_group.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="実際の転送は行わず、動作をシミュレーション"
    )
    control_group.add_argument(
        "--with-boot",
        action="store_true",
        help="boot.py も転送対象に含める"
    )

    # === 診断・調整 ===
    debug_group = parser.add_argument_group('診断・調整オプション')
    debug_group.add_argument(
        "--debug", "-d",
        action="store_true",
        help="詳細なデバッグログを出力"
    )
    debug_group.add_argument(
        "--timeout",
        type=int,
        default=config.default_timeout,
        metavar="SEC",
        help=f"通信タイムアウト秒数 (デフォルト: {config.default_timeout}秒)"
    )


    # === 廃止予定オプション ===
    deprecated_group = parser.add_argument_group('廃止予定オプション')
    deprecated_group.add_argument(
        "--keep-going", "-k",
        action="store_true",
        help="[廃止予定] ファイル転送エラー時は常に停止するため無効"
    )

    state.args = parser.parse_args()
    ARGS = state.args  # グローバル変数として設定（後方互換性のため）

    # 必要なグローバル変数を設定
    REQUIRED_FILES = config.required_files
    SAFE_MODE_FILES = config.safe_mode_files
    ROOT = state.root

    # オプションの後処理と検証
    if state.args.keep_going:
        print("[WARN] --keep-going オプションは廃止されました。ファイル転送エラー時は常に停止します。")

    # 緊急復旧モードの場合はセーフモードを有効化
    if state.args.emergency:
        state.args.safe_mode = True

    # デフォルトモードの設定（何も指定されていない場合は差分更新）
    if not (state.args.verify or state.args.force or state.args.emergency):
        state.args.verify = True
        print("[INFO] 更新モードが未指定のため、--verify（差分更新）を使用します。")

    # 実行モードの表示
    print("🚀 ESP32-S3 MicroPython デプロイメントツール")
    print(f"📱 対象デバイス: {ARGS.port}")

    # 更新モード
    if ARGS.emergency:
        print("🆘 更新モード: 緊急復旧（最小ファイルのみ）")
    elif ARGS.force:
        print("💪 更新モード: 強制更新（全ファイル）")
    elif ARGS.verify:
        print("🔍 更新モード: 差分更新（変更ファイルのみ）")

    # 制御オプション
    options = []
    if ARGS.dry_run:
        options.append("ドライラン")
    if ARGS.no_reset:
        options.append("リセットなし")
    if ARGS.with_boot:
        options.append("boot.py含む")
    if ARGS.debug:
        options.append("デバッグ")

    if options:
        print(f"⚙️  オプション: {', '.join(options)}")

    try:
        # デバイス接続確認
        if not ARGS.no_reset:
            reset_device(ARGS.port)

        check_device(ARGS.dry_run)

        # ファイルアップロード
        upload_required_files()

        # デプロイメント完了通知
        print("✅ デプロイメント完了！")

    except KeyboardInterrupt:
        print("\n⚠️  ユーザーによってデプロイメントが中断されました。")
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        handle_connection_error(e)

if __name__ == "__main__":
    main()