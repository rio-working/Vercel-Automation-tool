# GAS Web App セットアップ手順

## 概要
Google 系操作（スプレッドシート / Tasks / Calendar / Drive）は GAS Web App が担当します。

---

## 1. GAS プロジェクト作成

1. [script.google.com](https://script.google.com) を開く
2. 「新しいプロジェクト」を作成
3. プロジェクト名を「Workspace GAS」などに設定

---

## 2. ファイルをコピー

`workspace/gas/` フォルダ内の以下のファイルを GAS エディタに追加：

| ファイル | 内容 |
|---|---|
| `Code.gs` | ルーター（doGet / doPost） |
| `Utils.gs` | 共通ユーティリティ |
| `Todos.gs` | ToDo CRUD |
| `Journal.gs` | 日報 CRUD + Drive 保存 |
| `Links.gs` | リンク CRUD |
| `Memos.gs` | メモ CRUD |
| `Announcements.gs` | お知らせ |
| `Settings.gs` | 設定シート |
| `Logs.gs` | ログ |
| `Agenda.gs` | Google Calendar |
| `Tasks.gs` | Google Tasks |

- GAS エディタで「ファイルを追加」→「スクリプト」で各ファイルを追加
- `appsscript.json` の内容は「プロジェクトの設定」→「appsscript.json ファイルをエディタで表示」から上書き

---

## 3. Tasks 上級サービスを有効化

1. エディタ左の「サービス」(+) をクリック
2. 「Tasks API」を選択して追加
3. `userSymbol` が `Tasks` になっていることを確認

---

## 4. スクリプトプロパティを設定

「プロジェクトの設定」→「スクリプトプロパティ」で以下を追加：

| キー | 値 |
|---|---|
| `SPREADSHEET_ID` | 対象スプレッドシートのID |
| `API_SECRET_TOKEN` | Vercel の `API_SECRET_TOKEN` と同じ値 |
| `GOOGLE_CALENDAR_ID` | メインカレンダーのID（任意） |
| `GOOGLE_EXTRA_CALENDAR_IDS` | 追加カレンダーIDのカンマ区切り（任意） |

---

## 5. Web App としてデプロイ

1. 「デプロイ」→「新しいデプロイ」
2. 種類: **「ウェブアプリ」**
3. 設定:
   - 実行者: **「自分」**
   - アクセスできるユーザー: **「全員」**
4. 「デプロイ」をクリック
5. 表示された **ウェブアプリの URL** をコピー

---

## 6. Vercel 環境変数に設定

Vercel ダッシュボード → Settings → Environment Variables に追加：

| キー | 値 |
|---|---|
| `GAS_WEB_APP_URL` | 手順5でコピーしたURL |

設定後、Vercel で Redeploy（または次回プッシュで自動デプロイ）。

---

## 7. 動作確認

アプリを開いてログインし、ToDo / アジェンダ / タスクが表示されれば完了です。

### ログ確認
エラーが起きた場合はスプレッドシートの「ログ」シートに記録されます。

---

## GAS の再デプロイについて

コードを変更した場合は「デプロイ」→「デプロイを管理」→「✏️ 編集」→「バージョン: 新しいバージョン」→「デプロイ」で反映されます。
