"""
main.py
BPSプロジェクト - エントリーポイント（v5対応）

役割：Bluetoothスキャン → RSSIログ記録 → 重複排除 → 管理用Vercel API への送信
※ 混雑レベルの計算はサーバー側（Vercel API Route）で実行されます。
"""

import asyncio
import ctypes
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

from scanner.bluetooth_scanner import scan_devices, get_filtered_macs, get_filtered_results
from processor.mac_deduplicator import deduplicate
from logger.rssi_logger import log_rssi
from uploader.api_uploader import upload
import config.settings as settings
from config.settings import BOOTH_ID, OPERATOR_ID, END_TIME, LOG_DIR


def _now() -> str:
    return datetime.now().strftime("%y/%m/%d/%H:%M:%S")


def _past_end_time() -> bool:
    now = datetime.now().strftime("%H:%M")
    return now >= END_TIME


def _validate_settings():
    # ソルトなしハッシュはMAC空間の全数計算で逆引き可能なため、
    # 未設定のまま静かに稼働させない（開発時のみ明示的なオプトインで許可）。
    if not settings.MAC_HASH_SALT and not getattr(settings, "ALLOW_EMPTY_SALT_FOR_DEV", False):
        print("エラー: MAC_HASH_SALT が未設定です。")
        print("generate_configs.py で生成した配布パッケージを使用してください。")
        print("（開発時に空のまま動かす場合は config/settings.py の ALLOW_EMPTY_SALT_FOR_DEV = True を設定）")
        raise SystemExit(1)

    # _past_end_time は文字列比較のため、ゼロ埋めなし（例: "9:00"）だと
    # 終了判定が正しく機能しない。起動時に形式を検証する。
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", END_TIME):
        raise SystemExit(f"エラー: END_TIME の形式が不正です: {END_TIME}（例: 16:00）")


_last_status = "起動中..."
_last_send_time = "未送信"


async def _run_scan():
    global _last_status, _last_send_time

    try:
        raw_results = await scan_devices()
        log_rssi(raw_results)
        filtered_macs = get_filtered_macs(raw_results)
        unique_macs = deduplicate(filtered_macs)
        filtered_results = get_filtered_results(raw_results)
        unique_devices = {r["mac_hash"]: r["rssi"] for r in filtered_results}
        devices_payload = [{"pseudoId": k, "rssi": v} for k, v in unique_devices.items()]
        success = upload(unique_macs, devices=devices_payload)

        _last_send_time = datetime.now().strftime("%H:%M:%S")
        if success:
            _last_status = "✅ 正常に動作中です"
        else:
            _last_status = "⚠️ 直前の送信に失敗しました（次回リトライします）"

    except Exception as e:
        _last_status = "⚠️ エラー発生（次回リトライします）"
        print(f"[{_now()}] エラー: {e}")


def _show_status():
    print("\033[2J\033[H", end="")
    print("══════════════════════════════════════════")
    print(f"  BPSプロジェクト (v5)")
    print(f"  ブース: {BOOTH_ID}")
    print("══════════════════════════════════════════")
    print()

    if _past_end_time():
        print(f"  終了時刻（{END_TIME}）になりました。")
        print("  このウィンドウを閉じてください。")
    else:
        print(f"  状態: {_last_status}")
        print(f"  最終送信: {_last_send_time}")
        print(f"  送信間隔: {settings.SCAN_INTERVAL_SECONDS}秒")
        print()
        print("  ⚠ このウィンドウは閉じないでください")

    print("══════════════════════════════════════════")


_DRIVE_REMOVABLE = 2  # win32 GetDriveType の DRIVE_REMOVABLE


def _find_usb_drive() -> Path | None:
    # 存在するドライブを無条件にUSBとみなすと、ネットワークドライブや
    # 復旧パーティションへ書き込んだ上でローカルを削除してしまうため、
    # リムーバブルドライブに限定する。
    try:
        get_drive_type = ctypes.windll.kernel32.GetDriveTypeW
    except AttributeError:
        return None  # Windows以外（Surface本番では到達しない）
    for d in "DEFGHIJ":
        if get_drive_type(ctypes.c_wchar_p(f"{d}:\\")) == _DRIVE_REMOVABLE:
            return Path(f"{d}:/")
    return None


def _copy_logs_to_usb():
    log_path = Path(LOG_DIR)
    if not log_path.exists() or not any(log_path.iterdir()):
        print("ログファイルがありません。")
        return

    while True:
        usb_drive = _find_usb_drive()
        if usb_drive is not None:
            break
        print()
        print("USBメモリを挿入してください。")
        print("挿入後、Enterキーを押してください（スキップするにはCtrl+Cを押してください）")
        try:
            input()
        except KeyboardInterrupt:
            print("\nログのコピーをスキップしました。")
            return

    dest = usb_drive / f"bps_logs_{BOOTH_ID}"
    try:
        shutil.copytree(log_path, dest, dirs_exist_ok=True)
    except Exception as e:
        print(f"コピーに失敗しました: {e}")
        print("ローカルのログは削除せずに残します。")
        return

    # コピー結果を検証できるまでローカルは削除しない
    src_files = [p for p in log_path.rglob("*") if p.is_file()]
    mismatched = [
        p for p in src_files
        if not (dest / p.relative_to(log_path)).is_file()
        or (dest / p.relative_to(log_path)).stat().st_size != p.stat().st_size
    ]
    if mismatched:
        print(f"コピーの検証に失敗しました（{len(mismatched)}件不一致）。ローカルのログは削除せずに残します。")
        return

    print(f"ログを {dest} にコピーしました。")
    shutil.rmtree(log_path)
    print("ローカルのログを削除しました。")


def _input_token():
    if settings.BLUETOOTH_SECRET:
        return
    import subprocess
    result = subprocess.run(
        ["powershell", "-Command",
         'Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::InputBox("APIトークンを入力してください", "BPSプロジェクト")'],
        capture_output=True, text=True
    )
    token = result.stdout.strip() if result.returncode == 0 else ""
    if not token:
        print("トークンが入力されませんでした。終了します。")
        raise SystemExit(1)
    settings.BLUETOOTH_SECRET = token
    print("トークンを設定しました。\n")


def main():
    _validate_settings()
    _input_token()
    _show_status()
    asyncio.run(_run_scan())
    _show_status()

    while not _past_end_time():
        time.sleep(settings.SCAN_INTERVAL_SECONDS)
        asyncio.run(_run_scan())
        _show_status()

    _copy_logs_to_usb()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n[{_now()}] システム停止")
