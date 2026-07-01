"""
tools/rtdb_test.py
Firebase RTDB への疎通確認スクリプト（Firebase Admin SDK 方式）

使い方:
  python tools/rtdb_test.py
  python tools/rtdb_test.py --booth class1-1
  python tools/rtdb_test.py --key credentials/firebase_key.json
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# tools/内からの実行: parent.parent = プロジェクトルート
# dist/booth/内からの実行: parent = ブースフォルダ
_here = Path(__file__).resolve().parent
DEFAULT_KEY = (
    _here / "credentials" / "firebase_key.json"
    if (_here / "credentials" / "firebase_key.json").exists()
    else _here.parent / "credentials" / "firebase_key.json"
)
RTDB_URL = "https://isf-webapp-default-rtdb.asia-southeast1.firebasedatabase.app"


def main():
    parser = argparse.ArgumentParser(description="Firebase RTDB 疎通確認（Admin SDK）")
    parser.add_argument("--key", default=str(DEFAULT_KEY), help="SAキーのパス")
    parser.add_argument("--url", default=RTDB_URL, help="RTDB URL")
    parser.add_argument("--booth", default="test-booth", help="ブースID（デフォルト: test-booth）")
    args = parser.parse_args()

    key_path = Path(args.key)
    if not key_path.exists():
        sys.exit(f"❌ SAキーが見つかりません: {key_path}\n"
                 f"  Shoki から受け取った firebase_key.json を credentials/ に置いてください。")

    try:
        import firebase_admin
        from firebase_admin import credentials, db as rtdb
    except ImportError:
        sys.exit("❌ firebase-admin がインストールされていません。\n"
                 "  pip install firebase-admin を実行してください。")

    print("=== Firebase RTDB 疎通確認（Admin SDK）===")
    print(f"SAキー: {key_path}")
    print(f"RTDB URL: {args.url}")
    print(f"ブースID: {args.booth}")
    print()

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(str(key_path))
            firebase_admin.initialize_app(cred, {"databaseURL": args.url})

        date = datetime.now().strftime("%Y-%m-%d")
        ref = rtdb.reference(f"rssi_logs/{date}/{args.booth}")
        result = ref.push({
            "timestamp": datetime.now().isoformat(),
            "mac_hash": "testdeadbeef0001",
            "rssi": -65,
            "passed_filter": True,
        })
        print(f"✅ 成功: key={result.key}")
        print()
        print("Firebase Console で確認:")
        print(f"  Realtime Database → データ → rssi_logs → {date} → {args.booth}")

    except Exception as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
