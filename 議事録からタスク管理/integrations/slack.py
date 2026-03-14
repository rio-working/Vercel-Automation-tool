"""
integrations/slack.py  ─  Slack Webhook 通知
config.py で integrations.slack.enabled: True にして使う。
"""
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error, log_info

router = APIRouter(prefix="/api/integrations/slack", tags=["integrations"])


async def send_slack_message(text: str, color: str = "#4a86e8") -> None:
    """Slack Webhook にメッセージを送信する。"""
    url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not url:
        raise ValueError("SLACK_WEBHOOK_URL が未設定です")

    payload = {
        "attachments": [
            {
                "color": color,
                "text": text,
                "footer": APP_CONFIG["app_name"],
            }
        ]
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=payload, timeout=5.0)
        res.raise_for_status()


@router.post("/test")
async def test_slack(_token=Depends(verify_token)):
    if not APP_CONFIG["integrations"]["slack"]["enabled"]:
        raise HTTPException(status_code=400, detail="Slack連携が無効です（config.py を確認）")
    try:
        await send_slack_message(f"✅ {APP_CONFIG['app_name']} - Slack連携テスト成功")
        log_info("test_slack", "Slack接続テスト成功")
        return {"success": True, "message": "Slack通知を送信しました"}
    except Exception as e:
        log_error("test_slack", "Slack接続テスト失敗", e)
        raise HTTPException(status_code=500, detail=str(e))
