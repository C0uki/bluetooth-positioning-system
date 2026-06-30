# ISFプロジェクト - Bluetooth混雑検知システム

ISF webapp（高等学校 文化祭向け情報共有PWAアプリ）向け
Bluetooth を利用した混雑状況自動検知システム

---

## 概要

各ブースに設置した Surface 端末が、来場者のスマートフォンから発信される
Bluetooth 信号を検知し、デバイス数をカウントします。
検知結果は管理用 Vercel の API（`/api/booth/bluetooth`）に送信され、
混雑レベルの計算・Firestore への保存はサーバー側で行われます。

> このプログラムは「センサー」としての役割に専念します。
> 混雑レベルの判定ロジック自体は Shoki が実装する API Route 側で動作します。

**生 MAC アドレスは一切保存・送信しません。**
スキャン時にソルト付き SHA-256 で擬似 ID に変換します。

---

## システム構成

```
Surface（各ブース・1台固定）
  └── main.py 実行
        ├── scanner/bluetooth_scanner.py
        │     BLE スキャン → ソルト付き SHA-256 で擬似IDに変換（生MACは保持しない）
        ├── processor/mac_deduplicator.py
        │     擬似IDの重複排除
        ├── logger/rssi_logger.py
        │     RSSI・擬似IDをローカル CSV に記録（RTDBの成否に関わらず全件）
        └── uploader/
              ├── api_uploader.py
              │     管理用Vercel API への POST 送信（Bearer 認証・per-booth トークン）
              │           ↓
              │     Vercel API Route（Shoki実装）
              │           ├── 混雑レベル算出
              │           ├── Firestore booths コレクション更新
              │           └── 閲覧用Vercelへ revalidation リクエスト
              └── rtdb_uploader.py
                    Firebase RTDB への RSSI ログ送信（認証なし write-only REST）
```

---

## 送信データ形式

`POST /api/booth/bluetooth` へ以下の JSON を送信します。

```json
{
  "boothId": "class1-1",
  "deviceCount": 18,
  "macAddresses": ["a1b2c3d4e5f60001", "a1b2c3d4e5f60002"],
  "operatorId": "bt-class1-1"
}
```

| フィールド | 説明 |
|---|---|
| `boothId` | 設置ブースのID |
| `deviceCount` | 重複排除済みデバイス数 |
| `macAddresses` | 重複排除済み**擬似ID**（ソルト付き SHA-256 ハッシュ、16文字）のリスト |
| `operatorId` | 固定文字列 `bt-{boothId}`（changeLogs 記録用） |

---

## ブースID一覧（20件）

```
class1-1, class1-2, class1-3, class1-4,
class2-1, class2-2, class2-3, class2-4,
class3-1, class3-2, class3-3, class3-4,
club-esports, club-art,
eat-car-1, eat-car-2, eat-car-3, pta-bazaar,
health, pe-gym
```

---

## セットアップ

### 1. Python インストール

Python 3.12 をインストールしてください。

### 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. 設定ファイルの編集

`config/settings.py` を編集してください（通常は `generate_configs.py` が自動生成します）：

- `BOOTH_ID`：設置ブースのID
- `BLUETOOTH_SECRET`：API 認証トークン（Privateリポジトリで管理）
- `FIREBASE_DATABASE_URL`：Firebase RTDB の URL（未設定なら RTDB 送信をスキップ）
- `MAC_HASH_SALT`：擬似ID生成用ソルト（配布パッケージ生成時に一括設定）
- `RSSI_THRESHOLD`：RSSI フィルタ閾値（`None` でフィルタ無効）

### 4. 実行

```bash
python main.py
```

---

## 配布パッケージ生成

本番向けに各ブース固有の設定を含んだ配布パッケージを一括生成します。

```bash
python tools/generate_configs.py \
  --token-map ../bluetooth-positioning-system-data/credentials/booth_tokens.json \
  --firebase-database-url https://<project>-default-rtdb.asia-southeast1.firebasedatabase.app

# Firebase SA キーを各パッケージに同梱する場合
#   --firebase-key-file ../bluetooth-positioning-system-data/credentials/firebase_key.json

# RSSI 閾値を指定する場合（朝テスト後）
#   --rssi-csv ../bluetooth-positioning-system-data/rssi_thresholds.csv
```

生成結果は `dist/<booth_id>/` に出力されます。各フォルダを USB で各 Surface にコピーしてください。

トークン生成:
```bash
python tools/generate_booth_tokens.py \
  --output ../bluetooth-positioning-system-data/credentials/booth_tokens.json
```

---

## プロジェクト構成

| パス | 役割 |
|---|---|
| `main.py` | エントリポイント。スキャン・記録・送信のループを管理 |
| `scanner/bluetooth_scanner.py` | BLE スキャン。MAC → ソルト付き SHA-256 擬似IDに変換 |
| `processor/mac_deduplicator.py` | 擬似IDの重複排除 |
| `uploader/api_uploader.py` | Vercel API 送信（Bearer 認証・per-booth トークン） |
| `uploader/rtdb_uploader.py` | Firebase RTDB 送信（認証なし REST・append-only） |
| `logger/rssi_logger.py` | ローカル CSV 記録（RTDB の成否に関わらず全件記録） |
| `tools/generate_configs.py` | 教室別配布パッケージ生成（`dist/` に出力） |
| `tools/generate_booth_tokens.py` | per-booth トークン JSON 生成 |
| `config/settings.py` | 設定ファイル（`generate_configs.py` がブースごとに書き換え） |

---

## セキュリティ注意事項

- `dist/` は絶対にこのリポジトリへ push しない（`.gitignore` 済み・SA キー含有リスク）
- `credentials/` は Private リポジトリ（`bluetooth-positioning-system-data`）で管理
- 生 MAC アドレスは保存・送信しない（ソルト付きハッシュで擬似 ID 化）
- RTDB 送信は認証なし write-only ルール経由（SA キーは配布しない）
- `FIREBASE_DATABASE_URL` は秘密情報ではない（公開OK）
- `booth_tokens.json` は秘密情報（git にコミットしない）

---

## 混雑レベル定義

| 値 | 表示名 |
|---|---|
| 0 | 停止中（手動設定のみ） |
| 1 | 非常に閑散 |
| 2 | 閑散 |
| 3 | 通常 |
| 4 | 混雑 |
| 5 | 非常に混雑 |

---

## 開発体制

| 担当 | 内容 |
|---|---|
| Couki（[@C0uki](https://github.com/C0uki)） | Bluetooth 実装（Surface 側スキャン・送信） |
| Shoki | Web アプリ全体（閲覧用・管理用 Vercel、API Route、混雑レベル算出ロジック） |

---

*制作: ISFプロジェクト*
