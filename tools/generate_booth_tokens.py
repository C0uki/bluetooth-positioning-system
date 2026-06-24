"""
tools/generate_booth_tokens.py
ブースごとのランダムなAPIトークンを生成し、boothId→token のJSONマップを出力する。

出力したJSONは2か所で同じものを使う:
  1. サーバ（Vercel）の環境変数 BLUETOOTH_SECRET にそのまま設定（token↔booth束縛の検証用）
  2. tools/generate_configs.py の --token-map に渡す（各Surfaceに自分のトークンだけ埋め込む）

使い方:
  python tools/generate_booth_tokens.py \
    --output ../bluetooth-positioning-system-data/credentials/booth_tokens.json

  ※ 既存ファイルがある場合は --force を付けないと上書きしない（誤再生成でトークンが
     ずれて全Surface再配布が必要になるのを防ぐため）。
  ※ booth_tokens.json は秘密情報。git にコミットしない（credentials/ は .gitignore 済み）。
"""

import argparse
import json
import secrets
import sys
from pathlib import Path

from generate_configs import BOOTH_IDS


def main():
    parser = argparse.ArgumentParser(description="ブースごとのAPIトークンを生成しJSONマップを出力")
    parser.add_argument("--output", default="booth_tokens.json", help="出力先JSONパス（デフォルト: booth_tokens.json）")
    parser.add_argument("--extra", nargs="*", default=[], help="追加のブースID（generate_configsの--extraと揃える）")
    parser.add_argument("--force", action="store_true", help="既存の出力ファイルを上書きする")
    args = parser.parse_args()

    booth_ids = BOOTH_IDS + args.extra
    if len(set(booth_ids)) != len(booth_ids):
        sys.exit("エラー: boothId に重複があります。")

    output = Path(args.output)
    if output.exists() and not args.force:
        sys.exit(f"エラー: {output} は既に存在します。上書きするには --force を付けてください。")

    tokens = {bid: secrets.token_hex(32) for bid in booth_ids}
    output.write_text(json.dumps(tokens, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{len(tokens)} 個のトークンを {output} に生成しました。")
    print()
    print("次の手順:")
    print(f"  1. このJSONの中身をサーバ（Vercel）の環境変数 BLUETOOTH_SECRET に設定")
    print(f"  2. 配布生成時に --token-map {output} を指定")
    print()
    print("[重要] このファイルは秘密情報です。git にコミットせず、安全に保管してください。")


if __name__ == "__main__":
    main()
