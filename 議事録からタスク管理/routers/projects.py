"""
routers/projects.py  ─  プロジェクト CRUD API
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error, log_info
from core.sheets import append_row, get_all_values, get_worksheet

router = APIRouter(prefix="/api/projects", tags=["projects"])
_SHEET = APP_CONFIG["sheet_names"]["projects"]


def _rows_to_dicts(values: list[list]) -> list[dict]:
    if not values or len(values) < 2:
        return []
    headers = values[0]
    result = []
    for row in values[1:]:
        padded = row + [""] * max(0, len(headers) - len(row))
        result.append(dict(zip(headers, padded)))
    return result


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""


@router.get("")
def list_projects(_token=Depends(verify_token)):
    try:
        values = get_all_values(_SHEET)
        return {"success": True, "data": _rows_to_dicts(values)}
    except Exception as e:
        log_error("list_projects", "プロジェクト一覧取得エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_project(body: ProjectCreate, _token=Depends(verify_token)):
    try:
        project_id = str(uuid.uuid4())[:8]
        created_at = datetime.now().strftime("%Y-%m-%d")
        append_row(_SHEET, [project_id, body.name, created_at, body.description])
        log_info("create_project", f"プロジェクト作成: {body.name}")
        return {"success": True, "id": project_id, "name": body.name}
    except Exception as e:
        log_error("create_project", "プロジェクト作成エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
def delete_project(project_id: str, _token=Depends(verify_token)):
    try:
        ws = get_worksheet(_SHEET)
        values = ws.get_all_values()
        if not values or len(values) < 2:
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

        for i, row in enumerate(values[1:], start=2):
            if row and row[0] == project_id:
                ws.delete_rows(i)
                log_info("delete_project", f"プロジェクト削除: {project_id}")
                return {"success": True}

        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")
    except HTTPException:
        raise
    except Exception as e:
        log_error("delete_project", "プロジェクト削除エラー", e)
        raise HTTPException(status_code=500, detail=str(e))
