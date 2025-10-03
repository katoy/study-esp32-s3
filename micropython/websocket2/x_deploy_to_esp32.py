#!/usr/bin/env python3
"""
ESP32 再配置スクリプト（mpremote 使用）

機能:
- 必要ファイルのみを ESP32 にアップロード
- --verify: 差分更新モード。ハッシュ値を比較し、変更があるファイルのみ転送
- --force: 強制更新モード。ハッシュ比較を無視して全ファイルを転送
- --strict: ルート直下の不要ファイルを削除（許可リストベース）

要件:
- ホストPCに mpremote がインストール済みであること

使い方（例）:
  python3 deploy_to_esp32.py                 # 全ファイルをアップロード
  python3 deploy_to_esp32.py --verify        # 変更があったファイルのみアップロード
  python3 deploy_to_esp32.py --force         # 全てのファイルを強制的にアップロード
  python3 deploy_to_esp32.py --port /dev/tty.usbmodem1101
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# --- グローバル定数 ---
ROOT = Path(__file__).resolve().parent

REQUIRED_FILES = [
    Path("main.py"),
    Path("sensor_manager.py"),
    Path("thingspeak.py"),
    Path("web_routes.py"),
    Path("websocket_server.py"),
    Path("lib/microdot.py"),
    Path("index.html"),
    Path("manifest.json"),
    Path("wifi_config.py"),
    Path("static/app.js"),
    Path("static/style.css"),
]

# セーフモード：WebSocket関連ファイルを除外
SAFE_MODE_FILES = [
    Path("main.py"),
    Path("sensor_manager.py"),
    Path("lib/microdot.py"),
    Path("wifi_config.py"),
]

ROOT_ALLOWLIST = {
    "main.py",
    "sensor_manager.py",
    "thingspeak.py",
    "web_routes.py",
    "websocket_server.py",
    "index.html",
    "manifest.json",
    "wifi_config.py",
    "static",
    "lib",
    "webrepl.py",
    "webrepl_cfg.py",
    "boot.py",
}

ARGS = None

# ===== 1. 基本ユーティリティ関数 =====

def which(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def run_cmd(args, dry_run=False, check=True):
    # print("$", " ".join(map(str, args))) # デバッグ時以外は抑制
    if dry_run:
        print("(dry-run) $", " ".join(map(str, args)))
        return subprocess.CompletedProcess(args, 0, "", "")
    try:
        return subprocess.run(args, check=check, text=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        stdout = (e.stdout or "").strip()
        stderr = (e.stderr or "").strip()
        if stdout:
            print(f"[mpremote stdout]\n{stdout}")
        if stderr:
            print(f"[mpremote stderr]\n{stderr}")
        raise

# ===== 2. mpremote ラッパー関数 =====

def mp(args_mp, port=None, dry_run=False, check=True):
    """mpremote 実行ラッパー。必要に応じて connect <port> を前置する。

    例:
      mp(["fs", "ls", ":/"], port="/dev/tty.usbmodem1101")
      → mpremote connect /dev/tty.usbmodem1101 fs ls :/
    """
    base = ["mpremote"]
    # デバイス列挙は connect 不要。それ以外は port 指定時に connect を付与
    if port and args_mp and args_mp[0] not in ("devs",):
        base += ["connect", port]
    return run_cmd(base + args_mp, dry_run=dry_run, check=check)

def show_esp32_status(port=None):
    """ESP32の状態情報を表示する"""
    try:
        print("[INFO] ESP32ステータスチェック中...")

        # メモリ情報
        mp(["exec", "import gc; print(f'Free memory: {gc.mem_free()} bytes')"], port=port, check=False)

        # 実行中のスレッド情報
        mp(["exec", """
import _thread
try:
    print('Active threads:', _thread.get_ident())
except:
    print('Thread info not available')
"""], port=port, check=False)

        return True
    except Exception as e:
        print(f"[WARNING] ステータスチェックに失敗: {e}")
        return False

def interrupt_esp32_program(port=None):
    """ESP32の実行中プログラムにCtrl+C割り込みを送信"""
    if not SERIAL_AVAILABLE:
        return False

    if not port:
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

def soft_reset_esp32(port=None):
    """ESP32にソフトリセットを送信してREPLをクリアする"""
    try:
        print("[INFO] ESP32のソフトリセットを実行中...")
        # ハードウェアリセットを先に試行
        if hardware_reset_esp32(port):
            print("[INFO] ハードウェアリセット成功、REPLの確認中...")
            time.sleep(2)
            # REPLが利用可能かテスト
            try:
                mp(["exec", "print('Reset OK')"], port=port, check=True)
                return True
            except Exception:
                pass  # REPLがまだ準備できていない場合は通常のソフトリセットを続行

        # 通常のソフトリセット（Ctrl+D）を送信
        mp(["exec", "import machine; machine.soft_reset()"], port=port, check=False)
        time.sleep(3)  # リセット完了を待機
        return True
    except Exception as e:
        print(f"[WARNING] ソフトリセットに失敗しました: {e}")
        return False

def mp_with_retry(args_mp, port=None, dry_run=False, check=True):
    tries = max(1, int(getattr(ARGS, "retries", 1)))
    wait = float(getattr(ARGS, "retry_wait", 2.0))

    for attempt in range(1, tries + 1):
        try:
            return mp(args_mp, port=port, dry_run=dry_run, check=check)
        except subprocess.CalledProcessError as e:
            if attempt < tries:
                cmd_str = " ".join(args_mp)
                print(f"[RETRY] mpremote {cmd_str} (attempt {attempt}/{tries}) → {wait}s 後に再試行…")

                # "could not enter raw repl" エラーの場合はより強力なリセットを試行
                if "could not enter raw repl" in str(e):
                    print("[INFO] Raw REPLエラーを検出、強制的な割り込みとリセットを試行...")
                    # Ctrl+C割り込み + ハードウェアリセット
                    interrupt_esp32_program(port)
                    time.sleep(1)
                    hardware_reset_esp32(port)
                    time.sleep(2)

                time.sleep(wait)
            else:
                raise

def remote_exec(code: str):
    return mp_with_retry(["exec", code], port=ARGS.port, dry_run=ARGS.dry_run, check=False)

def remote_cp(src: Path, dst: str):
    mp_with_retry(["cp", str(src), dst], port=ARGS.port, dry_run=ARGS.dry_run)

def remote_rm(path: str):
    mp_with_retry(["fs", "rm", path], port=ARGS.port, dry_run=ARGS.dry_run, check=False)

def ensure_dir_remote(path):
    mp_with_retry(["fs", "mkdir", path], port=ARGS.port, dry_run=ARGS.dry_run, check=False)

# ===== 3. ファイルシステム & ハッシュ関連関数 =====

def remote_ls(path="/"):
    res = mp_with_retry(["fs", "ls", path], port=ARGS.port, dry_run=ARGS.dry_run, check=False)
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

def get_local_hash(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def get_remote_hash(remote_path: str) -> str | None:
    parent_dir_str = "/".join(remote_path.split('/')[1:-1])
    base_name = remote_path.split('/')[-1]

    # 親ディレクトリのファイルリストで存在確認
    if base_name not in remote_ls(":/"+parent_dir_str):
        return None

    code = f"""
import hashlib
try:
    h = hashlib.sha256()
    with open('{base_name}', 'rb') as f:
        buf = bytearray(256)
        while True:
            size = f.readinto(buf)
            if size == 0: break
            h.update(memoryview(buf)[:size])
    print(h.hexdigest())
except Exception as e:
    print(f'HASH_ERROR: {{e}}')
"""
    # execはカレントディレクトリがルートなので、パスを調整
    if parent_dir_str:
        res = remote_exec(f"import os; os.chdir('{parent_dir_str}');\n{code}")
    else:
        res = remote_exec(code)
    remote_hash = (res.stdout or "").strip()

    if remote_hash.startswith('HASH_ERROR') or not remote_hash:
        print(f"[WARN] デバイス上のハッシュ計算に失敗: {remote_path} ({remote_hash})")
        return "error"
    return remote_hash

# ===== 4. メインの処理フロー関数 =====

def list_devices():
    try:
        res = run_cmd(["mpremote", "devs"], dry_run=ARGS.dry_run, check=False)
        if res.stdout:
            print("[INFO] 検出デバイス:\n" + res.stdout.strip())
        else:
            print("[INFO] 検出デバイスはありませんでした")
    except Exception as _:
        pass

def handle_connection_error(e: subprocess.CalledProcessError):
    """mpremote接続エラーを処理し、原因を特定してユーザーに案内する"""
    # 1. ホスト側のポートロックをlsofで確認
    try:
        if ARGS.port and sys.platform != "win32":
            lsof_res = run_cmd(["lsof", ARGS.port], check=False, dry_run=ARGS.dry_run)
            if lsof_res.stdout and lsof_res.stdout.strip():
                print(f"\n[ERROR] ポート '{ARGS.port}' は、以下のプロセスによって使用中のようです。")
                print("--- lsof output ---")
                print(lsof_res.stdout.strip())
                print("-----------------")
                print("このプロセスを終了してから、再度スクリプトを実行してください。\n")
                sys.exit(1)
    except Exception:
        pass

    # 2. Thonnyのプロセスが起動しているか確認
    try:
        ps_res = run_cmd(["ps", "aux"], dry_run=ARGS.dry_run, check=False)
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
            mp(["soft-reset"], check=True, dry_run=ARGS.dry_run)
            if not ARGS.dry_run:
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

def check_port_available():
    """ポート疎通とデバイス応答性を確認する"""
    try:
        print("[CHECK] デバイス疎通チェック…")
        mp(["exec", "print('OK')"], port=ARGS.port, dry_run=ARGS.dry_run, check=True)
        print("[OK] デバイスと通信できます。")
    except subprocess.CalledProcessError as e:
        handle_connection_error(e)

def validate_local_files():
    # セーフモード時は最小限のファイルのみチェック
    if getattr(ARGS, 'safe_mode', False):
        files = list(SAFE_MODE_FILES)
        print("[INFO] セーフモード：WebSocket関連ファイルを除外して最小限転送")
    else:
        files = list(REQUIRED_FILES)

    if ARGS.with_boot:
        files.append(Path("boot.py"))
    missing = [str(p) for p in files if not (ROOT / p).exists()]
    if missing:
        print("[ERROR] ローカルに不足ファイルがあります:", *missing, sep="\n - ")
        sys.exit(1)

def upload_required_files():
    is_sync_mode = ARGS.verify and not ARGS.force
    if is_sync_mode:
        print("[STEP] 差分更新を開始します（--verify）…")
    elif ARGS.force:
        print("[STEP] 全てのファイルを強制アップロードします（--force）…")
    else:
        print("[STEP] 必要ファイルをアップロードします…")

    # セーフモード時は最小限のファイルのみ転送
    if getattr(ARGS, 'safe_mode', False):
        targets = list(SAFE_MODE_FILES)
        print("[INFO] セーフモード実行中...")
    else:
        targets = list(REQUIRED_FILES)

    if ARGS.with_boot:
        targets.insert(0, Path("boot.py"))

    ensure_dir_remote(":/static")
    ensure_dir_remote(":/lib")

    for rel_path in targets:
        local_path = ROOT / rel_path
        remote_path = ":" + rel_path.as_posix()

        if is_sync_mode:
            remote_hash = get_remote_hash(remote_path)
            if remote_hash == "error":
                print(f"[WARN] {remote_path} のハッシュ比較をスキップします。")
                continue
            local_hash = get_local_hash(local_path)
            if remote_hash == local_hash:
                print(f"[SKIP]   {remote_path} (変更なし)")
                continue
            elif remote_hash is None:
                print(f"[CREATE] {local_path} -> {remote_path}")
            else:
                print(f"[UPDATE] {local_path} -> {remote_path}")
        else:
            print(f"[PUT]    {local_path} -> {remote_path}")

        try:
            remote_cp(local_path, remote_path)
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").lower()
            if "could not enter raw repl" in stderr or "failed to access" in stderr:
                print("\n[ERROR] ファイル転送中にデバイスとの通信が途絶えました。")
                handle_connection_error(e)
            elif not ARGS.keep_going:
                raise

def cleanup_static_extras():
    print("[STEP] /static の不要ファイルを削除…")
    keep = {p.name for p in REQUIRED_FILES if p.parent.name == 'static'}
    items = remote_ls(":/static")
    for name in items:
        if name not in keep:
            print(f"[DEL] /static/{name}")
            remote_rm(f":/static/{name}")

def cleanup_root_extras_strict():
    print("[STEP] ルート直下の不要ファイルを削除（--strict）…")
    items = remote_ls(":/")
    for name in items:
        if name not in ROOT_ALLOWLIST:
            print(f"[DEL] /{name}")
            remote_rm(f":/{name}")

def confirm(prompt: str) -> bool:
    if ARGS.yes:
        return True
    ans = input(f"{prompt} [y/N]: ").strip().lower()
    return ans in ("y", "yes")

# ===== 5. メイン実行部 =====

def emergency_recovery():
    """緊急復旧: フラッシュ消去とMicroPython再インストール"""
    print("[WARNING] 緊急復旧モードが選択されました。")
    print("この操作により、ESP32のフラッシュメモリが完全に消去され、")
    print("MicroPythonファームウェアが再インストールされます。")
    print("すべてのファイルとプログラムが削除されます。")

    if not confirm("本当に実行しますか？"):
        print("[CANCELLED] 緊急復旧をキャンセルしました。")
        return False

    print("\n=== 緊急復旧手順 ===")
    print("1. ESP32ボードの【BOOT】ボタンを押したまま保持してください")
    print("2. そのままの状態で【RST】ボタンを1回押して離してください")
    print("3. その後【BOOT】ボタンを離してください")
    print("4. デバイスがダウンロードモードになります")

    if not confirm("上記の手順を実行しました。続行しますか？"):
        print("[CANCELLED] 緊急復旧をキャンセルしました。")
        return False

    print("\n[INFO] esptoolでフラッシュ消去を実行中...")
    try:
        run_cmd([
            "python", "-m", "esptool",
            "--chip", "esp32s3",
            "--port", ARGS.port,
            "erase_flash"
        ], dry_run=ARGS.dry_run)

        print("\n[INFO] MicroPythonファームウェアを再インストール中...")
        print("注意: この処理には数分かかる場合があります...")

        # ESP32-S3用のMicroPythonバイナリダウンロードと書き込み指示
        print("\n[INFO] ファームウェアダウンロードが必要です。")
        print("1. https://micropython.org/download/ESP32_GENERIC_S3/ にアクセス")
        print("2. 最新の .bin ファイルをダウンロード")
        print("3. 以下のコマンドを実行:")
        print(f"   python -m esptool --chip esp32s3 --port {ARGS.port} write_flash -z 0 <ダウンロードした.binファイル>")
        print("\n[INFO] ファームウェア再インストール後、再度このスクリプトを実行してください。")

        return True

    except Exception as e:
        print(f"[ERROR] 緊急復旧に失敗しました: {e}")
        print("\n手動での緊急復旧手順:")
        print("1. esptoolをインストール: pip install esptool")
        print("2. フラッシュ消去: python -m esptool --chip esp32s3 --port <PORT> erase_flash")
        print("3. MicroPython再インストール: 公式サイトからファームウェアをダウンロードして書き込み")
        return False

def main():
    if not which("mpremote"):
        print("[ERROR] mpremote が見つかりません。`pip install mpremote` でインストールしてください。")
        sys.exit(1)

    # 緊急復旧モード
    if getattr(ARGS, 'erase_flash', False):
        emergency_recovery()
        return

    # デプロイ前にソフトリセットを実行（接続問題を予防）
    if getattr(ARGS, 'reset', False) or confirm("デプロイ前にESP32をソフトリセットしますか？ (推奨)"):
        soft_reset_esp32(ARGS.port)

    check_port_available()
    validate_local_files()
    upload_required_files()
    cleanup_static_extras()

    if ARGS.strict:
        if confirm("ルート直下の不要ファイルを削除します。続行しますか？"):
            cleanup_root_extras_strict()

    print("\n[DONE] 再配置が完了しました。ESP32 を再起動して動作を確認してください。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ESP32 再配置 (mpremote)",
        formatter_class=argparse.RawTextHelpFormatter
    )
    group = parser.add_argument_group('Основные параметры')
    group.add_argument("-p", "--port", help="シリアルポート（例: /dev/tty.usbmodem1101）", default=None)
    group.add_argument("-y", "--yes", action="store_true", help="確認プロンプトを省略")

    mode_group = parser.add_argument_group('更新モード')
    mode_group.add_argument("-v", "--verify", action="store_true", help="差分更新モード。ハッシュを比較し変更があるファイルのみ転送")
    mode_group.add_argument("-f", "--force", action="store_true", help="強制更新モード。--verifyを無視して全ファイル転送")

    option_group = parser.add_argument_group('追加オプション')
    option_group.add_argument("--strict", action="store_true", help="ルート直下もクリーンアップ")
    option_group.add_argument("--with-boot", action="store_true", help="boot.py も対象に含める")
    option_group.add_argument("--reset", action="store_true", help="デプロイ前にESP32をソフトリセット")
    option_group.add_argument("--safe-mode", action="store_true", help="セーフモード：WebSocket関連ファイルを除外して最小限のファイルのみ転送")
    option_group.add_argument("--erase-flash", action="store_true", help="フラッシュを消去してMicroPythonを再インストール（緊急復旧用）")
    option_group.add_argument("--dry-run", action="store_true", help="実行せず計画だけ表示")

    retry_group = parser.add_argument_group('リトライ設定')
    retry_group.add_argument("-k", "--keep-going", action="store_true", help="ファイル転送失敗でも続行")
    retry_group.add_argument("--retries", type=int, default=3, help="mpremoteリトライ回数")
    retry_group.add_argument("--retry-wait", type=float, default=2.0, help="リトライ間隔秒")

    ARGS = parser.parse_args()
    main()
