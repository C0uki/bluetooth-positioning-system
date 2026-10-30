# Bluetooth 混雑計測システム連携仕様（Surface 側）

Surface Go 2 のスキャナ（本リポジトリ）が BPS-admin に検知数を送る部分の仕様です。
混雑レベルの算出（C-3 アルゴリズム）・フェイルオーバー・Firestore の項目・当日の運用フローは**サーバー側の仕様**なので、
重複を避けるため BPS-admin 側のドキュメントを正とします。

> サーバー側の詳細: [`bps-site-admin/docs/bluetooth.md`](https://github.com/sho29saka31/bps-site-admin/blob/main/docs/bluetooth.md)
> （C-3 算出・ベースライン・フェイルオーバー/自動復旧・Firestore のブースフィールド・運用フロー）

---

## システム概要

```
Surface Go 2
  └── bluetooth-positioning-system (Python)
       └── Bluetooth LE スキャン → 擬似ID化 → 重複排除
            └── POST /v1/ingest（Bearer 認証）  → データ配信 Worker（bps-site-data）
                 └── 貯めて、1分ごとに一括で BPS-admin へ（INGEST_SECRET）
                      └── C-3 算出 → Firestore 更新 → BPS-viewer のキャッシュ無効化（手動更新時など）
```

---

## 送信先の設定

| 設定項目 | 値 | 設定場所 |
|---|---|---|
| API URL | `https://data.bps.saka2931.jp/v1/ingest` | `config/settings.py` の `API_ENDPOINT`（`tools/generate_configs.py` が配布パッケージに書き出す） |
| Bearer トークン | 各ブースの per-booth トークン（`booth_tokens.json` の `map[boothId]`） | `BLUETOOTH_SECRET`（配布パッケージに埋め込み） |
| ブース ID | Firestore の `booths` コレクションのドキュメント ID | `BOOTH_ID` |

トークンは**ブースごとに異なる**方式です。`booth_tokens.json`（`{boothId: token}`）と**同じ内容**を、
データ配信 Worker（受信側）の `BLUETOOTH_SECRET`（admin の旧直接受信用の `BLUETOOTH_SECRET` と同じ形式）に設定してください。
`tools/generate_booth_tokens.py` で生成し、`tools/generate_configs.py` で教室別の配布パッケージを作ります。

---

## `POST /v1/ingest`

**認証:** `Authorization: Bearer <そのブースのトークン>`

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
| `deviceCount` | number | ✅ | 検出したデバイス数（**JSON 数値型**。有限の非負数であること） |
| `operatorId` | string | — | 変更ログに記録する送信元識別子。省略時は `bt-<boothId>` |
| `macAddresses` | string[] | — | 擬似ID（ソルト付きハッシュ）。サーバー側は `deviceCount` のみ参照し、未使用 |

> `uploader/api_uploader.py` は、このほかに `devices`（`{mac_hash, rssi}` の配列）も付けて送ります。サーバー側は参照しません。
> 生の MAC アドレスは送信しません。

**レスポンス:**

| 状況 | ステータス | ボディ |
|---|---|---|
| 受理（Worker が貯めた） | 200 | `{ "ok": true, "queued": true }` |
| 必須項目の欠落・値が不正 | 400 | `{ "error": "boothId and deviceCount required" }` など |
| 不正な JSON | 400 | `{ "error": "invalid JSON" }` |
| 認証失敗（未設定・不一致・boothId 未登録） | 401 | `{ "error": "Unauthorized" }` |
| ボディが大きすぎる（16 KB 超） | 413 | `{ "error": "payload too large" }` |

> 受理は「Worker が貯めた」ことを表します。混雑レベルへの反映は、Worker が1分ごとに admin へ一括送信したあとです（最大約1分遅れ）。
> ブース未登録・手動モードのスキップは、この時点では分かりません（admin 側で処理され、スキップされます）。
> `macAddresses` と `devices` は Worker が保存も転送もしません（台数だけを使います）。

---

## 送信間隔

- **推奨**: 30 秒〜1 分間隔（現行は 60 秒）
- **最大**: 2 分 30 秒以内。サーバー側は 3 分間データが途絶えると自動で手動モードへ切り替えます（フェイルオーバー）。
  次にデータが届くと自動で復帰します。

---

## 動作テスト（curl）

```bash
curl -X POST https://data.bps.saka2931.jp/v1/ingest \
  -H "Authorization: Bearer <そのブースのトークン>" \
  -H "Content-Type: application/json" \
  -d '{"boothId":"class1-1","deviceCount":10,"operatorId":"bt-class1-1"}'
```

期待レスポンス: `{"ok":true,"status":3}`

---

## boothId 一覧

送信する `boothId` は Firestore `booths` のドキュメント ID と**完全一致**が必要です（不一致は 400 `booth not found`）。
`booth_tokens.json` のキーも同じ boothId に揃えてください（不一致は 401）。

```
class1-1, class1-2, class1-3, class1-4,
class2-1, class2-2, class2-3, class2-4,
class3-1, class3-2, class3-3, class3-4,
club-esports, club-art,
health, pe-gym,
eat-car-1, eat-car-2, eat-car-3,
pta-bazaar
```

> eスポーツ部の ID は、BPS-admin 側のドキュメントでは `club-game` と書かれている箇所があります。
> 実際の Firestore ドキュメント ID に合わせて、トークンマップのキーと送信 `boothId` を統一してください。

---

## トラブルシューティング

Bluetooth 関連の問題は [`docs/troubleshooting.md`](./troubleshooting.md) を参照してください。
