# bluetooth-positioning-system

ISF文化祭（2026-09-07）Bluetooth混雑検知システム — Surface側スキャン・送信コード。
Couki担当。Webアプリ側（Vercel API・Firestore・画面）はShoki担当。

## 関連リポジトリ

- `bluetooth-positioning-system`（Public・本リポジトリ）— Surfaceで動くスキャン・送信コード
- `bluetooth-positioning-system-data`（Private）— トークン・ドキュメント

## セットアップ

```bash
pip install -r requirements.txt
python main.py
```

## 配布パッケージ生成

```bash
python tools/generate_configs.py \
  --token-map ../bluetooth-positioning-system-data/credentials/booth_tokens.json

# RSSI閾値を指定する場合（朝テスト後）
#   --rssi-csv ../bluetooth-positioning-system-data/rssi_thresholds.csv
```

トークン生成:
```bash
python tools/generate_booth_tokens.py \
  --output ../bluetooth-positioning-system-data/credentials/booth_tokens.json
```

## プロジェクト構成

| パス | 役割 |
|---|---|
| `scanner/bluetooth_scanner.py` | BLEスキャン。MAC→ソルト付きSHA-256擬似IDに変換 |
| `processor/mac_deduplicator.py` | 擬似IDの重複排除 |
| `uploader/api_uploader.py` | Vercel API送信（Bearer認証・per-boothトークン） |
| `logger/rssi_logger.py` | ローカルCSV記録（全件記録） |
| `tools/generate_configs.py` | 教室別配布パッケージ生成（dist/に出力） |
| `tools/generate_booth_tokens.py` | per-boothトークンJSON生成 |
| `config/settings.py` | 設定ファイル（generate_configs.pyが教室ごとに書き換え） |

## ブースID（18件・ASCII slug）

```
class1-1, class1-2, class1-3, class1-4,
class2-1, class2-2, class2-3, class2-4,
class3-1, class3-2, class3-3, class3-4,
club-esports, club-art,
eat-car-1, eat-car-2, eat-car-3,
pta-bazaar
```

## セキュリティ・プライバシー注意事項

- `dist/` は絶対にこのリポジトリへpushしない（.gitignore済み・サービスアカウントキー含有リスク）
- `credentials/` はPrivateリポジトリ（bluetooth-positioning-system-data）で管理
- 生MACアドレスは保存・送信しない（ソルト付きハッシュで擬似ID化）
- プライバシー方針（会場掲示・データ保持期間・イベント後のソルト破棄）は `docs/privacy.md` を参照
- RSSIログの保持期限は 2027-03-31。位置推定の検証完了後はソルトを破棄する
- `booth_tokens.json` は秘密情報（gitにコミットしない）
