"""
core/auth.py  ─  認証
config.py の auth.mode に応じて動作を切り替える。
  "token" : X-Api-Token ヘッダーを検証（API_SECRET_TOKEN 環境変数）
  "none"  : 認証スキップ（社内限定公開など）
"""
import os

from fastapi import Header, HTTPException

from config import APP_CONFIG


async def verify_token(x_api_token: str = Header(None)) -> str | None:
    if APP_CONFIG["auth"]["mode"] == "none":
        return None

    secret = os.environ.get("API_SECRET_TOKEN", "")
    if not secret:
        raise HTTPException(status_code=500, detail="API_SECRET_TOKEN が未設定です")

    if x_api_token != secret:
        raise HTTPException(status_code=401, detail="認証に失敗しました")

    return x_api_token
