"""
main.py
Bluetooth Positioning System - エントリーポイント（v5対応）

役割：Bluetoothスキャン → 重複排除 → 管理用Vercel API への送信
※ 混雑レベルの計算はサーバー側（Vercel API Route）で実行されます。
   このプログラムは「センサー」としての役割に専念します。
"""

import asyncio
import schedule
import time
from datetime import datetime

from scanner.bluetooth_scanner import scan_devices
from processor.mac_deduplicator import deduplicate
from processor.congestion_calculator import preview_calculate  # ローカル確認専用
from uploader.api_uploader import upload
from config.settings import SCAN_INTERVAL_SECONDS, BOOTH_ID, OPERATOR_ID


def _now() -> str:
    return datetime.now().strftime("%y/%m/%d/%H:%M:%S")


async def _run_scan():
    """1回のスキャンサイクルを実行"""
    print(f"\n{'='*50}")
    print(f"[{_now()}] スキャン開始 - {BOOTH_ID}")
    print(f"{'='*50}")

    # 1. Bluetooth スキャン
    raw_macs = await scan_devices()

    # 2. MAC アドレス重複排除
    unique_macs = deduplicate(raw_macs)

    # 3.【ローカル確認専用】想定される混雑レベルを表示（本番では使わない参考値）
    preview_calculate(len(unique_macs))

    # 4. 管理用Vercel API へ送信（本番の混雑レベル計算はサーバー側で実行される）
    success = upload(unique_macs)

    if not success:
        print(f"[{_now()}] ⚠️  API送信失敗 - ローカルに保存しました")
        print(f"[{_now()}] ⚠️  管理者セクションから手動モードへの切り替えを検討してください")


def _job():
    asyncio.run(_run_scan())


def main():
    print(f"""
╔══════════════════════════════════════════╗
║  Bluetooth Positioning System (v5)        ║
║  ISF webapp - 混雑状況自動検知            ║
╠══════════════════════════════════════════╣
║  ブースID    : {BOOTH_ID:<26} ║
║  担当者ID    : {OPERATOR_ID:<26} ║
║  スキャン間隔 : {SCAN_INTERVAL_SECONDS}秒毎                     ║
╚══════════════════════════════════════════╝
""")

    _job()
    schedule.every(SCAN_INTERVAL_SECONDS).seconds.do(_job)

    print(f"[{_now()}] スケジュール開始（{SCAN_INTERVAL_SECONDS}秒ごと）")
    print(f"[{_now()}] 終了するには Ctrl+C を押してください")

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n[{_now()}] システム停止")
