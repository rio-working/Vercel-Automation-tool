"""
routers/settings_api.py  ─  設定シート CRUD
シート列: key, value, description
GAS の getSettingsMap() はヘッダー行（row 0）をスキップする仕様のため、
シートには必ずヘッダー行を保持する。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error, log_info
from core.sheets import get_worksheet

router = APIRouter()
_SHEET = APP_CONFIG["sheet_names"]["settings"]
_HEADERS = ["key", "value", "description"]


def _ensure_headers(ws) -> list[list]:
    """ヘッダー行がなければ先頭に挿入し、全行を返す。"""
    rows = ws.get_all_values()
    if not rows:
        ws.append_row(_HEADERS)
        return [_HEADERS]
    if rows[0][0] != "key":
        ws.insert_row(_HEADERS, index=1)
        rows = [_HEADERS] + rows
    return rows


def _get_all_settings() -> dict:
    ws = get_worksheet(_SHEET)
    rows = _ensure_headers(ws)
    result = {}
    for row in rows[1:]:  # ヘッダースキップ
        if len(row) >= 2 and row[0]:
            result[row[0]] = row[1]
    return result


def _set_setting(key: str, value: str, description: str = ""):
    ws = get_worksheet(_SHEET)
    rows = _ensure_headers(ws)
    for i, row in enumerate(rows):
        if row and row[0] == key:
            ws.update(f"B{i+1}", [[value]])
            return
    ws.append_row([key, value, description])


class SettingUpdate(BaseModel):
    key: str
    value: str
    description: str = ""


@router.get("/api/settings")
def get_settings(_token=Depends(verify_token)):
    try:
        return {"settings": _get_all_settings()}
    except Exception as e:
        log_error("settings.get", "設定取得エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/settings")
def update_setting(body: SettingUpdate, _token=Depends(verify_token)):
    try:
        _set_setting(body.key, body.value, body.description)
        log_info("settings.update", f"設定更新: {body.key} = {body.value}")
        return {"success": True}
    except Exception as e:
        log_error("settings.update", "設定更新エラー", e)
        raise HTTPException(status_code=500, detail=str(e))
