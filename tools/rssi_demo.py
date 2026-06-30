"""
tools/rssi_demo.py
RSSI閾値決定用デモスクリプト

生MACアドレスとRSSI値を収集・表示・CSV保存する。
本番の main.py とは独立して動作する。

使い方:
  python tools/rssi_demo.py              # 1回スキャン
  python tools/rssi_demo.py --loop 60   # 60秒ごとに繰り返し
  python tools/rssi_demo.py --duration 15  # スキャン時間を15秒に変更（デフォルト: 10秒）
  python tools/rssi_demo.py --output rssi_data.csv  # 出力先CSVを指定

⚠ このスクリプトは生MACアドレスを含むデータをローカルに保存します。
  収集したCSVは実験後に必ず削除してください。
  本番の配布パッケージには含めないこと。
"""

import argparse
import asyncio
import csv
import time
from datetime import datetime
from pathlib import Path

from bleak import BleakScanner


async def scan(duration: int) -> list[dict]:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] スキャン開始（{duration}秒）...")

    devices = await BleakScanner.discover(timeout=duration, return_adv=True)

    results = []
    for device, adv_data in devices.values():
        results.append({
            "timestamp": datetime.now().isoformat(),
            "mac": device.address,
            "name": device.name or "",
            "rssi": adv_data.rssi,
        })

    results.sort(key=lambda r: r["rssi"], reverse=True)
    return results


def print_results(results: list[dict], thresholds: list[int] = (-50, -60, -70, -80)) -> None:
    print(f"\n検知台数: {len(results)} 台")
    print(f"{'MAC':20} {'RSSI':>6}  {'デバイス名'}")
    print("-" * 60)
    for r in results:
        print(f"{r['mac']:20} {r['rssi']:>6}  {r['name']}")

    print()
    print("── 閾値別カット結果 ──")
    for t in thresholds:
        passed = sum(1 for r in results if r["rssi"] >= t)
        print(f"  RSSI >= {t:4d}  →  {passed:3d} 台 / {len(results)} 台")
    print()


def save_csv(results: list[dict], path: Path) -> None:
    write_header = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "mac", "name", "rssi"])
        if write_header:
            writer.writeheader()
        writer.writerows(results)
    print(f"CSV保存: {path} （累計 {path.stat().st_size // 1024} KB）")


def main():
    parser = argparse.ArgumentParser(description="RSSI閾値決定用デモスクリプト")
    parser.add_argument("--duration", type=int, default=10, help="スキャン時間（秒）")
    parser.add_argument("--loop", type=int, default=0, help="繰り返し間隔（秒）。0なら1回だけ実行")
    parser.add_argument("--output", default="rssi_demo.csv", help="出力CSVパス")
    parser.add_argument(
        "--thresholds", nargs="+", type=int, default=[-50, -60, -70, -80],
        help="比較する閾値リスト（例: --thresholds -50 -65 -75）"
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    print(f"出力先: {output_path.resolve()}")
    print("⚠  生MACアドレスを含むデータを収集します。実験後はCSVを削除してください。\n")

    try:
        while True:
            results = asyncio.run(scan(args.duration))
            print_results(results, thresholds=args.thresholds)
            if results:
                save_csv(results, output_path)

            if args.loop <= 0:
                break

            print(f"{args.loop}秒後に再スキャン... （Ctrl+C で終了）\n")
            time.sleep(args.loop)

    except KeyboardInterrupt:
        print("\n終了しました。")


if __name__ == "__main__":
    main()
