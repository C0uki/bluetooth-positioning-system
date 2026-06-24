# bluetooth-positioning-system

ISF文化祭（2026-09-07）Bluetooth混雑検知システム — Surface側スキャン・送信コード。
Couki担当。Webアプリ側（Vercel API・Firestore・画面）はShoki担当。

## 関連リポジトリ

- `bluetooth-positioning-system`（Public・本リポジトリ）— Surfaceで動くスキャン・送信コード
- `bluetooth-positioning-system-data`（Private）— トークン・RTDBルール・ドキュメント

## セットアップ

```bash
pip install -r requirements.txt
python main.py
```

## 配布パッケージ生成

```bash
python tools/generate_configs.py \
  --token-map ../bluetooth-positioning-system-data/credentials/booth_tokens.json \
  --firebase-database-url https://isf-db-6eec4-default-rtdb.asia-southeast1.firebasedatabase.app

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
| `uploader/rtdb_uploader.py` | Firebase RTDB送信（認証なしREST・append-only） |
| `logger/rssi_logger.py` | ローカルCSV記録（RTDBの成否に関わらず全件記録） |
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

## セキュリティ注意事項

- `dist/` は絶対にこのリポジトリへpushしない（.gitignore済み・サービスアカウントキー含有リスク）
- `credentials/` はPrivateリポジトリ（bluetooth-positioning-system-data）で管理
- 生MACアドレスは保存・送信しない（ソルト付きハッシュで擬似ID化）
- RTDB送信は認証なしwrite-onlyルール経由（SA鍵は配布しない）
- `FIREBASE_DATABASE_URL` は秘密情報ではない（公開OK）
- `booth_tokens.json` は秘密情報（gitにコミットしない）
