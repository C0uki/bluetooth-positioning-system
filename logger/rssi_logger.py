"""
logger/rssi_logger.py
RSSIデータをCSV形式でローカルに記録するモジュール
（将来の位置推定システム用の学習データ収集）
"""

import csv
from datetime import datetime
from pathlib import Path

from config.settings import BOOTH_ID, LOG_DIR


def log_rssi(scan_results: list[dict]) -> None:
    """
    スキャン結果をCSVに追記する

    Args:
        scan_results: bluetooth_scanner.scan_devices() の戻り値
    """
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    log_path = log_dir / f"rssi_log_{BOOTH_ID}_{today}.csv"

    write_header = not log_path.exists()
    timestamp = datetime.now().isoformat()

    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["timestamp", "booth_id", "mac_address", "rssi", "passed_filter"])
        for r in scan_results:
            writer.writerow([timestamp, BOOTH_ID, r["mac"], r["rssi"], r["passed_filter"]])
