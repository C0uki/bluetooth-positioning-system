# Claude Code スキル リファレンス（コーディング向け）
> 調査日: 2026-06-24  
> 対象: Claude Code / Codex / Cursor / Gemini CLI など Agent Skills 標準対応ツール
---
## 仕組み
スキルは `SKILL.md` ファイルを置くだけで動く拡張モジュール。
- セッション開始時に Claude がスキル一覧をスキャン（1スキルあたり約 100 トークン）
- タスクに関係するスキルだけフル読み込み（5,000 トークン以内）
- `/skill-name` で手動呼び出し、または Claude が自動判断で呼び出す
- Pro / Max / Team / Enterprise プランで利用可能（Free は不可）
```
~/.claude/skills/          # 個人用（全プロジェクトで有効）
.claude/skills/            # プロジェクト用（そのリポジトリ内だけ有効）
```
---
## 公式スキル（anthropics/skills）
まず最初に確認するリポジトリ。  
GitHub: https://github.com/anthropics/skills
### コーディング関連
| スキル名 | 用途 | 自動呼び出しトリガー |
|---|---|---|
| `frontend-design` | AIスロップ脱却。コード前に目的/トーン/制約/差別化を考えさせる | フロントエンドUI生成時 |
| `webapp-testing` | Playwright を使った E2E テスト自動化 | テスト作成時 |
| `mcp-builder` | MCPサーバーを Python/TypeScript で構築するガイド | MCP関連作業時 |
| `claude-api` | Python/TS/Go/Ruby 等向け Claude API リファレンス | `import anthropic` 記述時 |
| `skill-creator` | スキル自体を作るメタスキル | スキル作成依頼時 |
### インストール（公式）
```cmd
REM マーケットプレイス経由
/plugin marketplace add anthropics/skills
/plugin install frontend-design@anthropics/skills
/plugin install webapp-testing@anthropics/skills
REM git clone → 手動コピー（Windows）
git clone https://github.com/anthropics/skills.git
xcopy /E /I skills\skills\frontend-design %USERPROFILE%\.claude\skills\frontend-design
xcopy /E /I skills\skills\webapp-testing %USERPROFILE%\.claude\skills\webapp-testing
```
---
## コミュニティ注目スキル（コーディング向け）
### 1. Karpathy Skills ★144k
`multica-ai/andrej-karpathy-skills`  
https://github.com/multica-ai/andrej-karpathy-skills
Andrej Karpathy が指摘した AI コーディングエージェントの失敗パターンを 4 つのルールで封じる。
封じるパターン:
- 確認せず黙って暴走する
- 50行で済む処理を500行に過剰設計する
- 関係ないコードまで触る
```cmd
npx @swarmclawai/andrej-karpathy-skills --agent claude --dest .
```
---
### 2. Caveman ★68k
トークン削減特化スキル。
- 出力トークンを平均 65% 削減（範囲 22〜87%）
- `/caveman-compress` で CLAUDE.md 自体も約 46% 圧縮
- `/caveman-commit` — 50文字以内のコンベンショナルコミットメッセージ生成
- `/caveman-review` — 1行 PR レビュー: `L42: bug: user null. Add guard.`
Claude Code / Codex / Gemini CLI / Cursor / Windsurf 対応。
---
### 3. UI/UX Pro Max ★88.7k
`nextlevelbuilder/ui-ux-pro-max-skill`
デザインシステムの自動生成スキル。
- 50以上の UI スタイル（Glassmorphism / Brutalism / Neumorphism 等）
- 161 カラーパレット
- 57 フォントコンビネーション（Google Fonts import 付き）
- 対応スタック: React / Next.js / Vue / Nuxt / Svelte / Flutter / SwiftUI / React Native / Jetpack Compose
```
/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill
```
---
### 4. Taste Skill ★37.4k
`Leonxlnx/taste-skill`
3パラメータでデザイン出力を調整する「イコライザー型」スキル。
- `DESIGN_VARIANCE` 1〜10: 1=中央寄りレイアウト、10=非対称モダン
- `MOTION_INTENSITY` 1〜10: 1=シンプルホバー、10=スクロールトリガー
- `COLOR_TEMPERATURE`: ウォーム〜クール
11種の専門バリアント + 3種の画像生成スキル付き。
---
### 5. Engineering Skills（alirezarezvani/claude-skills）
https://github.com/alirezarezvani/claude-skills
345スキル・17ドメインの大型コレクション。コーディング向けは `engineering/` 配下。
主なスキル:
- `senior-fullstack` — フルスタックシニアエンジニアのペルソナ
- `senior-frontend` — フロントエンド専門
- `senior-backend` — バックエンド専門
- `security-auditor` — セキュリティスキャン（PASS/WARN/FAIL 判定）
- `playwright-pro` — Playwright テストツールキット
- `handoff` — セッション引き継ぎサマリ生成
```cmd
/plugin marketplace add alirezarezvani/claude-skills
/plugin install engineering-skills@claude-skills
/plugin install engineering-advanced-skills@claude-skills
```
---
## スキル探索リポジトリ一覧
| リポジトリ | 特徴 |
|---|---|
| `anthropics/skills` | 公式。まずここ |
| `travisvn/awesome-claude-skills` | カテゴリ別キュレーションリスト（起点に最適） |
| `ComposioHQ/awesome-claude-skills` | 1000+スキル。外部アプリ（Gmail/Slack等）連携重視 |
| `GetBindu/awesome-claude-code-and-skills` | セキュリティ・エージェント系に強い |
| `alirezarezvani/claude-skills` | 345スキル・17ドメイン。最大規模のコレクション |
| `github.com/topics/claude-code-skills` | GitHubトピック。最新スキルをリアルタイムで探せる |
---
## インストール方法 3択
```cmd
REM 1. マーケットプレイス（一番楽）
/plugin marketplace add {owner}/{repo}
/plugin install {skill-name}@{repo}
REM 2. git clone → 手動コピー（一部だけ欲しいとき）
git clone https://github.com/{owner}/{repo}.git C:\tmp\skills
xcopy /E /I C:\tmp\skills\skills\{skill-name} %USERPROFILE%\.claude\skills\{skill-name}
REM 3. 一時試用（--add-dir フラグ）
claude --add-dir C:\tmp\skills
```
---
## スキル自作テンプレート
```markdown
---
name: my-skill
description: このスキルが使われる条件を具体的に書く（Claude がトリガー判断に使う）
disable-model-invocation: false
---
# My Skill
## 手順
1. ステップ1
2. ステップ2
## 注意事項
- ...
```
ベストプラクティス:
- `SKILL.md` 本体は 500行 / 1500〜2000ワード 以内に抑える
- 詳細情報は `references/` に分離する
- 副作用のある操作（デプロイ・送信等）は `disable-model-invocation: true` を付ける
- スクリプトは `scripts/` に、テンプレート素材は `assets/` に分離する
---
## 動的コンテキスト注入（上級）
`!` プレフィックスでシェルコマンドの出力をスキル内に埋め込める:
```markdown
---
name: pr-summary
description: PR の変更内容を要約する
context: fork
---
## PR diff
!`gh pr diff`
## コメント
!`gh pr view --comments`
上記の内容を 3 点で要約し、リスクを指摘してください。
```
---
*参考: `anthropics/skills`, `travisvn/awesome-claude-skills`, `code.claude.com/docs/ja/skills`*
