"""
uploader/api_uploader.py
管理用Vercel の API Route（/api/booth/bluetooth）へ
スキャン結果を POST するモジュール（企画書v5 §10.3 準拠）
"""

import json
import requests
from datetime import datetime
from pathlib import Path

from config.settings import (
    BOOTH_ID,
    OPERATOR_ID,
    API_ENDPOINT,
    API_AUTH_TOKEN,
    API_TIMEOUT_SECONDS,
    LOG_DIR,
)


def upload(mac_addresses: list[str]) -> bool:
    """
    スキャン結果を Vercel API へ POST する

    Args:
        mac_addresses: 重複排除済みの MAC アドレスリスト

    Returns:
        bool: 送信成功なら True、失敗なら False
    """
    payload = {
        "boothId": BOOTH_ID,
        "deviceCount": len(mac_addresses),
        "macAddresses": mac_addresses,
        "operatorId": OPERATOR_ID,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_AUTH_TOKEN}",
    }

    now_display = datetime.now().strftime("%y/%m/%d/%H:%M:%S")

    try:
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        print(f"[{now_display}] API送信成功: {BOOTH_ID} ({len(mac_addresses)}台)")
        return True

    except requests.exceptions.RequestException as e:
        print(f"[{now_display}] API送信失敗: {e}")
        _save_local(payload, now_display)
        return False


def _save_local(payload: dict, now_display: str) -> None:
    """送信失敗時にローカルへ保存（フェイルオーバー用ログ）"""
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    log_path = Path(LOG_DIR) / f"scan_{datetime.now().strftime('%Y%m%d')}.json"

    logs = []
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            logs = json.load(f)

    logs.append({**payload, "savedAt": now_display})

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

    print(f"[{now_display}] ローカル保存: {log_path}")
