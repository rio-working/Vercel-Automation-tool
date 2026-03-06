"""
api/index.py  ─  Vercel エントリポイント
Vercel は api/ ディレクトリのファイルをサーバーレス関数として自動認識する。
"""
import sys
import os

# workspace/ をパスに追加（相対インポート対応）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import handler  # noqa: F401  Mangum handler
