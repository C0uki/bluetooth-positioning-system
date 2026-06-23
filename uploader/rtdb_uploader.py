"""
uploader/rtdb_uploader.py
RSSIスキャン結果を Firebase Realtime Database へ送信するモジュール
"""

import collections
from datetime import datetime
from pathlib import Path

import config.settings as settings

_firebase_app = None
_db = None
_initialized = False
_queue: collections.deque = collections.deque(maxlen=10)


def _ensure_initialized() -> bool:
    global _firebase_app, _db, _initialized

    if _initialized:
        return _db is not None

    _initialized = True

    url = settings.FIREBASE_DATABASE_URL
    if not url:
        print("[RTDB] URL未設定のためスキップ")
        return False

    key_path = Path(__file__).resolve().parent.parent / "credentials" / "firebase_key.json"
    if not key_path.exists():
        print(f"[RTDB] サービスアカウントキーが見つかりません: {key_path}")
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials, db

        cred = credentials.Certificate(str(key_path))
        _firebase_app = firebase_admin.initialize_app(cred, {"databaseURL": url})
        _db = db
        return True
    except Exception as e:
        print(f"[RTDB] Firebase初期化エラー: {e}")
        return False


def upload_rssi(scan_results: list[dict]) -> None:
    if not _ensure_initialized():
        return

    _flush_queue()

    records = []
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    timestamp = now.isoformat()

    for result in scan_results:
        records.append({
            "booth_id": settings.BOOTH_ID,
            "date": date_str,
            "timestamp": timestamp,
            "mac_address": result["mac"],
            "rssi": result["rssi"],
            "passed_filter": result["passed_filter"],
        })

    try:
        _send_records(records, date_str)
    except Exception as e:
        print(f"[RTDB] 送信失敗、キューに追加: {e}")
        _queue.append(records)


def _send_records(records: list[dict], date_str: str) -> None:
    ref = _db.reference(f"rssi_logs/{date_str}/{settings.BOOTH_ID}")
    for record in records:
        ref.push({
            "timestamp": record["timestamp"],
            "mac_address": record["mac_address"],
            "rssi": record["rssi"],
            "passed_filter": record["passed_filter"],
        })


def _flush_queue() -> None:
    while _queue:
        records = _queue[0]
        try:
            date_str = records[0]["date"] if records else datetime.now().strftime("%Y-%m-%d")
            _send_records(records, date_str)
            _queue.popleft()
        except Exception:
            break
