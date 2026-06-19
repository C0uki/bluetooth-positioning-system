"""
scanner/bluetooth_scanner.py
Bluetooth デバイスのスキャンを行うモジュール
"""

import asyncio
from bleak import BleakScanner
from datetime import datetime
from config.settings import SCAN_DURATION_SECONDS, RSSI_THRESHOLD


async def scan_devices() -> list[dict]:
    """
    Bluetooth デバイスをスキャンして検知結果を返す

    Returns:
        list[dict]: 各デバイスの {"mac": str, "rssi": int, "passed_filter": bool}
    """
    print(f"[{_now()}] Bluetooth スキャン開始（{SCAN_DURATION_SECONDS}秒）")

    devices = await BleakScanner.discover(timeout=SCAN_DURATION_SECONDS, return_adv=True)

    results = []
    for device, adv_data in devices.values():
        rssi = adv_data.rssi
        passed = RSSI_THRESHOLD is None or rssi >= RSSI_THRESHOLD
        results.append({
            "mac": device.address,
            "rssi": rssi,
            "passed_filter": passed,
        })

    total = len(results)
    passed = sum(1 for r in results if r["passed_filter"])

    if RSSI_THRESHOLD is not None:
        print(f"[{_now()}] スキャン完了: {total}台検知, RSSIフィルタ通過: {passed}台 (閾値: {RSSI_THRESHOLD})")
    else:
        print(f"[{_now()}] スキャン完了: {total}台検知（RSSIフィルタ無効）")

    return results


def get_filtered_macs(scan_results: list[dict]) -> list[str]:
    """フィルタ通過したデバイスのMACアドレスリストを返す"""
    return [r["mac"] for r in scan_results if r["passed_filter"]]


def _now() -> str:
    return datetime.now().strftime("%y/%m/%d/%H:%M:%S")
