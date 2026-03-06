#!/bin/bash
# Workspace Next v2 ローカル起動スクリプト
# 使い方: bash start_local.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# .env 読み込み
if [ -f "$SCRIPT_DIR/.env" ]; then
  export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
  echo "✅ .env を読み込みました"
else
  echo "❌ .env ファイルが見つかりません"
  echo "   .env.example をコピーして .env を作成してください"
  exit 1
fi

# venv 確認
VENV="/tmp/workspace_venv"
if [ ! -f "$VENV/bin/uvicorn" ]; then
  echo "⚙️  パッケージをインストールします..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" -q
fi

echo "🚀 Workspace Next v2 を起動します..."
echo "   → http://localhost:8000"
echo "   Ctrl+C で停止"
echo ""
cd "$SCRIPT_DIR"
"$VENV/bin/uvicorn" main:app --reload --port 8000
