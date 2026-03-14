# 議事録からタスク管理ツール — SoW（作業範囲定義）

## 概要
会議音声ファイルをアップロードするだけで、議事録・フローチャート・ガントチャートを自動生成するツール。
GeminiのAIが経営者目線で分析し、優先タスク・委任可能タスク・放置リスクを自動整理する。

## 技術スタック
| 層 | 採用 | 理由 |
|---|---|---|
| フロントエンド | Vanilla JS + Tailwind + Mermaid.js | テンプレート統一・CDNで軽量 |
| バックエンド | FastAPI（Vercel） | テンプレート流用・実績あり |
| AI処理・通知 | GAS | Drive直接アクセス・Gemini Files API呼び出し |
| データ | Googleスプレッドシート | 非エンジニアも操作可能 |

## 処理フロー
```
ユーザー（DriveファイルID入力）
  → Vercel（会議レコード作成、ステータス=待機中）
  → Vercel（ステータス=処理中に変更）
  → GAS doPost（processMeeting アクション）
    → DriveApp でファイル取得
    → Gemini Files API にアップロード（resumable upload）
    → gemini-2.0-flash-exp で一括生成
      ・文字起こし全文
      ・議事録（agenda/decisions/priority_tasks/delegate_tasks/risks/carryover_tasks）
      ・フローチャート Mermaid コード
      ・ガントチャート JSON
    → Sheets.gs でスプレッドシートに保存（ステータス=完了）
    → Notify.gs で Slack + メール通知
  → フロントエンドが3秒間隔ポーリングで完了を検知
  → Mermaid.js でフローチャート表示
```

## スプレッドシート設計
| シート名 | 列 |
|---|---|
| プロジェクト | ID / プロジェクト名 / 作成日 / 説明 |
| 会議履歴 | ID / プロジェクトID / 会議名 / 日付 / ステータス / 文字起こし / 議事録JSON / MermaidCode / ガントJSON |
| 設定 | キー / 値 |
| ログ | タイムスタンプ / レベル / 発生元 / メッセージ |

## 環境変数（Vercel）
- `SPREADSHEET_ID` : GoogleスプレッドシートID
- `GOOGLE_SERVICE_ACCOUNT_JSON` : サービスアカウントJSON
- `API_SECRET_TOKEN` : 認証トークン（GASと共通）
- `GAS_WEB_APP_URL` : GAS Web App URL
- `GEMINI_API_KEY` : Gemini APIキー（将来の直接呼び出し用）
- `SLACK_WEBHOOK_URL` : Slack通知（任意）

## GAS スクリプトプロパティ
- `GEMINI_API_KEY`
- `SPREADSHEET_ID`
- `API_SECRET_TOKEN`
- `SLACK_WEBHOOK_URL`（任意）
- `NOTIFY_EMAIL`（任意）

## スコープ外
- Notion連携（スプレッドシートで管理）
- ログイン・権限管理
- Word・PDF出力
- リアルタイム文字起こし
- Phase2/Phase3機能

## 注意事項
- GAS Web App 実行時間上限: 6分（大きな音声は分割推奨）
- Vercel Serverless 実行時間: 10秒（GAS呼び出し後即座に返す非同期方式で対応）
- Gemini Files API: gemini-2.0-flash-exp は音声ファイルを直接処理可能
- スプレッドシート1セル上限: 50,000文字（長文は切り詰め対応済み）
