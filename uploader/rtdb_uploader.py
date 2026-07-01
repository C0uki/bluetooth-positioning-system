"""
uploader/rtdb_uploader.py
RSSIスキャン結果を Firebase Realtime Database へ送信するモジュール

Firebase Admin SDK 方式:
  credentials/firebase_key.json のサービスアカウントキーで認証し、
  RTDB の rssi_logs/<date>/<booth> 配下へ append-only で書き込む。
  キーファイルが存在しない場合は RTDB 送信をスキップする。
"""

import collections
from datetime import datetime
from pathlib import Path

import config.settings as settings

_db = None
_initialized = False
_queue: collections.deque = collections.deque(maxlen=10)

_project_root = Path(__file__).resolve().parent.parent
KEY_PATH = _project_root / "credentials" / "firebase_key.json"


def _ensure_initialized() -> bool:
    global _db, _initialized

    if _initialized:
        return _db is not None

    _initialized = True

    if not settings.FIREBASE_DATABASE_URL:
        print("[RTDB] URL未設定のためスキップ")
        return False

    if not KEY_PATH.exists():
        print(f"[RTDB] SAキーが見つかりません（{KEY_PATH}）。RTDB送信をスキップします。")
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials, db as rtdb

        if not firebase_admin._apps:
            cred = credentials.Certificate(str(KEY_PATH))
            firebase_admin.initialize_app(cred, {
                "databaseURL": settings.FIREBASE_DATABASE_URL,
            })

        _db = rtdb
        print("[RTDB] Firebase Admin SDK 初期化完了")
        return True

    except Exception as e:
        print(f"[RTDB] 初期化失敗: {e}")
        return False


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
    for i, record in enumerate(records):
        try:
            _push_one(record)
        except Exception as e:
            print(f"[RTDB] 送信失敗、キューに追加: {e}")
            return records[i:]
    return []


def _push_one(record: dict) -> None:
    ref = _db.reference(f"rssi_logs/{record['date']}/{settings.BOOTH_ID}")
    ref.push({
        "timestamp": record["timestamp"],
        "mac_hash": record["mac_hash"],
        "rssi": record["rssi"],
        "passed_filter": record["passed_filter"],
    })


def _flush_queue() -> None:
    while _queue:
        unsent = _send_records(_queue[0])
        if unsent:
            _queue[0] = unsent
            break
        _queue.popleft()
