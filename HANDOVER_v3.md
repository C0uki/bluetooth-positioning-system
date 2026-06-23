# ISF webapp / Bluetooth混雑検知システム — 引き継ぎサマリー v3
> 新しいチャットの最初にこのファイルを貼り付けることで、続きから会話できます。

最終更新: 2026年6月22日

---

## プロジェクト概要
- **アプリ名**: ISF webapp（旧称: inusoポケット）
- **制作名**: ISFプロジェクト
- **学校**: 犬山総合高等学校
- **文化祭本番**: 2026年9月7日
- **公開期間**: 2026年8月31日〜9月8日
- **企画書バージョン**: v5（README-v5 / process.me 準拠）

## 開発体制
| 担当 | 範囲 |
|---|---|
| Couki（自分） | Bluetooth実装（Surface側スキャン・送信） |
| Shoki（友人） | Web アプリ全体（閲覧用・管理用Vercel、API Route、混雑レベル算出ロジック） |

**ツールの役割分担**
- claude.ai: 設計相談・企画書/サマリー作成・意思決定
- Claude Code（開発用PCにインストール済み）: Pythonコード作成・デバッグ・Git操作

---

## 現在地（進捗状況）

### ✅ 完了したこと
- システム全体設計（企画書v5・process.meロードマップで確定済み）
- GitHubリポジトリ作成・push済み
  - `bluetooth-positioning-system`（Public）— コード完成・push済み
  - `bluetooth-positioning-system-data`（Private）— 作成済み・トークン保存済み
- **Bluetooth Pythonプログラム v5対応版を実装・動作確認済み**
  - スキャン → RSSIログ記録 → 重複排除 → API送信、の全フロー動作確認済み（2026/6/22）
  - API送信成功確認済み（200 OK、混雑レベルがレスポンスで返る）
- APIトークン生成・Shoki側Vercel環境変数に設定済み
- API_ENDPOINT確定・設定済み
- `gh` CLIインストール・認証済み
- 配布用パッケージ一括生成スクリプト（`tools/generate_configs.py`）作成済み
- 起動用バッチファイル（`start.bat`, `install.bat`）作成済み
- 先生へのソフトウェアインストール申請書（Word）を作成済み

### 🔲 進行中・ブロッカー
- 学校のSurface Go 2で **PowerShellがシステム管理者にブロックされている**
  → Python/Git/Claude Codeのインストール申請が必要
  → PowerShell自体のブロック解除も合わせて申請予定

### 🔲 未実施タスク
- Surface Go 2での実機テスト（インストール許可待ち）
- RSSIフィルタリングの検証・採否判断（8月上旬まで）
- 会場掲示の文面確定（優先度低）
- 校舎フロアマップSVG作成（学校の平面図データ待ち。claude.aiで作業予定）

---

## ファイル構成

```
bluetooth-positioning-system/（Public）
├── main.py                  # エントリーポイント（起動→トークン入力GUI→スキャンループ→終了時USB回収）
├── start.bat                # ダブルクリックで起動
├── install.bat              # 依存パッケージインストール用
├── requirements.txt         # bleak>=3.0.0, requests==2.32.3
├── config/
│   └── settings.py          # 教室固有設定＋共通設定
├── scanner/
│   └── bluetooth_scanner.py # BLEスキャン＋RSSIフィルタリング
├── processor/
│   ├── mac_deduplicator.py  # MACアドレス重複排除
│   └── congestion_calculator.py  # 【ローカル確認専用】参考実装
├── uploader/
│   └── api_uploader.py      # Vercel API へPOST送信
├── logger/
│   └── rssi_logger.py       # RSSI値をCSVでローカル記録
└── tools/
    └── generate_configs.py  # 12教室分の配布パッケージ一括生成

bluetooth-positioning-system-data/（Private）
├── credentials/
│   └── api_token.txt        # APIトークン
└── .gitignore               # credentials/, logs/ を除外
```

---

## 確定している設計決定

### API接続情報
```
API_ENDPOINT = "https://inuso-admin.vercel.app/api/booth/bluetooth"
BLUETOOTH_SECRET = "73de08f1d9a92b9a74c43a96bc4af81e940d8e5c07e474792094635da21496c6"
認証方式: Authorization: Bearer <token>
```

### 動作フロー（確認済み）
```
Surface端末が main.py を実行
  → 起動時にBLUETOOTH_SECRETが空ならGUIダイアログでトークン入力
  → Bluetoothスキャン（60秒間隔）→ deviceCount をカウント
  → RSSIログをCSVに記録（将来の位置推定用）
  → POST /api/booth/bluetooth にBearer認証で送信
  → admin API が混雑レベル（1〜5）を算出してFirestoreを更新
  → viewer側のISRキャッシュを無効化 → 混雑状況がリアルタイム反映
  → END_TIME 経過後、ログをUSBにコピーしてローカル削除
```

### データ送信形式（Surface → Vercel API）
```json
POST /api/booth/bluetooth
{
  "boothId": "class-1-1",
  "deviceCount": 8,
  "macAddresses": ["AA:BB:CC:DD:EE:01", "..."],
  "operatorId": "bt-class-1-1"
}
```

### config/settings.py 全フィールド
```python
# ===== 教室固有設定（教室ごとに異なる） =====
BOOTH_ID     = "class-1-1"
OPERATOR_ID  = f"bt-{BOOTH_ID}"
END_TIME     = "16:00"

# ===== Bluetoothスキャン設定 =====
SCAN_INTERVAL_SECONDS = 60        # スキャン間隔（秒）
SCAN_DURATION_SECONDS = 10        # 1回のスキャン時間（秒）
RSSI_THRESHOLD    = None          # 朝テストで実測（Noneならフィルタ無効）

# ===== API設定 =====
API_ENDPOINT      = "https://inuso-admin.vercel.app/api/booth/bluetooth"
BLUETOOTH_SECRET  = ""            # 起動時にGUIで入力 or 配布パッケージで埋め込み
API_TIMEOUT_SECONDS = 10

# ===== ログ設定 =====
LOG_DIR      = "logs"             # ローカルログ保存先
```

### 混雑レベル定義（企画書v5 §8.2）
```
0 = 停止中（手動設定のみ）
1 = 非常に閑散
2 = 閑散
3 = 通常
4 = 混雑
5 = 非常に混雑
```

### 混雑レベル判定アルゴリズム（C-3ハイブリッド型）
```
初期: 朝テストのbaselineMaxに対する割合で判定
切り替え: 「企画ごとの事前設定時刻」または「過去10分のstddevが閾値以下」のどちらか早い方
切り替え後: 過去30分のローリングウィンドウで動的判定
```
※ この計算ロジックはAPI Route側（Shoki実装）で動く。Pythonはセンサーとしての役割のみ。

### Bluetooth方式
- デバイス数カウント（MACアドレス一元管理）
- Surface配置: 各教室1台固定（計19台、予備11台、合計30台利用可能）
- 1教室=1企画（複数企画が同教室に入ることはない）
- スキャン間隔: 60秒
- フェイルオーバー型（Bluetooth失敗→手動更新に自動切替）

### 技術スタック
- フロントエンド: Next.js (App Router) + TypeScript
- ホスティング: Vercel × 2（閲覧用・管理用、別プロジェクト）
- DB: Firebase Firestore（単一）
- 通知: Firebase Cloud Messaging
- 認証: Cookie自己申告制（Firebase Authは不使用）

### GitHubリポジトリ構成
```
Couki:
  - bluetooth-positioning-system（Public）— 実装完了・push済み
  - bluetooth-positioning-system-data（Private）— 作成済み・トークン保存済み
Shoki:
  - ISF-viewer（閲覧用）
  - ISF-admin（管理用）
```

---

## 本番Surfaceへの配布フロー

1. Couki操作の1台でPublic/Privateリポジトリをclone
2. `python tools/generate_configs.py --token-file ../bluetooth-positioning-system-data/credentials/api_token.txt` で12教室分のパッケージを `dist/` に生成
3. USBメモリで19教室＋予備Surfaceにローカルコピー
4. 各Surfaceで `install.bat`（初回のみ）→ `start.bat` で起動

### 配布パッケージの構成（dist/class-1-1/ の例）
```
class-1-1/
  main.py, start.bat, install.bat, requirements.txt
  config/settings.py（BOOTH_ID="class-1-1", BLUETOOTH_SECRET=トークン埋め込み済み）
  scanner/, processor/, uploader/, logger/
```

---

## 当日の起動・表示・終了UX

- **起動**: `start.bat` をダブルクリック。BLUETOOTH_SECRETが設定に埋め込まれていない場合はGUIダイアログでトークン入力
- **表示**: 「✅ 正常に動作中です」/「⚠️ 直前の送信に失敗しました」+ 最終送信時刻を表示
- **終了**: END_TIME 経過後「終了時刻になりました。このウィンドウを閉じてください」に切り替え。USBへログコピー後にローカル削除
- **エラー時**: 例外を握り込んで次の60秒サイクルへ進む（担当者に操作を求めない）

---

## RSSIとMACアドレスに関する方針

### MACアドレスランダム化リスク
- iOS/Android端末のBluetooth MACアドレスランダム化によりデバイス数カウントの精度に影響する可能性あり
- RSSI（信号強度）フィルタリングで対応を試みる（実装済み、閾値は朝テストで決定）
- **採用/見送りの最終判断期限: 2026年8月上旬**

### RSSI記録方針（将来の位置推定用）
- CSVログに **ハッシュ化MAC（擬似ID）** + RSSI値 を記録（`logger/rssi_logger.py`）
  - 生MACは保存・送信しない。`MAC_HASH_SALT` 付きSHA-256で擬似ID化（`scanner/bluetooth_scanner.py: hash_mac`）
  - 同一端末は常に同じ擬似IDになるため、重複排除・将来の位置推定（擬似ID＋RSSIパターン）は維持される
- 形式: `timestamp, booth_id, mac_hash, rssi, passed_filter`
- 文化祭終了後、19台分のローカルログをUSBで回収しPrivateリポジトリに保管

### MACアドレスデータの保持・開示方針
- 保持期間: 当面保持（秋以降の位置推定システム開発用の学習データ）
  - 保存・送信するのは生MACではなくソルト付きハッシュの擬似IDのみ（個人端末の生識別子は保持しない）
- 会場内に「Bluetoothによる混雑計測を実施しています」の掲示を出す（受付に1箇所）

---

## コード上の注意点（次のClaude Codeへ）

### デバッグ用コードが残っている（要クリーンアップ）
1. `main.py:51` — `input("Enterキーで続行...")` はデバッグ用。本番前に削除すること
2. `main.py:125` — トークン設定時の先頭4文字・長さ表示はデバッグ用。本番前に削除すること
3. `uploader/api_uploader.py` — 送信失敗時のレスポンス詳細表示はデバッグ用。本番前に削除するか検討

### tkinterはbleakと競合する
- トークン入力GUIにtkinterを使うとbleakのBluetooth通信が壊れる（`Thread is configured for Windows GUI but callbacks are not working`）
- 現在はPowerShellの `Microsoft.VisualBasic.Interaction.InputBox` を subprocess で呼び出すことで回避済み

### BLUETOOTH_SECRETの動的設定
- `config/settings.py` の `BLUETOOTH_SECRET` はPublicリポジトリでは空文字
- 起動時にGUIで入力した値を `settings.BLUETOOTH_SECRET` に代入する仕組み
- `uploader/api_uploader.py` は `import config.settings as settings` で参照しているため、動的変更が反映される（直接importすると反映されないバグがあった）

---

## 予備Surface（11台）の運用方針
- 当日中の積極的な交換プロトコルは作らない
- Bluetooth不調時は既存のフェイルオーバー（→手動更新モード）に任せる
- 予備機は「設置日までの故障対応・最終手段」としてのみ位置づける

---

## 次にやること（優先順、2026/6/22更新）

1. **デバッグ用コードのクリーンアップ**（上記3箇所）
2. **PR #2をマージ**（未マージのコミットが複数ある）
3. 先生からのソフトウェアインストール許可を待つ（Surface Go 2用）
4. 許可が出たらSurface Go 2での実機テスト
5. （8月上旬まで）RSSIフィルタリングの検証・採否判断
6. 校舎フロアマップSVG作成（学校の平面図データ待ち、claude.aiで作業）
7. 会場掲示の文面確定（優先度低）
8. 文化祭終了後、19台分のローカルログをUSBで回収

---

## このサマリーの使い方
新しいチャットの最初に「これが今までの進捗です」とこのファイルを貼り付けてください。
Claudeはこの内容を前提に、続きから会話を進められます。
