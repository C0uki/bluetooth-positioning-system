"""
tools/rtdb_test.py
Firebase RTDB への疎通確認スクリプト

使い方:
  python tools/rtdb_test.py
  python tools/rtdb_test.py --booth class1-1
  python tools/rtdb_test.py --url https://<project>-default-rtdb.asia-southeast1.firebasedatabase.app
"""

import argparse
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    sys.exit("requests がインストールされていません。pip install requests を実行してください。")

RTDB_URL = "https://isf-db-6eec4-default-rtdb.asia-southeast1.firebasedatabase.app"


def test_write(rtdb_url: str, booth_id: str) -> bool:
    date = datetime.now().strftime("%Y-%m-%d")
    url = f"{rtdb_url}/rssi_logs/{date}/{booth_id}.json"
    payload = {
        "timestamp": datetime.now().isoformat(),
        "mac_hash": "testdeadbeef0001",
        "rssi": -65,
        "passed_filter": True,
    }

    print(f"送信先: {url}")
    print(f"ペイロード: {payload}")
    print()

    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print(f"✅ 成功 (200): {r.text}")
            print()
            print("Firebase Console で確認:")
            print(f"  Realtime Database → データ → rssi_logs → {date} → {booth_id}")
            return True
        else:
            print(f"❌ エラー ({r.status_code}): {r.text}")
            if r.status_code == 401 or "Permission denied" in r.text:
                print()
                print("→ RTDBセキュリティルールがデプロイされていません。")
                print("  Shoki に database.rules.json のデプロイを依頼してください。")
            return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 接続エラー: {e}")
        print("→ ネットワーク接続を確認してください。")
        return False
    except requests.exceptions.Timeout:
        print("❌ タイムアウト: Firebase に接続できませんでした。")
        return False


def main():
    parser = argparse.ArgumentParser(description="Firebase RTDB 疎通確認")
    parser.add_argument("--url", default=RTDB_URL, help="RTDB URL")
    parser.add_argument("--booth", default="test-booth", help="ブースID（デフォルト: test-booth）")
    args = parser.parse_args()

    print("=== Firebase RTDB 疎通確認 ===")
    print()
    success = test_write(args.url, args.booth)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
