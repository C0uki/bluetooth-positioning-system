"""
uploader/api_uploader.py
データ配信 Worker の受信 API（/v1/ingest）へ
スキャン結果を POST するモジュール（企画書v5 §10.3 準拠）
"""

import json
import requests
from datetime import datetime
from pathlib import Path

import config.settings as settings
from config.settings import (
    BOOTH_ID,
    OPERATOR_ID,
    API_ENDPOINT,
    API_TIMEOUT_SECONDS,
    LOG_DIR,
)


# 受信側（データ配信 Worker）はボディが 16KB を超えると 413 を返す。
# 余裕を見てこの値を上限にし、超える分の devices は送らない。
MAX_PAYLOAD_BYTES = 15 * 1024


def _dumps(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def build_payload(mac_addresses: list[str], devices: list[tuple[str, int]] | None = None) -> dict:
    """
    送信ペイロードを組み立てる。

    devices は [擬似ID, RSSI] の短い配列で送る（1台あたり約25バイト、約600台まで）。
    以前は {"pseudoId": ..., "rssi": ...} と macAddresses を両方載せていたため、
    約240台で 16KB を超えて 413 になり、混雑時ほど送信が止まっていた。
    それでも上限を超える場合は RSSI の強い（近い）順に入るだけ送り、
    devicesTruncated を true にする。deviceCount は常に全台数。
    """
    payload = {
        "boothId": BOOTH_ID,
        "deviceCount": len(mac_addresses),
        "operatorId": OPERATOR_ID,
    }
    if devices is None:
        return payload

    rows = sorted(([pid, rssi] for pid, rssi in devices), key=lambda r: r[1], reverse=True)
    payload["devices"] = rows
    if len(_dumps(payload)) <= MAX_PAYLOAD_BYTES:
        return payload

    # 入る件数を二分探索で求める
    lo, hi = 0, len(rows)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        payload["devices"] = rows[:mid]
        payload["devicesTruncated"] = True
        if len(_dumps(payload)) <= MAX_PAYLOAD_BYTES:
            lo = mid
        else:
            hi = mid - 1
    payload["devices"] = rows[:lo]
    payload["devicesTruncated"] = True
    return payload


def upload(mac_addresses: list[str], devices: list[tuple[str, int]] | None = None) -> bool:
    """
    スキャン結果を BPS-admin の API へ POST する

    Args:
        mac_addresses: 重複排除済み擬似IDリスト（台数の算出に使う）
        devices: (擬似ID, RSSI) のリスト（省略可）

    Returns:
        bool: 送信成功なら True、失敗なら False
    """
    payload = build_payload(mac_addresses, devices)
    if payload.get("devicesTruncated"):
        print(f"[注意] 送信上限のため devices を {len(payload['devices'])}/{len(devices)} 台に絞りました（RSSIの強い順）")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.BLUETOOTH_SECRET}",
    }

    now_display = datetime.now().strftime("%y/%m/%d/%H:%M:%S")

    try:
        response = requests.post(
            API_ENDPOINT,
            data=_dumps(payload),
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
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    log_path = Path(LOG_DIR) / f"scan_{datetime.now().strftime('%Y%m%d')}.json"

    logs = []
    if log_path.exists():
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
            if not isinstance(logs, list):
                raise ValueError("ログJSONがリスト形式ではありません")
        except (json.JSONDecodeError, ValueError, OSError) as e:
            # 既存JSONが壊れていても以後の保存を止めないよう、退避して作り直す
            backup = log_path.with_suffix(f".corrupt_{datetime.now().strftime('%H%M%S')}.json")
            log_path.replace(backup)
            logs = []
            print(f"[{now_display}] 既存ログが破損のため退避: {backup}（{e}）")

    logs.append({**payload, "savedAt": now_display})

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

    print(f"[{now_display}] ローカル保存: {log_path}")
