# Bluetooth Positioning System（v5対応）

ISF webapp（犬山総合高等学校 文化祭向け情報共有PWAアプリ）向け
Bluetooth を利用した混雑状況自動検知システム

---

## 概要

各教室に設置した Surface 端末が、来場者のスマートフォンから発信される
Bluetooth 信号を検知し、デバイス数をカウントします。
検知結果は管理用Vercel の API（`/api/booth/bluetooth`）に送信され、
混雑レベルの計算・Firestore への保存はサーバー側で行われます。

> このプログラムは「センサー」としての役割に専念します。
> 混雑レベルの判定ロジック自体は Shoki が実装する API Route 側で動作します。

---

## システム構成（v5）

```
Surface（各教室・1台固定）
  └── main.py 実行
        ├── scanner/       Bluetooth スキャン（bleak）
        ├── processor/
        │     ├── mac_deduplicator.py      MACアドレス重複排除
        │     └── congestion_calculator.py 【ローカル確認専用】参考値の計算
        └── uploader/
              └── api_uploader.py  管理用Vercel API への POST 送信
                    ↓
        Vercel API Route（Shoki実装）
              ├── 混雑レベル算出（C-3 ハイブリッド型）
              ├── Firestore booths コレクション更新
              ├── changeLogs へ記録
              └── 閲覧用Vercelへ revalidation リクエスト
```

---

## 送信データ形式

`POST /api/booth/bluetooth` へ以下の JSON を送信します。

```json
{
  "boothId": "class1-1",
  "deviceCount": 18,
  "macAddresses": ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"],
  "operatorId": "bt-class1-1"
}
```

| フィールド | 説明 |
|---|---|
| `boothId` | 設置教室のブースID（企画書v5 §9.2 命名規則） |
| `deviceCount` | 重複排除済みデバイス数 |
| `macAddresses` | 重複排除済み MAC アドレスリスト |
| `operatorId` | 固定文字列 `bt-{boothId}`（changeLogs記録用） |

---

## 混雑レベル定義（企画書v5 §8.2）

| 値 | 表示名 |
|---|---|
| 0 | 停止中（手動設定のみ） |
| 1 | 非常に閑散 |
| 2 | 閑散 |
| 3 | 通常 |
| 4 | 混雑 |
| 5 | 非常に混雑 |

---

## セットアップ

### 1. Python インストール

Python 3.12 をインストールしてください。

### 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. 設定ファイルの編集

`config/settings.py` を編集してください：

- `BOOTH_ID`：設置教室のブースID
- `API_ENDPOINT`：Shokiから共有される管理用VercelのURL
- `API_AUTH_TOKEN`：API認証トークン（Shokiと要相談）

### 4. 実行

```bash
python main.py
```

---

## フェイルオーバー

API への送信が失敗した場合：
- ローカルにスキャンログを保存（`bluetooth-positioning-system-data/logs/`）
- 管理者セクションに警告表示（Shoki側API実装）
- 接続復旧後に手動での再送信を検討

---

## ローカル動作確認について

`processor/congestion_calculator.py` は本番では使用されませんが、
Surface単体でのテスト時に「想定される混雑レベル」をコンソールに表示します。
このロジックは Shoki への実装仕様としてそのまま使用できます
（企画書v5 §8.4「C-3 ハイブリッド型」準拠）。

---

## 開発体制

| 担当 | 内容 |
|---|---|
| Couki（[@C0uki](https://github.com/C0uki)） | Bluetooth実装（Surface側スキャン・送信） |
| Shoki | Web アプリ全体（閲覧用・管理用Vercel、API Route、混雑レベル算出ロジック） |

---

*制作: 犬山総合高等学校生徒 / ISF webapp 企画書v5準拠*
