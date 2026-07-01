# トラブルシューティング

Bluetooth 混雑検知システムの動作不良時の切り分け手順をまとめます。

---

## Bluetooth データが受信されない

「サイト側（`/admin/booth` や Viewer の混雑表示）にデータが反映されない」場合、
以下の順に切り分けます。

### 1. Surface側でスキャン・送信が実行されているか確認

```bash
python main.py
```

コンソールに `API送信成功: <boothId> (<N>台)` が出力されているか確認してください。
出力されない、またはエラーが出る場合は Bluetooth アダプタが無効になっていないか、
`config/settings.py` の `BOOTH_ID` / `BLUETOOTH_SECRET` / `API_ENDPOINT` が正しいか確認します。

### 2. API送信のレスポンスを確認する

`api_uploader.py` は失敗時に `API送信失敗: <エラー内容>` をコンソールに出力し、
`logs/scan_<日付>.json` にペイロードをローカル保存します（後で再送可能）。

代表的なエラーと原因:

| レスポンス | 原因 |
|---|---|
| `401 Unauthorized` | `BLUETOOTH_SECRET` が boothId に対応するトークンと一致しない（per-boothトークンのキー不一致・入力ミス） |
| `400 booth not found` | 送信している `boothId` が Firestore `booths` コレクションのドキュメントIDと一致しない |
| `400 boothId and deviceCount required` | ペイロード不正（`deviceCount` が数値型でない等） |
| タイムアウト / 接続エラー | Surface のネットワーク疎通不良、または `API_ENDPOINT` の URL 誤り |

詳細な API 仕様は [`docs/webapp-bluetooth-api-spec.md`](./webapp-bluetooth-api-spec.md) を参照してください。

### 3. curl で疎通テストする

Surfaceの実装を経由せず、API単体で疎通確認する場合:

```bash
curl -X POST https://inuso-admin.vercel.app/api/booth/bluetooth \
  -H "Authorization: Bearer <そのブースのトークン>" \
  -H "Content-Type: application/json" \
  -d '{"boothId":"class1-1","deviceCount":10,"operatorId":"bt-class1-1"}'
```

期待レスポンス: `{"ok":true,"status":3}`

### 4. `/admin/booth` の手動モードを確認する

送信自体は成功していても（`{"ok":true,"skipped":true,"reason":"manual mode"}`）、
担当者が手動でブースを「手動モード」に切り替えている場合は Bluetooth 側の値が反映されません。
`/admin/booth` または `/admin/mybooth` で自動モードになっているか確認してください。

### 5. フェイルオーバーの通知を確認する

Bluetooth データが3分間途絶えると自動的に手動モードへ切り替わります（フェイルオーバー）。
担当者にFCM通知（「混雑情報 手動モードに切替」）が届いていないか確認してください。
次にBluetoothデータを受信した時点で自動的に自動モードへ復帰します。

---

## RTDB（rssi_logs）にデータが記録されない

`uploader/rtdb_uploader.py` はRTDB送信の失敗を握りつぶさず、以下のログを出力します。

| ログ | 原因 |
|---|---|
| `[RTDB] URL未設定のためスキップ` | `config/settings.py` の `FIREBASE_DATABASE_URL` が空 |
| `[RTDB] SAキーが見つかりません` | `credentials/firebase_key.json` が配置されていない |
| `[RTDB] 初期化失敗: <エラー>` | SAキーの内容不正、またはRTDB URLがプロジェクトと不一致 |
| `[RTDB] 送信失敗、キューに追加: <エラー>` | 一時的なネットワーク不良（次回送信時に再試行） |

`FIREBASE_DATABASE_URL` は `https://isf-webapp-default-rtdb.asia-southeast1.firebasedatabase.app`
であることを確認してください（別プロジェクトのURLを指定すると401 Unauthorizedになります）。

疎通確認には `tools/rtdb_test.py` を使用します。

```bash
python tools/rtdb_test.py
```

---

## boothId 不一致によるエラー

`booth_tokens.json` のキー、Surface側の `config/settings.py` の `BOOTH_ID`、
Firestore `booths` コレクションのドキュメントIDの3箇所は完全一致している必要があります。

不一致がある場合、`docs/webapp-bluetooth-api-spec.md` の「boothId 一覧」セクションを参照し、
サイト側（Shoki）と実際の Firestore ドキュメントIDを突き合わせてください。
