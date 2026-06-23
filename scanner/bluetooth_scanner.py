"""
scanner/bluetooth_scanner.py
Bluetooth デバイスのスキャンを行うモジュール
"""

import asyncio
import hashlib
from bleak import BleakScanner
from datetime import datetime
from config.settings import SCAN_DURATION_SECONDS, RSSI_THRESHOLD, MAC_HASH_SALT


def hash_mac(mac: str) -> str:
    """
    生 MAC アドレス（来場者端末の識別子）を保存・送信しないため、
    ソルト付き SHA-256 で擬似 ID に変換する。

    同一端末は常に同じ擬似 ID になるので、重複排除や将来の位置推定
    （擬似 ID + RSSI パターン）は維持したまま匿名化できる。
    """
    return hashlib.sha256(f"{MAC_HASH_SALT}:{mac}".encode("utf-8")).hexdigest()[:16]


async def scan_devices() -> list[dict]:
    """
    Bluetooth デバイスをスキャンして検知結果を返す

    Returns:
        list[dict]: 各デバイスの {"mac_hash": str, "rssi": int, "passed_filter": bool}
                    mac_hash はソルト付きハッシュ化済みの擬似 ID（生 MAC は保持しない）
    """
    print(f"[{_now()}] Bluetooth スキャン開始（{SCAN_DURATION_SECONDS}秒）")

    devices = await BleakScanner.discover(timeout=SCAN_DURATION_SECONDS, return_adv=True)

    results = []
    for device, adv_data in devices.values():
        rssi = adv_data.rssi
        passed = RSSI_THRESHOLD is None or rssi >= RSSI_THRESHOLD
        results.append({
            "mac_hash": hash_mac(device.address),
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
    """フィルタ通過したデバイスの擬似ID（ハッシュ化MAC）リストを返す"""
    return [r["mac_hash"] for r in scan_results if r["passed_filter"]]


def _now() -> str:
    return datetime.now().strftime("%y/%m/%d/%H:%M:%S")
