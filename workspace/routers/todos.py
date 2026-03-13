"""
routers/todos.py  ─  Smart ToDo CRUD
シート列: id, content, priority, effort, completed, delete_flag, created_at
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error, log_info
from core.sheets import append_row, get_all_values, update_cell, update_row

router = APIRouter()
_SHEET = APP_CONFIG["sheet_names"]["todos"]
_HEADERS = ["id", "content", "priority", "effort", "completed", "delete_flag", "created_at"]

# 列インデックス（1-indexed）
COL = {h: i + 1 for i, h in enumerate(_HEADERS)}


class TodoCreate(BaseModel):
    content: str
    priority: str = "中"
    effort: str = "中"


class TodoUpdate(BaseModel):
    content: str | None = None
    priority: str | None = None
    effort: str | None = None
    completed: bool | None = None


def _ensure_headers():
    """ヘッダー行がなければ先頭に挿入する（既存データがあっても対応）。"""
    from core.sheets import get_worksheet
    ws = get_worksheet(_SHEET)
    rows = ws.get_all_values()
    if not rows:
        ws.append_row(_HEADERS)
    elif rows[0][0] != "id":
        ws.insert_row(_HEADERS, index=1)


def _rows_to_todos(rows: list[list]) -> list[dict]:
    result = []
    for i, row in enumerate(rows[1:], start=2):  # ヘッダー行スキップ、row_index は2始まり
        if len(row) < 7:
            row = row + [""] * (7 - len(row))
        if row[5] == "TRUE":  # delete_flag
            continue
        result.append({
            "row": i,
            "id": row[0],
            "content": row[1],
            "priority": row[2],
            "effort": row[3],
            "completed": row[4] == "TRUE",
            "created_at": row[6],
        })
    return result


@router.get("/api/todos")
def get_todos(_token=Depends(verify_token)):
    try:
        _ensure_headers()
        rows = get_all_values(_SHEET)
        return {"todos": _rows_to_todos(rows)}
    except Exception as e:
        log_error("todos.get", "ToDo一覧取得エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/todos")
def create_todo(body: TodoCreate, _token=Depends(verify_token)):
    try:
        _ensure_headers()
        import uuid
        todo_id = str(uuid.uuid4())[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [todo_id, body.content, body.priority, body.effort, "FALSE", "FALSE", now]
        append_row(_SHEET, row)
        log_info("todos.create", f"ToDo追加: {body.content}")
        return {"success": True, "id": todo_id}
    except Exception as e:
        log_error("todos.create", "ToDo追加エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/todos/{row}")
def update_todo(row: int, body: TodoUpdate, _token=Depends(verify_token)):
    try:
        rows = get_all_values(_SHEET)
        if row < 2 or row > len(rows):
            raise HTTPException(status_code=404, detail="行が見つかりません")

        current = rows[row - 1]
        if len(current) < 7:
            current = current + [""] * (7 - len(current))

        if body.content is not None:
            current[1] = body.content
        if body.priority is not None:
            current[2] = body.priority
        if body.effort is not None:
            current[3] = body.effort
        if body.completed is not None:
            current[4] = "TRUE" if body.completed else "FALSE"

        update_row(_SHEET, row, current)
        log_info("todos.update", f"ToDo更新: row={row}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        log_error("todos.update", "ToDo更新エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/todos/{row}")
def delete_todo(row: int, _token=Depends(verify_token)):
    try:
        update_cell(_SHEET, row, COL["delete_flag"], "TRUE")
        log_info("todos.delete", f"ToDo論理削除: row={row}")
        return {"success": True}
    except Exception as e:
        log_error("todos.delete", "ToDo削除エラー", e)
        raise HTTPException(status_code=500, detail=str(e))
