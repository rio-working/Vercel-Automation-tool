"""
routers/meetings.py  ─  会議 CRUD + GAS AI処理依頼 API
"""
import json
import os
import uuid
from datetime import datetime, timezone, timedelta

_JST = timezone(timedelta(hours=9))
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error, log_info
from core.sheets import append_row, get_all_values, get_worksheet

router = APIRouter(prefix="/api/meetings", tags=["meetings"])
_SHEET = APP_CONFIG["sheet_names"]["meetings"]

# 列インデックス（0-based）
COL_ID           = 0
COL_PROJECT_ID   = 1
COL_NAME         = 2
COL_DATE         = 3
COL_STATUS       = 4
COL_TRANSCRIPT   = 5
COL_MINUTES_JSON = 6
COL_MERMAID      = 7
COL_GANTT_JSON   = 8


def _rows_to_dicts(values: list[list]) -> list[dict]:
    if not values or len(values) < 2:
        return []
    headers = values[0]
    result = []
    for row in values[1:]:
        padded = row + [""] * max(0, len(headers) - len(row))
        result.append(dict(zip(headers, padded)))
    return result


class MeetingCreate(BaseModel):
    project_id: str
    name: str
    date: Optional[str] = ""
    drive_file_id: Optional[str] = ""


class ProcessRequest(BaseModel):
    drive_file_id: str
    prev_meeting_id: Optional[str] = ""


class TranscribeRequest(BaseModel):
    drive_file_id: str


class MinutesRequest(BaseModel):
    prev_meeting_id: Optional[str] = ""


@router.get("")
def list_meetings(
    project_id: Optional[str] = Query(None),
    _token=Depends(verify_token),
):
    try:
        values = get_all_values(_SHEET)
        data = _rows_to_dicts(values)
        if project_id:
            data = [m for m in data if m.get("プロジェクトID") == project_id]
        return {"success": True, "data": data}
    except Exception as e:
        log_error("list_meetings", "会議一覧取得エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_meeting(body: MeetingCreate, _token=Depends(verify_token)):
    try:
        meeting_id = str(uuid.uuid4())[:8]
        date = body.date or datetime.now(_JST).strftime("%Y-%m-%d")
        append_row(_SHEET, [
            meeting_id, body.project_id, body.name, date,
            "待機中", "", "", "", ""
        ])
        log_info("create_meeting", f"会議作成: {body.name}")
        return {"success": True, "id": meeting_id, "name": body.name}
    except Exception as e:
        log_error("create_meeting", "会議作成エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{meeting_id}/process")
async def process_meeting(
    meeting_id: str,
    body: ProcessRequest,
    _token=Depends(verify_token),
):
    """AI処理開始：ステータスを「処理中」に更新してGASに処理依頼する。"""
    gas_url = os.environ.get("GAS_WEB_APP_URL", "")
    if not gas_url:
        raise HTTPException(status_code=500, detail="GAS_WEB_APP_URL が未設定です")

    # ステータスを「処理中」に更新
    ws = get_worksheet(_SHEET)
    row_index = _find_row_index(ws, meeting_id)
    if row_index is None:
        raise HTTPException(status_code=404, detail="会議が見つかりません")

    ws.update_cell(row_index, COL_STATUS + 1, "処理中")

    # GASへ非同期で処理依頼（Vercelは即座に返す）
    token = os.environ.get("API_SECRET_TOKEN", "")
    payload = {
        "action": "processMeeting",
        "token": token,
        "meeting_id": meeting_id,
        "drive_file_id": body.drive_file_id,
        "prev_meeting_id": body.prev_meeting_id,
    }
    await _call_gas_fire_and_forget(gas_url, payload, "process_meeting", meeting_id)

    log_info("process_meeting", f"AI処理依頼送信: {meeting_id}")
    return {"success": True, "message": "AI処理を開始しました", "meeting_id": meeting_id}


def _find_row_index(ws, meeting_id: str) -> int:
    """会議IDの行番号（1-based）を返す。見つからなければ None。"""
    values = ws.get_all_values()
    for i, row in enumerate(values[1:], start=2):
        if row and row[COL_ID] == meeting_id:
            return i
    return None


async def _call_gas_fire_and_forget(gas_url: str, payload: dict, log_source: str, meeting_id: str):
    """GASへ fire-and-forget でリクエストし、タイムアウトは正常扱いにする。
    GAS Web AppはPOST時に302リダイレクト→GET変換でbodyが消えるため、
    GET+クエリパラメータで送信する。
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            await client.get(gas_url, params=payload, timeout=10.0)
    except httpx.TimeoutException:
        log_info(log_source, f"GAS処理継続中（タイムアウト正常）: {meeting_id}")
    except Exception as e:
        log_error(log_source, f"GAS呼び出しエラー（処理継続の可能性あり）: {meeting_id}: {e}")


@router.post("/{meeting_id}/transcribe")
async def transcribe_meeting(
    meeting_id: str,
    body: TranscribeRequest,
    _token=Depends(verify_token),
):
    """①文字起こし開始：ステータスを「文字起こし中」に更新してGASに依頼する。"""
    gas_url = os.environ.get("GAS_WEB_APP_URL", "")
    if not gas_url:
        raise HTTPException(status_code=500, detail="GAS_WEB_APP_URL が未設定です")

    ws = get_worksheet(_SHEET)
    row_index = _find_row_index(ws, meeting_id)
    if row_index is None:
        raise HTTPException(status_code=404, detail="会議が見つかりません")

    ws.update_cell(row_index, COL_STATUS + 1, "文字起こし中")

    token = os.environ.get("API_SECRET_TOKEN", "")
    payload = {
        "action": "transcribeAudio",
        "token": token,
        "meeting_id": meeting_id,
        "drive_file_id": body.drive_file_id,
    }
    await _call_gas_fire_and_forget(gas_url, payload, "transcribe_meeting", meeting_id)
    log_info("transcribe_meeting", f"文字起こし依頼送信: {meeting_id}")
    return {"success": True, "message": "文字起こしを開始しました", "meeting_id": meeting_id}


@router.post("/{meeting_id}/minutes")
async def generate_minutes(
    meeting_id: str,
    body: MinutesRequest,
    _token=Depends(verify_token),
):
    """②議事録生成開始：ステータスを「議事録生成中」に更新してGASに依頼する。"""
    gas_url = os.environ.get("GAS_WEB_APP_URL", "")
    if not gas_url:
        raise HTTPException(status_code=500, detail="GAS_WEB_APP_URL が未設定です")

    ws = get_worksheet(_SHEET)
    row_index = _find_row_index(ws, meeting_id)
    if row_index is None:
        raise HTTPException(status_code=404, detail="会議が見つかりません")

    ws.update_cell(row_index, COL_STATUS + 1, "議事録生成中")

    token = os.environ.get("API_SECRET_TOKEN", "")
    payload = {
        "action": "generateMinutes",
        "token": token,
        "meeting_id": meeting_id,
        "prev_meeting_id": body.prev_meeting_id,
    }
    await _call_gas_fire_and_forget(gas_url, payload, "generate_minutes", meeting_id)
    log_info("generate_minutes", f"議事録生成依頼送信: {meeting_id}")
    return {"success": True, "message": "議事録生成を開始しました", "meeting_id": meeting_id}


@router.post("/{meeting_id}/flowchart")
async def generate_flowchart(
    meeting_id: str,
    _token=Depends(verify_token),
):
    """③フローチャート生成開始：ステータスを「フロー生成中」に更新してGASに依頼する。"""
    gas_url = os.environ.get("GAS_WEB_APP_URL", "")
    if not gas_url:
        raise HTTPException(status_code=500, detail="GAS_WEB_APP_URL が未設定です")

    ws = get_worksheet(_SHEET)
    row_index = _find_row_index(ws, meeting_id)
    if row_index is None:
        raise HTTPException(status_code=404, detail="会議が見つかりません")

    ws.update_cell(row_index, COL_STATUS + 1, "フロー生成中")

    token = os.environ.get("API_SECRET_TOKEN", "")
    payload = {
        "action": "generateFlowchart",
        "token": token,
        "meeting_id": meeting_id,
    }
    await _call_gas_fire_and_forget(gas_url, payload, "generate_flowchart", meeting_id)
    log_info("generate_flowchart", f"フロー生成依頼送信: {meeting_id}")
    return {"success": True, "message": "フローチャート生成を開始しました", "meeting_id": meeting_id}


@router.post("/{meeting_id}/gantt")
async def generate_gantt(
    meeting_id: str,
    _token=Depends(verify_token),
):
    """④ガントチャート生成開始：ステータスを「ガント生成中」に更新してGASに依頼する。"""
    gas_url = os.environ.get("GAS_WEB_APP_URL", "")
    if not gas_url:
        raise HTTPException(status_code=500, detail="GAS_WEB_APP_URL が未設定です")

    ws = get_worksheet(_SHEET)
    row_index = _find_row_index(ws, meeting_id)
    if row_index is None:
        raise HTTPException(status_code=404, detail="会議が見つかりません")

    ws.update_cell(row_index, COL_STATUS + 1, "ガント生成中")

    token = os.environ.get("API_SECRET_TOKEN", "")
    payload = {
        "action": "generateGantt",
        "token": token,
        "meeting_id": meeting_id,
    }
    await _call_gas_fire_and_forget(gas_url, payload, "generate_gantt", meeting_id)
    log_info("generate_gantt", f"ガント生成依頼送信: {meeting_id}")
    return {"success": True, "message": "ガントチャート生成を開始しました", "meeting_id": meeting_id}


@router.get("/{meeting_id}/status")
def get_meeting_status(meeting_id: str, _token=Depends(verify_token)):
    """処理ステータス確認（ポーリング用）。"""
    try:
        values = get_all_values(_SHEET)
        headers = values[0] if values else []
        for row in values[1:]:
            if row and row[COL_ID] == meeting_id:
                padded = row + [""] * max(0, len(headers) - len(row))
                data = dict(zip(headers, padded))
                return {"success": True, "data": data}
        raise HTTPException(status_code=404, detail="会議が見つかりません")
    except HTTPException:
        raise
    except Exception as e:
        log_error("get_meeting_status", "ステータス取得エラー", e)
        raise HTTPException(status_code=500, detail=str(e))
