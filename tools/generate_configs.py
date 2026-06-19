"""
tools/generate_configs.py
教室ごとの配布用フォルダを一括生成するスクリプト

使い方:
  python tools/generate_configs.py --token-file ../bluetooth-positioning-system-data/credentials/api_token.txt
"""

import argparse
from pathlib import Path

CLASSROOMS = []
for grade in range(1, 4):
    for cls in range(1, 5):
        CLASSROOMS.append(f"class-{grade}-{cls}")

TEMPLATE = '''\
BOOTH_ID = "{booth_id}"
OPERATOR_ID = f"bt-{{BOOTH_ID}}"
END_TIME = "16:00"

SCAN_INTERVAL_SECONDS = 90
SCAN_DURATION_SECONDS = 10
RSSI_THRESHOLD = None

API_ENDPOINT = "https://inuso-admin.vercel.app/api/booth/bluetooth"
BLUETOOTH_SECRET = "{token}"
API_TIMEOUT_SECONDS = 10

LOG_DIR = "../bluetooth-positioning-system-data/logs"

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


def main():
    parser = argparse.ArgumentParser(description="教室ごとの配布用設定を生成")
    parser.add_argument("--token-file", required=True, help="APIトークンファイルのパス")
    parser.add_argument("--output-dir", default="dist", help="出力先ディレクトリ（デフォルト: dist）")
    parser.add_argument("--extra", nargs="*", default=[], help="追加の教室ID（例: club-art eat-car-1）")
    args = parser.parse_args()

    token = Path(args.token_file).read_text(encoding="utf-8").strip()
    classrooms = CLASSROOMS + args.extra
    output_dir = Path(args.output_dir)

    for booth_id in classrooms:
        folder = output_dir / booth_id / "config"
        folder.mkdir(parents=True, exist_ok=True)
        settings = TEMPLATE.format(booth_id=booth_id, token=token)
        (folder / "settings.py").write_text(settings, encoding="utf-8")

    print(f"{len(classrooms)} 教室分の設定を {output_dir} に生成しました。")


if __name__ == "__main__":
    main()
