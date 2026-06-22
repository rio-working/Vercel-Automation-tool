# Workspace — Vercel + GAS 統合アプリ環境

複数のWebアプリとGAS（Google Apps Script）が連携する統合ワークスペース。Vercel（FastAPI）でシート操作・AI処理を担当し、GASでGoogle Calendar / Tasks / Drive を直接操作。

---

## 主要アプリ

| アプリ | パス | 説明 |
|--------|------|------|
| **Workspace** | `workspace/` | メインアプリ（日報・TODOの一元管理） |
| **Cross-Trade** | `cross-trade/` | クロス取引管理 |
| App Kanri | `app-kanri/` | アプリ管理 |
| 議事録からタスク管理 | `議事録からタスク管理/` | 会議記録の自動タスク化 |

---

## システム構成

```
Workspace（Vercel + GAS）
├── Vercel/FastAPI
│   ├── main.py          → スプレッドシート CRUD + AI エンドポイント
│   ├── routers/         → todos, journal, links, memos 等
│   └── core/sheets.py   → gspread ラッパー（30秒キャッシュ）
└── GAS（`workspace/gas/`）
    ├── Code.gs          → Google Calendar / Tasks / Drive ルーター
    ├── Agenda.gs        → カレンダーイベント取得
    ├── Tasks.gs         → Google Tasks 操作
    └── Drive.gs         → Markdown ファイル保存
```

---

## 主要な操作フロー

### 日報入力 → 自動保存

```
フロントエンド
  ↓
Vercel `/api/journal` (シート保存)
  ↓
GAS `/action?cmd=saveToDrive` (Drive保存)
```

### Google Calendar / Tasks 取得

```
フロントエンド
  ↓
GAS Web App URL `?action=getAgenda` / `?action=getTasks`
  ↓
Google の各サービス直接操作
```

### AI処理

```
フロントエンド
  ↓
Vercel `/api/ai/*` (Gemini API)
```

---

## 環境変数（`.env`）

| 変数 | 用途 | 必須 |
|------|------|------|
| `GAS_WEB_APP_URL` | GAS Web App URL（Google Calendar / Tasks操作） | Yes |
| `GEMINI_API_KEY` | Gemini API（AI処理） | Yes |
| `API_SECRET_TOKEN` | 通信認証トークン（Vercel ↔ GAS） | Yes |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google認証（スプレッドシート読み書き） | Yes |
| `SPREADSHEET_ID` | 管理スプレッドシートID | Yes |

---

## デプロイ

### Vercel（自動）

`main` ブランチへのプッシュで自動デプロイ。GitHub リポジトリ: `rio-working/Vercel-Automation-tool`

### GAS（手動）

```bash
cd workspace/gas
clasp push
```

---

## ファイル構成

```
Vecel公開/Workspace/
├── workspace/              ← メインアプリ（Vercel + GAS）
│   ├── workspace/          ← Vercel フロントエンド
│   ├── gas/                ← GAS スクリプト
│   ├── .vercel/
│   ├── .env                ← 環境変数（git除外）
│   └── .env.local          ← ローカル設定
├── cross-trade/            ← クロス取引管理
├── app-kanri/              ← アプリ管理
├── 議事録からタスク管理/
└── Vercel化マニュアル.md
```

---

## よくある作業

### Vercel の API を確認
```bash
cd workspace
cat main.py | grep "@app.post\|@app.get"
```

### GAS の受け付けアクション一覧
```bash
cd workspace/gas
grep "case '" Code.gs | cut -d"'" -f2 | sort -u
```

### スプレッドシート ID 確認
```bash
cat workspace/.env | grep SPREADSHEET_ID
```

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| GAS呼び出しが失敗 | API_SECRET_TOKEN が一致していない | `.env` を確認 |
| シート読み込みが遅い | キャッシュ期限切れ（30秒） | 数秒待機してリトライ |
| Gemini API エラー | GEMINI_API_KEY が無効 | API キーを更新 |

