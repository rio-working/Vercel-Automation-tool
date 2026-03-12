"""
routers/links.py  ─  クイック・リンク管理
シート列: id, title, url, category, created_at
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error, log_info
from core.sheets import append_row, get_all_values, update_cell

router = APIRouter()
_SHEET = APP_CONFIG["sheet_names"]["links"]
_HEADERS = ["id", "title", "url", "category", "created_at", "delete_flag"]


def _ensure_headers():
    from core.sheets import get_worksheet
    ws = get_worksheet(_SHEET)
    rows = ws.get_all_values()
    if not rows:
        ws.append_row(_HEADERS)
    elif not rows[0] or rows[0][0] != "id":
        ws.insert_row(_HEADERS, index=1)


class LinkCreate(BaseModel):
    title: str
    url: str
    category: str = "その他"


@router.get("/api/links")
def get_links(_token=Depends(verify_token)):
    try:
        _ensure_headers()
        rows = get_all_values(_SHEET)
        result = []
        for i, row in enumerate(rows[1:], start=2):
            if len(row) < 6:
                row = row + [""] * (6 - len(row))
            if row[5] == "TRUE":
                continue
            result.append({
                "row": i,
                "id": row[0],
                "title": row[1],
                "url": row[2],
                "category": row[3],
                "created_at": row[4],
            })
        return {"links": result}
    except Exception as e:
        log_error("links.get", "リンク一覧取得エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/links")
def create_link(body: LinkCreate, _token=Depends(verify_token)):
    try:
        _ensure_headers()
        import uuid
        link_id = str(uuid.uuid4())[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [link_id, body.title, body.url, body.category, now, "FALSE"]
        append_row(_SHEET, row)
        log_info("links.create", f"リンク追加: {body.title}")
        return {"success": True, "id": link_id}
    except Exception as e:
        log_error("links.create", "リンク追加エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/links/{row}")
def delete_link(row: int, _token=Depends(verify_token)):
    try:
        update_cell(_SHEET, row, 6, "TRUE")
        log_info("links.delete", f"リンク論理削除: row={row}")
        return {"success": True}
    except Exception as e:
        log_error("links.delete", "リンク削除エラー", e)
        raise HTTPException(status_code=500, detail=str(e))
