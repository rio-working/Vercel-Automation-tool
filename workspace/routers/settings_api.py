"""
routers/settings_api.py  ─  設定シート CRUD
シート列: key, value, description
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error, log_info
from core.sheets import get_worksheet

router = APIRouter()
_SHEET = APP_CONFIG["sheet_names"]["settings"]


def _get_all_settings() -> dict:
    ws = get_worksheet(_SHEET)
    rows = ws.get_all_values()
    result = {}
    for row in rows[1:]:  # ヘッダースキップ
        if len(row) >= 2 and row[0]:
            result[row[0]] = row[1]
    return result


def _set_setting(key: str, value: str, description: str = ""):
    ws = get_worksheet(_SHEET)
    rows = ws.get_all_values()
    for i, row in enumerate(rows):
        if row and row[0] == key:
            ws.update(f"B{i+1}", [[value]])
            return
    # 存在しなければ末尾に追加
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
