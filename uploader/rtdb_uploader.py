"""
uploader/rtdb_uploader.py
RSSIスキャン結果を Firebase Realtime Database へ送信するモジュール

認証なし write-only 方式（B1）:
  サービスアカウントキーは配布せず、RTDB の REST API へ直接 POST する。
  書き込みは RTDB セキュリティルールで rssi_logs/<date>/<booth> 配下への
  「新規追加のみ（上書き・削除・読み取り不可）＋フィールド/型検証」に限定される。
  ルール定義は data リポジトリの database.rules.json を参照。
"""

import collections
from datetime import datetime

import requests

import config.settings as settings

RTDB_TIMEOUT_SECONDS = 10

_base_url: str | None = None
_session: requests.Session | None = None
_initialized = False
_queue: collections.deque = collections.deque(maxlen=10)


def _ensure_initialized() -> bool:
    global _base_url, _session, _initialized

    if _initialized:
        return _base_url is not None

    _initialized = True

    url = settings.FIREBASE_DATABASE_URL
    if not url:
        print("[RTDB] URL未設定のためスキップ")
        return False

    _base_url = url.rstrip("/")
    _session = requests.Session()
    return True


def upload_rssi(scan_results: list[dict]) -> None:
    if not _ensure_initialized():
        return

    _flush_queue()

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    timestamp = now.isoformat()

    records = [
        {
            "date": date_str,
            "timestamp": timestamp,
            "mac_hash": result["mac_hash"],
            "rssi": result["rssi"],
            "passed_filter": result["passed_filter"],
        }
        for result in scan_results
    ]

    unsent = _send_records(records)
    if unsent:
        _queue.append(unsent)


def _send_records(records: list[dict]) -> list[dict]:
    """
    レコードを1件ずつ POST する（ルールが新規追加のみ許可のため push 単位で送信）。

    Returns:
        送信できなかった残りのレコード（成功時は空リスト）。
        途中で失敗した場合は、未送信分のみを返して重複送信を最小化する。
    """
    for i, record in enumerate(records):
        try:
            _post_one(record)
        except Exception as e:
            print(f"[RTDB] 送信失敗、キューに追加: {e}")
            return records[i:]
    return []


def _post_one(record: dict) -> None:
    url = f"{_base_url}/rssi_logs/{record['date']}/{settings.BOOTH_ID}.json"
    response = _session.post(
        url,
        json={
            "timestamp": record["timestamp"],
            "mac_hash": record["mac_hash"],
            "rssi": record["rssi"],
            "passed_filter": record["passed_filter"],
        },
        timeout=RTDB_TIMEOUT_SECONDS,
    )
    response.raise_for_status()


def _flush_queue() -> None:
    while _queue:
        unsent = _send_records(_queue[0])
        if unsent:
            _queue[0] = unsent
            break
        _queue.popleft()
