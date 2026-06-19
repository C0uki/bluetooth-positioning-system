"""
scanner/bluetooth_scanner.py
Bluetooth デバイスのスキャンを行うモジュール
"""

import asyncio
from bleak import BleakScanner
from datetime import datetime
from config.settings import SCAN_DURATION_SECONDS


async def scan_devices() -> list[str]:
    """
    Bluetooth デバイスをスキャンして MAC アドレスのリストを返す

    Returns:
        list[str]: 検知した MAC アドレスのリスト
    """
    print(f"[{_now()}] Bluetooth スキャン開始（{SCAN_DURATION_SECONDS}秒）")

    devices = await BleakScanner.discover(timeout=SCAN_DURATION_SECONDS)
    mac_addresses = [device.address for device in devices]

    print(f"[{_now()}] スキャン完了: {len(mac_addresses)} 台検知")
    return mac_addresses


def _now() -> str:
    return datetime.now().strftime("%y/%m/%d/%H:%M:%S")
