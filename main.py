"""
main.py
Bluetooth Positioning System - エントリーポイント（v5対応）

役割：Bluetoothスキャン → RSSIログ記録 → 重複排除 → 管理用Vercel API への送信
※ 混雑レベルの計算はサーバー側（Vercel API Route）で実行されます。
"""

import asyncio
import shutil
import time
from datetime import datetime
from pathlib import Path

from scanner.bluetooth_scanner import scan_devices, get_filtered_macs
from processor.mac_deduplicator import deduplicate
from logger.rssi_logger import log_rssi
from uploader.api_uploader import upload
from config.settings import SCAN_INTERVAL_SECONDS, BOOTH_ID, OPERATOR_ID, END_TIME, LOG_DIR


def _now() -> str:
    return datetime.now().strftime("%y/%m/%d/%H:%M:%S")


def _past_end_time() -> bool:
    now = datetime.now().strftime("%H:%M")
    return now >= END_TIME


_last_status = "起動中..."
_last_send_time = "未送信"


async def _run_scan():
    global _last_status, _last_send_time

    try:
        raw_results = await scan_devices()
        log_rssi(raw_results)
        filtered_macs = get_filtered_macs(raw_results)
        unique_macs = deduplicate(filtered_macs)
        success = upload(unique_macs)

        _last_send_time = datetime.now().strftime("%H:%M:%S")
        if success:
            _last_status = "✅ 正常に動作中です"
        else:
            _last_status = "⚠️ 直前の送信に失敗しました（次回リトライします）"

    except Exception as e:
        _last_status = f"⚠️ エラー発生（次回リトライします）"
        print(f"[{_now()}] エラー: {e}")


def _show_status():
    print(f"\033[2J\033[H", end="")
    print(f"══════════════════════════════════════════")
    print(f"  Bluetooth Positioning System (v5)")
    print(f"  ブース: {BOOTH_ID}")
    print(f"══════════════════════════════════════════")
    print()

    if _past_end_time():
        print(f"  終了時刻（{END_TIME}）になりました。")
        print(f"  このウィンドウを閉じてください。")
    else:
        print(f"  状態: {_last_status}")
        print(f"  最終送信: {_last_send_time}")
        print(f"  送信間隔: {SCAN_INTERVAL_SECONDS}秒")
        print()
        print(f"  ⚠ このウィンドウは閉じないでください")

    print(f"══════════════════════════════════════════")


def _copy_logs_to_usb():
    """終了後、ログをUSBドライブにコピーしてローカルから削除する"""
    log_path = Path(LOG_DIR)
    if not log_path.exists() or not any(log_path.iterdir()):
        print("ログファイルがありません。")
        return

    usb_candidates = [Path(f"{d}:/") for d in "DEFGHIJ"]
    usb_drive = None
    for candidate in usb_candidates:
        if candidate.exists() and candidate.is_dir():
            usb_drive = candidate
            break

    if usb_drive is None:
        print()
        print("USBメモリを挿入してください。")
        print("挿入後、Enterキーを押してください（スキップするにはCtrl+Cを押してください）")
        try:
            input()
            return _copy_logs_to_usb()
        except KeyboardInterrupt:
            print("\nログのコピーをスキップしました。")
            return

    dest = usb_drive / f"bps_logs_{BOOTH_ID}"
    shutil.copytree(log_path, dest, dirs_exist_ok=True)
    print(f"ログを {dest} にコピーしました。")

    shutil.rmtree(log_path)
    print("ローカルのログを削除しました。")


def main():
    _show_status()
    asyncio.run(_run_scan())
    _show_status()

    while not _past_end_time():
        time.sleep(SCAN_INTERVAL_SECONDS)
        asyncio.run(_run_scan())
        _show_status()

    _copy_logs_to_usb()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n[{_now()}] システム停止")
