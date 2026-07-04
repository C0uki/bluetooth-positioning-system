"""
uploader/rtdb_uploader.py
RSSIスキャン結果を Firebase Realtime Database へ送信するモジュール

Firebase Admin SDK 方式:
  credentials/firebase_key.json のサービスアカウントキーで認証し、
  RTDB の rssi_logs/<date>/<booth> 配下へ append-only で書き込む。
  キーファイルが存在しない場合は RTDB 送信をスキップする。
"""

import collections
import uuid
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

    if not records:
        return

    if not _send_batch(records):
        if len(_queue) == _queue.maxlen:
            print(f"[RTDB] 未送信キューが上限（{_queue.maxlen}バッチ）のため、最古のバッチ {len(_queue[0])} 件を破棄します")
        _queue.append(records)


def _entry_key(record: dict) -> str:
    # Admin SDK の push() は1件ごとにHTTP POSTが発生するため使わず、
    # キーはローカルで生成する（timestamp接頭辞で時刻順ソート可能に保つ）。
    time_part = record["timestamp"][11:19].replace(":", "")
    return f"{time_part}_{uuid.uuid4().hex[:12]}"


def _send_batch(records: list[dict]) -> bool:
    """1スキャン分を multi-location update で一括送信する（HTTPリクエスト1回）"""
    ref = _db.reference(f"rssi_logs/{records[0]['date']}/{settings.BOOTH_ID}")
    updates = {
        _entry_key(r): {
            "timestamp": r["timestamp"],
            "mac_hash": r["mac_hash"],
            "rssi": r["rssi"],
            "passed_filter": r["passed_filter"],
        }
        for r in records
    }
    try:
        ref.update(updates)
        return True
    except Exception as e:
        print(f"[RTDB] バッチ送信失敗（{len(records)}件・未送信キューで保持し次回再送）: {e}")
        return False


def _flush_queue() -> None:
    while _queue:
        if not _send_batch(_queue[0]):
            break
        _queue.popleft()
