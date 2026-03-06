"""
routers/announcements.py  ─  お知らせテロップ管理
シート列: id, content, active, expires_at
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error
from core.sheets import get_all_values

router = APIRouter()
_SHEET = APP_CONFIG["sheet_names"]["announcements"]
_HEADERS = ["id", "content", "active", "expires_at"]


def _ensure_headers():
    from core.sheets import get_worksheet
    ws = get_worksheet(_SHEET)
    if not ws.get_all_values():
        ws.append_row(_HEADERS)


@router.get("/api/announcements")
def get_announcements(_token=Depends(verify_token)):
    try:
        _ensure_headers()
        rows = get_all_values(_SHEET)
        result = []
        now = datetime.now()
        for i, row in enumerate(rows[1:], start=2):
            if len(row) < 4:
                row = row + [""] * (4 - len(row))
            if row[2] != "TRUE":
                continue
            expires_at = row[3]
            if expires_at:
                try:
                    exp_dt = datetime.strptime(expires_at, "%Y-%m-%d")
                    if exp_dt < now:
                        continue
                except Exception:
                    pass
            result.append({
                "row": i,
                "id": row[0],
                "content": row[1],
                "expires_at": row[3],
            })
        return {"announcements": result}
    except Exception as e:
        log_error("announcements.get", "お知らせ取得エラー", e)
        raise HTTPException(status_code=500, detail=str(e))
