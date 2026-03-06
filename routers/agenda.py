"""
routers/agenda.py  ─  デイリー・アジェンダ（Google Calendar予定取得）
"""
from fastapi import APIRouter, Depends, HTTPException

from core.auth import verify_token
from core.logger import log_error
from integrations.calendar import get_today_events

router = APIRouter()


@router.get("/api/agenda")
def get_agenda(_token=Depends(verify_token)):
    try:
        events = get_today_events()
        return {"events": events}
    except Exception as e:
        log_error("agenda.get", "アジェンダ取得エラー", e)
        raise HTTPException(status_code=500, detail=str(e))
