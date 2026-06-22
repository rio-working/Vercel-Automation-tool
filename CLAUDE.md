# Workspace — Claude Code 作業手順書

このファイルはClaude Codeがこのディレクトリで作業する際に自動で読み込まれる。

---

## 前提

- `.env` に `GAS_WEB_APP_URL`, `GEMINI_API_KEY`, `API_SECRET_TOKEN`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `SPREADSHEET_ID` が設定済み
- Vercel 自動デプロイ: `main` ブランチへのプッシュで即反映
- GAS は `workspace/gas` にあり、`clasp push` で更新

---

## システムアーキテクチャ

### 通信フロー

```
フロントエンド（Vercel）
├→ /api/sheets/* → gspread で直接読み書き
├→ /api/journal  → シート保存 → GAS → Drive 保存
├→ /api/ai/*     → Gemini API
└→ gasApi()      → GAS Web App URL（Calendar / Tasks）
```

### GAS の受け付けアクション

- `getAgenda` — Google Calendar イベント取得
- `getCalendarLists` — カレンダー一覧取得
- `getTasks` — Google Tasks リスト取得
- `completeTask` — タスク完了マーク
- `getTaskLists` — タスク一覧リスト取得
- `saveToDrive` — Markdown を Drive に保存

---

## 実装時のチェックリスト

- [ ] 環境変数（`.env`）に必要な値が全て設定されているか確認
- [ ] GAS Web App URL が有効か（`?action=ping` で確認）
- [ ] Vercel デプロイ後、フロントエンドで動作確認
- [ ] スプレッドシート ID が正確か
- [ ] Drive フォルダ ID がスプレッドシート設定に記載されているか

---

## デバッグ

### Vercel ログ確認
```bash
vercel logs workspace --tail
```

### GAS ログ確認
```bash
# GAS Editorで実行ログを確認
# または Google Apps Script Dashboard でエラー確認
```

### API疎通確認
```bash
curl "GAS_WEB_APP_URL?action=ping"
```

---

## よくある修正パターン

### シート操作の追加
1. `main.py` に `routers/{name}.py` を追加
2. `core/sheets.py` でカラムマッピング定義
3. Vercel にプッシュ（自動デプロイ）

### Google Calendar / Tasks の新しい操作を追加
1. `workspace/gas/{Service}.gs` に関数追加
2. `Code.gs` の case に新アクション追加
3. `clasp push` で更新
4. `.env` の `GAS_WEB_APP_URL` で呼び出し

### 環境変数の追加
1. `.env` に新しい変数を追加
2. `main.py` で読み込み: `os.getenv("新変数")`
3. Vercel Project Settings でも同じ変数を設定

## ナレッジ参照
- GAS API ガイド: `~/.claude/commands/gas_api_guide.md`
- GAS デプロイ手順: `~/.claude/commands/gas-deploy-workflow.md`
- Vercel × FastAPI アプリ作成: `~/.claude/commands/new-vercel-app.md`

