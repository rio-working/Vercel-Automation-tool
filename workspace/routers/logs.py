"""
routers/logs.py  ─  ログ一覧取得
"""
from fastapi import APIRouter, Depends, HTTPException

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error
from core.sheets import get_all_values

router = APIRouter()
_SHEET = APP_CONFIG["sheet_names"]["logs"]


@router.get("/api/logs")
def get_logs(_token=Depends(verify_token)):
    try:
        rows = get_all_values(_SHEET)
        if len(rows) <= 1:
            return {"logs": []}
        result = []
        for row in rows[1:]:
            if len(row) < 4:
                row = row + [""] * (4 - len(row))
            result.append({
                "timestamp": row[0],
                "level": row[1],
                "source": row[2],
                "message": row[3],
            })
        return {"logs": list(reversed(result[-100:]))}  # 最新100件
    except Exception as e:
        log_error("logs.get", "ログ取得エラー", e)
        raise HTTPException(status_code=500, detail=str(e))
