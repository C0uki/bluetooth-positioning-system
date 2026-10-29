# BPSプロジェクト - Bluetooth混雑検知システム

BPS webapp（高等学校 文化祭向け情報共有PWAアプリ）向け
Bluetooth を利用した混雑状況自動検知システム

---

## 概要

各ブースに設置した Surface 端末が、来場者のスマートフォンから発信される
Bluetooth 信号を検知し、デバイス数をカウントします。
検知結果はBPS-admin の API（`/api/booth/bluetooth`、`https://adac.saka2931.jp`）に送信され、
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
        │     RSSI・擬似IDをローカル CSV に記録（全件記録）
        └── uploader/
              └── api_uploader.py
              │     BPS-admin の API への POST 送信（Bearer 認証・per-booth トークン）
              │           ↓
              │     BPS-admin の API（Shoki実装）
              │           ├── 混雑レベル算出
              │           ├── Firestore booths コレクション更新
              │           └── BPS-viewer のデータ配信 Worker（Cloudflare）へキャッシュ無効化リクエスト
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
  --token-map ../bluetooth-positioning-system-data/credentials/booth_tokens.json

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
| `uploader/api_uploader.py` | BPS-admin の API 送信（Bearer 認証・per-booth トークン） |
| `logger/rssi_logger.py` | ローカル CSV 記録（全件記録） |
| `tools/generate_configs.py` | 教室別配布パッケージ生成（`dist/` に出力） |
| `tools/generate_booth_tokens.py` | per-booth トークン JSON 生成 |
| `config/settings.py` | 設定ファイル（`generate_configs.py` がブースごとに書き換え） |

---

## プライバシーへの配慮

来場者のプライバシー保護方針は [docs/privacy.md](docs/privacy.md) に定めています。要点:

- 生 MAC アドレスはスキャン時に即時ハッシュ化し、保存・送信は一切しない
- アドバタイジングパケットの存在検知によるカウントのみで、通信内容は傍受しない
- 会場入口・各ブースに計測の目的と方法を掲示する（掲示文テンプレートは docs/privacy.md 参照）
- RSSI ログは検証目的に限り保持し、保持期限（2027-03-31）までに削除する
- 位置推定の検証完了後にソルトを破棄し、擬似IDと端末の対応付けを不可能にする

---

## セキュリティ注意事項

- `dist/` は絶対にこのリポジトリへ push しない（`.gitignore` 済み・SA キー含有リスク）
- `credentials/` は Private リポジトリ（`bluetooth-positioning-system-data`）で管理
- 生 MAC アドレスは保存・送信しない（ソルト付きハッシュで擬似 ID 化）
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
| Shoki （[@sho29saka31](https://github.com/sho29saka31)）| Web アプリ全体（BPS-viewer・BPS-admin、API、混雑レベル算出ロジック） |

---

*制作: BPSプロジェクト*
