# Bluetooth 混雑計測システム連携仕様 — inuso-admin

Surface Go 2 から送られてくる Bluetooth デバイス数を受信し、  
C-3 アルゴリズムで混雑レベルを算出して Firestore に保存する仕組みを説明します。

---

## システム概要

```
Surface Go 2
  └── bluetooth-positioning-system (Python)
       └── Bluetooth LE スキャン
            └── POST /api/booth/bluetooth（Bearer 認証）
                 └── C-3 算出 → Firestore 更新 → Viewer ISR 無効化
```

---

## API エンドポイント仕様

### `POST /api/booth/bluetooth`

**認証:** `Authorization: Bearer <トークン>`

トークンは **per-booth（ブースごとに異なる）方式**に対応しています。サーバー側の環境変数
`BLUETOOTH_SECRET` の内容によって照合方法が切り替わります。

| `BLUETOOTH_SECRET` の形式 | 照合方法 |
|---|---|
| `{ "boothId": "token", ... }` のJSONマップ | リクエストの `boothId` に対応するトークン（`map[boothId]`）と Bearer を照合 |
| 単一文字列（旧方式・後方互換） | 全ブース共通トークンとして Bearer を照合 |

- スキャナ側の `booth_tokens.json`（`{boothId: token}`）と**同じ内容**をサーバーの `BLUETOOTH_SECRET` に設定すると、ブース単位のトークン照合になります。
- 照合はタイミングセーフ比較。未設定・トークン不一致・`boothId` がマップに未登録 → **401**。

**リクエスト:**
```json
{
  "boothId": "class1-1",
  "deviceCount": 12,
  "operatorId": "bt-class1-1",
  "macAddresses": ["<擬似ID>", "..."]
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `boothId` | string | ✅ | Firestore の `booths/{boothId}` ドキュメント ID |
| `deviceCount` | number | ✅ | スキャンで検出したデバイス数（**JSON 数値型**であること） |
| `operatorId` | string | — | 変更ログに記録する送信元識別子。省略時は `bt-<boothId>` |
| `macAddresses` | string[] | — | 受信するが**サイト側は未使用**（`deviceCount` のみ参照） |

**レスポンス（成功）:**
```json
{ "ok": true, "status": 3 }
```

**レスポンス（手動モードスキップ）:**
```json
{ "ok": true, "skipped": true, "reason": "manual mode" }
```

**レスポンス（エラー）:**
```json
{ "error": "booth not found", "boothId": "class1-1" }   // 400: ブース未登録
{ "error": "boothId and deviceCount required" }          // 400: 必須欠落
{ "error": "invalid JSON" }                              // 400: ボディ不正
{ "error": "Unauthorized" }                              // 401: 認証失敗
```

---

## C-3 混雑レベル算出アルゴリズム

### 概要

Rolling Window（直近 30 件）とベースライン値を組み合わせたハイブリッド算出方式。

### 計算式

```
ratio = deviceCount / baseline × 100

ratio ≤ 15%  → status 1（空）
ratio ≤ 35%  → status 2（少ない）
ratio ≤ 55%  → status 3（普通）
ratio ≤ 75%  → status 4（多い）
ratio > 75%  → status 5（満員）
```

### ベースライン決定ロジック

| 条件 | ベースライン |
|---|---|
| `booths/{boothId}.baselineMax` が設定されている | `baselineMax` の値を使用 |
| 未設定 | Rolling Window（直近 30 件）の最大値を使用 |
| Rolling Window も空 | デフォルト値 `20` を使用 |

### baselineMax の設定方法

朝の事前テストで満員時のデバイス数を計測し、Firestore に登録します。

```
Firestore > booths > {boothId} > baselineMax: <満員時デバイス数>
```

または `/db/booth` の編集画面から設定可能です。

---

## フェイルオーバー仕様

### 自動フェイルオーバー

Bluetooth データが **3 分間**途絶えると自動的に手動モードへ切り替わります。

```
lastBluetoothAt から 3 分経過
  └── isManual: true
  └── isManualByFailover: true
  └── FCM 通知送信:「混雑情報 手動モードに切替」
```

その後 **5 分ごと**に担当者にリマインダー通知を送信します。

### 自動復旧

次に Bluetooth データを受信した時点で自動的に自動モードへ復帰します。

```
POST /api/booth/bluetooth 受信
  └── isManualByFailover === true の場合
       └── isManual: false
       └── isManualByFailover: false
       └── FCM 通知送信:「Bluetooth 復旧」
```

### 手動モードとフェイルオーバーの違い

| 状態 | `isManual` | `isManualByFailover` | Bluetooth データの扱い |
|---|---|---|---|
| 自動モード | `false` | `false` | 受信して算出 |
| フェイルオーバー（自動切替） | `true` | `true` | 受信時に自動復旧 |
| 手動モード（人が設定） | `true` | `false` | 受信してもスキップ |

---

## Surface Go 2 側の設定

### 必要な設定値

| 設定項目 | 値 |
|---|---|
| API URL | `https://inuso-admin.vercel.app/api/booth/bluetooth` |
| Bearer トークン | 各ブースの per-booth トークン（`booth_tokens.json` の `map[boothId]`）。サーバーの `BLUETOOTH_SECRET` に同じ JSON を設定 |
| ブース ID | Firestore の `booths` コレクションのドキュメント ID（下記一覧・要確認） |

### 送信間隔の推奨値

- **推奨**: 30 秒〜1 分間隔
- **最大**: 2 分 30 秒以内（フェイルオーバー閾値 3 分の安全マージン）

### 動作テスト（curl）

```bash
curl -X POST https://inuso-admin.vercel.app/api/booth/bluetooth \
  -H "Authorization: Bearer <そのブースのトークン>" \
  -H "Content-Type: application/json" \
  -d '{"boothId":"class1-1","deviceCount":10,"operatorId":"bt-class1-1"}'
```

期待レスポンス: `{"ok":true,"status":3}`

---

## boothId 一覧（Firestore ドキュメントID）

送信する `boothId` は Firestore `booths` のドキュメントIDと**完全一致**が必要（不一致は 400 `booth not found`）。
per-booth トークン方式では、`booth_tokens.json` のキーもこの boothId に揃える必要があります。

| 区分 | boothId |
|---|---|
| クラス（12） | `class1-1`〜`class1-4` / `class2-1`〜`class2-4` / `class3-1`〜`class3-4` |
| 部活 | `club-art`（美術部） / `club-game`（eスポーツ部）※下記要確認 |
| 委員会・有志 | `health`（保健委員会） / `pe-gym`（有志発表） |
| 飲食 | `eat-car-1` / `eat-car-2` / `eat-car-3` / `pta-bazaar` |

### 要確認（Bluetooth 開発側との突き合わせ）

- **eスポーツ部の boothId**: サイト側コードは `club-game` を Firestore ドキュメントIDとして扱う箇所があります。一方 Bluetooth 側の `booth_tokens.json` は `club-esports` をキーにしています。**実際の Firestore ドキュメントIDに合わせて、トークンマップのキーと送信 `boothId` を統一**してください（不一致だと per-booth トークン照合に失敗して 401、または 400 `booth not found`）。
- 飲食IDは旧 `eat-1`〜`eat-4` から `eat-car-1/2/3`・`pta-bazaar` へ移行済み（サイト側コードは対応済み。Firestore ドキュメントIDの実移行が前提）。
- `macAddresses` は現状サイト側で未使用（送信自体は問題なし）。

---

## Firestore のブースフィールド（Bluetooth 関連）

| フィールド | 型 | 説明 |
|---|---|---|
| `status` | number | 混雑レベル 1〜5 |
| `deviceCount` | number | 最後に受信したデバイス数 |
| `isManual` | boolean | 手動モードフラグ |
| `isManualByFailover` | boolean | フェイルオーバーによる手動切替フラグ |
| `failoverAt` | Timestamp \| null | フェイルオーバー発生時刻 |
| `lastBluetoothAt` | Timestamp \| null | 最終 Bluetooth 受信時刻 |
| `lastManualReminderAt` | Timestamp \| null | 最終リマインダー送信時刻 |
| `baselineMax` | number \| null | 満員時デバイス数（C-3 算出用） |
| `scope` | string | FCM 通知ルーティング用（担当者 ID） |

---

## 当日の運用フロー

### 開場前

1. Surface Go 2 を起動し、Bluetooth スキャンスクリプトを開始
2. `POST /api/booth/bluetooth` が正常に動作するか curl でテスト
3. 各ブースの `baselineMax` を設定（空のブースと満員のブースでテストして計測）
4. `/admin/booth` で各ブースが `自動` モードになっているか確認

### 開場中

- 担当者は `/admin/booth` または `/admin/mybooth` で混雑状況を監視
- フェイルオーバー通知（FCM）が届いたら手動でブースを更新
- Bluetooth が復旧したら通知が届き、自動モードに戻る

### 閉場後

- Surface Go 2 のスクリプトを停止
- 全ブースを `status: 0`（未設定）または `status: 1`（空）にリセット

---

## トラブルシューティング

Bluetooth 関連の問題は [`docs/troubleshooting.md`](./troubleshooting.md) の「Bluetooth データが受信されない」セクションを参照してください。

---

作成者：claude & sho29saka31
