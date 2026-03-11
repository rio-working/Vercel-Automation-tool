"""
routers/agenda.py  ─  デイリー・アジェンダ（Google Calendar予定取得）
"""
import json

from fastapi import APIRouter, Depends, HTTPException

from core.auth import verify_token
from core.logger import log_error
from integrations.calendar import get_today_events
from routers.settings_api import _get_all_settings

router = APIRouter()


@router.get("/api/agenda")
def get_agenda(_token=Depends(verify_token)):
    try:
        # 設定から選択済みカレンダーIDを取得
        selected_ids = None
        try:
            settings = _get_all_settings()
            raw = settings.get("calendar_selected_ids", "")
            if raw:
                selected_ids = json.loads(raw)
        except Exception:
            pass

        events = get_today_events(selected_ids=selected_ids)
        return {"events": events}
    except Exception as e:
        log_error("agenda.get", "アジェンダ取得エラー", e)
        raise HTTPException(status_code=500, detail=str(e))
