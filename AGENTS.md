# Workspace 作業ルール

> Codex はこのリポジトリの `.git` でルールの読み込みが止まるため、`~/cursor-rimonyan` 内で作業するときは作業前にルートの `AGENTS.md`（`~/cursor-rimonyan/AGENTS.md`）も読む。Claude Code は自動で読む。

> 作業前に、このフォルダの `_MOC.md` で関連ファイルを確認する。

## 構成

- Vercel: UI、スプレッドシートCRUD、AI処理。
- GAS: Google Calendar / Tasks / Driveの認証付き操作。
- `main` へのpushはVercel本番デプロイにつながる。
- GASコードは `workspace/gas/` を正本とする。

## 通信

```text
frontend
  -> /api/sheets/* : gspread
  -> /api/journal  : sheet -> GAS -> Drive
  -> /api/ai/*     : Gemini API
  -> GAS Web App   : Calendar / Tasks / Drive
```

GASの既存アクション:

- `getAgenda`
- `getCalendarLists`
- `getTasks`
- `completeTask`
- `getTaskLists`
- `saveToDrive`

## 実装規則

- シート操作は既存routerと `core/sheets.py` のカラム定義に合わせる。
- Calendar / Tasks / Drive操作はGAS側へ追加し、Vercel側へ認証情報を持ち込まない。
- 環境変数名を追加した場合は、ローカル設定とVercel設定の両方を確認する。
- APIキー、サービスアカウントJSON、トークン、IDの実値をコード・ログ・回答へ出さない。
- 認証、シート構造、既存データを変更する場合は事前確認する。

## 検証

- GAS Web Appの疎通を安全なpingで確認する。
- 対象APIの正常系とエラー表示を確認する。
- スプレッドシートの対象IDとカラム対応を確認する。
- GAS変更は構文確認後にテスト環境で動作確認する。
- Vercel変更はローカル検証とビルド確認を行う。

`clasp push`、`clasp deploy`、Vercelデプロイ、`main`へのpushは外部状態を変えるため、変更内容と影響を示してユーザー承認後に実行する。

## よくある修正（Workspace アプリのパスは `workspace/` 配下。このリポジトリには `app-kanri/`・`cross-trade/`・`議事録からタスク管理/` など別アプリも同居している）

- シート操作の追加: `main.py` に `routers/{name}.py` を登録 → `core/sheets.py` でカラム対応を定義
- Calendar / Tasks 操作の追加: `workspace/gas/{Service}.gs` に関数追加 → `Code.gs` の case にアクション追加 → `clasp push`
- 環境変数の追加: `.env` → `main.py` で `os.getenv()` → Vercel の Project Settings にも同じ変数を設定。既存の必須変数は `GAS_WEB_APP_URL`・`GEMINI_API_KEY`・`API_SECRET_TOKEN`・`GOOGLE_SERVICE_ACCOUNT_JSON`・`SPREADSHEET_ID`（値は表示しない）
- Drive 保存先フォルダIDはスプレッドシートの設定側に持つ

## デバッグ

- Vercel ログ: `vercel logs workspace --tail`
- GAS 疎通: GAS Web App URL に `?action=ping`。GAS の実行ログは Apps Script ダッシュボードで確認する
- GAS の API・デプロイ手順は `gas-automation-toolkit` / `gas-design-lead`、Vercel × FastAPI の定型は `new-vercel-app` スキルを使う
