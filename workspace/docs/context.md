# Workspace Next v2 要件定義書

## プロジェクト概要

個人用ダッシュボードアプリ。FastAPI × Vercel × Google Sheets × Gemini AI で構築。
URLは Vercel でホスティングし、ブラウザからアクセスするシングルページアプリ（SPA）。

---

## 技術スタック

| 分類 | 技術 |
|------|------|
| バックエンド | FastAPI (Python) |
| ホスティング | Vercel (サーバーレス) |
| データ保存 | Google Sheets (gspread) |
| AI | Gemini 2.0 Flash (google-generativeai) |
| カレンダー | Google Calendar API (google-api-python-client) |
| フロントエンド | Vanilla JS + CSS (グラスモーフィズム) |

---

## 機能一覧

### 1. Smart ToDo
- テキスト入力 → AIが自動で優先度（高/中/低）・工数（大/中/小）を判定
- 完了チェック・論理削除対応
- データ保存先: Todos シート

### 2. デイリー・アジェンダ
- Google Calendar から本日の予定を取得・表示（時刻順、終日含む）
- AIが隙間時間を分析して集中タイム提案

### 3. AI壁打ちチャット
- Gemini 2.0 Flash とのチャット
- 今日のToDo・予定をコンテキストとして自動送信

### 4. インテリジェント日報
- 完了タスク＋今日の予定から AI が日報テキストを自動生成
- 手動編集・保存対応
- 過去の日報一覧表示

### 5. クイックリンク
- カテゴリ別リンク管理（仕事/ツール/参考/その他）
- 論理削除対応

### 6. ポモドーロタイマー
- 作業時間・休憩時間を設定可能（デフォルト 25/5 分）
- 完了時に音演出（Web Audio API）
- 完了セッション数カウント

### 7. お知らせテロップ
- スプレッドシートの Announcements シートから取得
- アクティブかつ有効期限内のお知らせをスクロール表示

### 8. スクリーンセーバー
- 宇宙テーマ（星が降る Canvas アニメーション）
- 時刻・日付表示
- クリックまたはキーで終了

---

## スプレッドシート設計

| シート名 | 列構成 |
|---------|--------|
| Todos | id, content, priority, effort, completed, delete_flag, created_at |
| Links | id, title, url, category, created_at, delete_flag |
| Journal | id, date, content, auto_summary, created_at |
| Announcements | id, content, active, expires_at |
| 設定 | key, value, description |
| ログ | タイムスタンプ, レベル, 発生元, メッセージ |

---

## 環境変数

| 変数名 | 必須 | 用途 |
|--------|------|------|
| SPREADSHEET_ID | ✅ | データ保存スプレッドシートID |
| GOOGLE_SERVICE_ACCOUNT_JSON | ✅ | Google API認証（1行JSON） |
| GEMINI_API_KEY | ✅ | Gemini API キー |
| GOOGLE_CALENDAR_ID | - | カレンダーID（省略時: primary） |
| API_SECRET_TOKEN | ✅ | フロントエンド認証トークン |

---

## APIエンドポイント

| メソッド | パス | 機能 |
|---------|------|------|
| GET | /api/config | 設定取得 |
| POST | /api/setup | 初期シート作成 |
| GET | /api/todos | ToDo一覧 |
| POST | /api/todos | ToDo追加 |
| PUT | /api/todos/{row} | ToDo更新 |
| DELETE | /api/todos/{row} | ToDo論理削除 |
| GET | /api/agenda | 本日カレンダー予定 |
| GET | /api/journal | 日報一覧 |
| POST | /api/journal | 日報保存 |
| GET | /api/links | リンク一覧 |
| POST | /api/links | リンク追加 |
| DELETE | /api/links/{row} | リンク論理削除 |
| GET | /api/announcements | お知らせ取得 |
| POST | /api/ai/chat | AI壁打ちチャット |
| POST | /api/ai/analyze-todo | ToDo優先度・工数判定 |
| POST | /api/ai/generate-journal | 日報自動生成 |
| POST | /api/ai/suggest-focus | 集中タイム提案 |
| GET | /api/logs | ログ一覧 |

---

## デプロイ手順

1. `.env.example` をコピーして `.env` を作成し、各値を設定
2. Vercel プロジェクトを作成し、環境変数を設定
3. GitHub リポジトリと連携してプッシュ → 自動デプロイ
4. 初回: `/api/setup` を POST してシートを初期化（要 X-Api-Token ヘッダー）

---

## ローカル起動

```bash
cd "02_開発/Vercel/Workspace/workspace"
pip install -r requirements.txt
uvicorn main:app --reload
# → http://localhost:8000 でアクセス
```

---

## 設計方針

- **差分最小**: テンプレート `core/` をそのまま流用し、Workspace固有の実装のみ追加
- **論理削除**: Todos・Links は delete_flag で論理削除（データは残す）
- **AI失敗でも動く**: AI連携は try/except で囲み、失敗時はデフォルト値で動作継続
- **認証**: X-Api-Token ヘッダーで全APIを保護（mode: "token"）
