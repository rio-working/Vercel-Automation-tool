"""
routers/logs.py  ─  ログシートの参照・クリア
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error
from core.sheets import get_all_values, get_worksheet

router = APIRouter(prefix="/api/logs", tags=["logs"])
_LOG_SHEET = APP_CONFIG["sheet_names"]["logs"]


@router.get("")
def get_logs(
    level: Optional[str] = Query(None, description="INFO / WARN / ERROR"),
    limit: int = Query(100, ge=1, le=1000),
    _token=Depends(verify_token),
):
    try:
        values = get_all_values(_LOG_SHEET)
        if not values or len(values) <= 1:
            return {"success": True, "data": []}

        headers = values[0]
        logs = []
        for row in values[1:]:
            padded = row + [""] * max(0, len(headers) - len(row))
            logs.append(dict(zip(headers, padded)))

        if level:
            logs = [l for l in logs if l.get("レベル", "").upper() == level.upper()]

        logs.reverse()  # 新しい順
        return {"success": True, "data": logs[:limit], "total": len(logs)}
    except Exception as e:
        log_error("get_logs", "ログ取得エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("")
def clear_logs(keep: int = Query(50, ge=0), _token=Depends(verify_token)):
    try:
        ws = get_worksheet(_LOG_SHEET)
        values = ws.get_all_values()
        delete_count = len(values) - keep - 1  # ヘッダー行を除く

        if delete_count <= 0:
            return {"success": True, "message": "削除対象なし"}

        for _ in range(delete_count):
            ws.delete_rows(2)  # 常にヘッダーの次の行を削除

        return {"success": True, "message": f"ログをクリアしました（最新{keep}件保持）"}
    except Exception as e:
        log_error("clear_logs", "ログクリアエラー", e)
        raise HTTPException(status_code=500, detail=str(e))
