"""
routers/journal.py  ─  インテリジェント日報
シート列: id, date, content, auto_summary, created_at
Drive 保存は GAS の saveToDrive アクションに委譲。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error, log_info
from core.sheets import append_row, get_all_values

router = APIRouter()
_SHEET = APP_CONFIG["sheet_names"]["journal"]
_HEADERS = ["id", "date", "content", "auto_summary", "created_at"]


def _ensure_headers():
    from core.sheets import get_worksheet
    ws = get_worksheet(_SHEET)
    rows = ws.get_all_values()
    if not rows:
        ws.append_row(_HEADERS)
    elif rows[0][0] != "id":
        ws.insert_row(_HEADERS, index=1)


class JournalCreate(BaseModel):
    date: str  # YYYY-MM-DD
    content: str
    auto_summary: str = ""


@router.get("/api/journal")
def get_journal(_token=Depends(verify_token)):
    try:
        _ensure_headers()
        rows = get_all_values(_SHEET)
        result = []
        for i, row in enumerate(rows[1:], start=2):
            if len(row) < 5:
                row = row + [""] * (5 - len(row))
            result.append({
                "row": i,
                "id": row[0],
                "date": row[1],
                "content": row[2],
                "auto_summary": row[3],
                "created_at": row[4],
            })
        return {"journals": list(reversed(result))}  # 新しい順
    except Exception as e:
        log_error("journal.get", "日報一覧取得エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/journal")
def create_journal(body: JournalCreate, _token=Depends(verify_token)):
    try:
        _ensure_headers()
        import uuid
        journal_id = str(uuid.uuid4())[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [journal_id, body.date, body.content, body.auto_summary, now]
        append_row(_SHEET, row)
        log_info("journal.create", f"日報保存: {body.date}")
        return {"success": True, "id": journal_id}
    except Exception as e:
        log_error("journal.create", "日報保存エラー", e)
        raise HTTPException(status_code=500, detail=str(e))
