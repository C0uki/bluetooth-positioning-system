"""
tools/generate_configs.py
教室ごとの配布用パッケージを一括生成するスクリプト

使い方:
  # per-boothトークン（推奨）
  python tools/generate_configs.py \
    --token-map ../bluetooth-positioning-system-data/credentials/booth_tokens.json \
    --firebase-database-url https://<project>-default-rtdb.asia-southeast1.firebasedatabase.app \
    --firebase-key-file ../bluetooth-positioning-system-data/credentials/firebase_key.json \
    --rssi-csv ../bluetooth-positioning-system-data/rssi_thresholds.csv

  # 単一共有トークン（旧方式・後方互換）
  python tools/generate_configs.py \
    --token-file ../bluetooth-positioning-system-data/credentials/api_token.txt \
    --firebase-database-url https://<project>-default-rtdb.asia-southeast1.firebasedatabase.app

  ※ --token-map と --token-file はどちらか一方を指定する。
  ※ booth_tokens.json は tools/generate_booth_tokens.py で生成でき、
     同じJSONをサーバ（Vercel）の BLUETOOTH_SECRET 環境変数にも設定する。
  ※ RTDB へは認証なし write-only ルール経由で REST 送信するため、
     サービスアカウントキーは配布しない（database.rules.json を参照）。

生成される構成:
  dist/
    class1-1/
      main.py, start.bat, install.bat, requirements.txt
      config/settings.py（教室固有）
      scanner/, processor/, uploader/, logger/
    class1-2/
      ...
"""

import argparse
import csv
import json
import secrets
import shutil
import sys
from pathlib import Path

BOOTH_IDS = [
    "class1-1", "class1-2", "class1-3", "class1-4",
    "class2-1", "class2-2", "class2-3", "class2-4",
    "class3-1", "class3-2", "class3-3", "class3-4",
    "club-esports", "club-art",
    "eat-car-1", "eat-car-2", "eat-car-3", "pta-bazaar",
    "health", "pe-gym",
]

SETTINGS_TEMPLATE = '''\
BOOTH_ID = "{booth_id}"
OPERATOR_ID = f"bt-{{BOOTH_ID}}"
END_TIME = "16:00"

SCAN_INTERVAL_SECONDS = 60
SCAN_DURATION_SECONDS = 10
RSSI_THRESHOLD = {rssi_threshold}

MAC_HASH_SALT = "{mac_salt}"

FIREBASE_DATABASE_URL = "{firebase_database_url}"

API_ENDPOINT = "https://inuso-admin.vercel.app/api/booth/bluetooth"
BLUETOOTH_SECRET = "{token}"
API_TIMEOUT_SECONDS = 10

LOG_DIR = "logs"

LOCAL_PREVIEW_BASELINE_MAX = 20
LOCAL_PREVIEW_SWITCH_TIME = "09:30"
LOCAL_PREVIEW_STDDEV_THRESHOLD = 2.5
LOCAL_PREVIEW_RATIOS = {{
    1: (0,   15),
    2: (16,  35),
    3: (36,  55),
    4: (56,  75),
    5: (76, 100),
}}
'''

COPY_ITEMS = [
    "main.py",
    "start.bat",
    "install.bat",
    "requirements.txt",
    "scanner",
    "processor",
    "uploader",
    "logger",
]

EXTRA_COPY = [
    ("tools/rssi_demo.py", "rssi_demo.py"),
    ("tools/rtdb_test.py", "rtdb_test.py"),
]


def _resolve_tokens(args, booth_ids: list[str]) -> dict:
    """各 boothId に対応するトークンを解決する（単一トークン or per-boothマップ）。"""
    if bool(args.token_map) == bool(args.token_file):
        sys.exit("エラー: --token-map か --token-file のどちらか一方を指定してください。")

    if args.token_file:
        token = Path(args.token_file).read_text(encoding="utf-8").strip()
        if not token:
            sys.exit(f"エラー: トークンが空です: {args.token_file}")
        return {bid: token for bid in booth_ids}

    data = json.loads(Path(args.token_map).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        sys.exit("エラー: --token-map のJSONは {boothId: token} のオブジェクトである必要があります。")
    missing = [bid for bid in booth_ids if not str(data.get(bid, "")).strip()]
    if missing:
        sys.exit("エラー: --token-map に以下のブースのトークンがありません:\n  " + ", ".join(missing))
    unused = [k for k in data if k not in booth_ids]
    if unused:
        print(f"[注意] --token-map に未使用のキーがあります（無視）: {', '.join(unused)}")
    return {bid: str(data[bid]).strip() for bid in booth_ids}


def main():
    parser = argparse.ArgumentParser(description="教室ごとの配布用パッケージを一括生成")
    parser.add_argument("--token-map", default=None,
                        help="boothId→token のJSONファイル（per-boothトークン。--token-fileと併用不可）")
    parser.add_argument("--token-file", default=None,
                        help="全ブース共通の単一APIトークンファイル（旧方式・後方互換。--token-mapと併用不可）")
    parser.add_argument("--firebase-database-url", default="",
                        help="RTDB の URL（例: https://<project>-default-rtdb.asia-southeast1.firebasedatabase.app）。未指定なら RTDB 送信を無効化")
    parser.add_argument("--firebase-key-file", default=None,
                        help="Firebaseサービスアカウントキーのパス。各配布パッケージの credentials/firebase_key.json にコピー")
    parser.add_argument("--rssi-csv", default=None, help="RSSI閾値CSVのパス")
    parser.add_argument("--mac-salt", default=None,
                        help="MACハッシュ用ソルト（未指定時はランダム生成。再生成すると過去データと突合不可になるので記録すること）")
    parser.add_argument("--output-dir", default="dist", help="出力先ディレクトリ（デフォルト: dist）")
    parser.add_argument("--extra", nargs="*", default=[],
                        help="追加のブースID（例: eat-car-4）。--token-map使用時はマップにも同IDのトークンが必要")
    args = parser.parse_args()

    mac_salt = args.mac_salt if args.mac_salt else secrets.token_hex(16)
    booth_ids = BOOTH_IDS + args.extra
    output_dir = Path(args.output_dir)
    project_root = Path(__file__).resolve().parent.parent

    token_map = _resolve_tokens(args, booth_ids)

    rssi_thresholds = {}
    if args.rssi_csv:
        with open(args.rssi_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                bid = row["booth_id"].strip()
                val = row["rssi_threshold"].strip() if row.get("rssi_threshold") else ""
                if val and val.lower() != "none":
                    rssi_thresholds[bid] = int(val)

    firebase_database_url = args.firebase_database_url.strip()

    if output_dir.exists():
        shutil.rmtree(output_dir)

    for booth_id in booth_ids:
        dest = output_dir / booth_id

        for item in COPY_ITEMS:
            src = project_root / item
            if src.is_dir():
                shutil.copytree(src, dest / item, ignore=shutil.ignore_patterns("__pycache__"))
            elif src.is_file():
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest / item)

        for src_rel, dest_name in EXTRA_COPY:
            src = project_root / src_rel
            if src.is_file():
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest / dest_name)

        threshold = rssi_thresholds.get(booth_id)
        rssi_value = str(threshold) if threshold is not None else "None"

        config_dir = dest / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        settings = SETTINGS_TEMPLATE.format(
            booth_id=booth_id,
            token=token_map[booth_id],
            rssi_threshold=rssi_value,
            mac_salt=mac_salt,
            firebase_database_url=firebase_database_url,
        )
        (config_dir / "settings.py").write_text(settings, encoding="utf-8")

        if args.firebase_key_file:
            cred_dir = dest / "credentials"
            cred_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(args.firebase_key_file, cred_dir / "firebase_key.json")

    print(f"{len(booth_ids)} 教室分の配布パッケージを {output_dir} に生成しました。")
    print(f"各フォルダをUSBで各Surfaceにコピーしてください。")
    if not args.mac_salt:
        print()
        print(f"[重要] MAC_HASH_SALT = {mac_salt}")
        print("       このソルトを必ず記録してください。再生成すると擬似IDが変わり、")
        print("       過去に収集したデータと突合できなくなります。")


if __name__ == "__main__":
    main()
