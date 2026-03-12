"""
routers/memos.py  ─  付箋メモ CRUD
シート列: id, content, color, created_at
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error, log_info
from core.sheets import append_row, get_all_values, get_worksheet, update_cell, _read_cache

router = APIRouter()
_SHEET = APP_CONFIG["sheet_names"]["memos"]
_HEADERS = ["id", "content", "color", "created_at"]

COL = {h: i + 1 for i, h in enumerate(_HEADERS)}


class MemoCreate(BaseModel):
    content: str
    color: str = "yellow"


def _ensure_headers():
    ws = get_worksheet(_SHEET)
    rows = ws.get_all_values()
    if not rows:
        ws.append_row(_HEADERS)
    elif not rows[0] or rows[0][0] != "id":
        ws.insert_row(_HEADERS, index=1)


def _rows_to_memos(rows: list[list]) -> list[dict]:
    result = []
    for i, row in enumerate(rows[1:], start=2):
        if len(row) < 4:
            row = row + [""] * (4 - len(row))
        if not row[0]:  # 空行スキップ
            continue
        result.append({
            "row": i,
            "id": row[0],
            "content": row[1],
            "color": row[2] or "yellow",
            "created_at": row[3],
        })
    return result


@router.get("/api/memos")
def get_memos(_token=Depends(verify_token)):
    try:
        _ensure_headers()
        rows = get_all_values(_SHEET)
        return {"memos": _rows_to_memos(rows)}
    except Exception as e:
        log_error("memos.get", "メモ一覧取得エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/memos")
def create_memo(body: MemoCreate, _token=Depends(verify_token)):
    try:
        _ensure_headers()
        memo_id = str(uuid.uuid4())[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        append_row(_SHEET, [memo_id, body.content, body.color, now])
        log_info("memos.create", f"メモ追加: {body.content[:20]}")
        return {"success": True, "id": memo_id}
    except Exception as e:
        log_error("memos.create", "メモ追加エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/memos/{row}")
def delete_memo(row: int, _token=Depends(verify_token)):
    try:
        ws = get_worksheet(_SHEET)
        ws.delete_rows(row)
        _read_cache.pop(_SHEET, None)
        log_info("memos.delete", f"メモ削除: row={row}")
        return {"success": True}
    except Exception as e:
        log_error("memos.delete", "メモ削除エラー", e)
        raise HTTPException(status_code=500, detail=str(e))
