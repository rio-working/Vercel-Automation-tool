"""
core/sheets.py  ─  Google Sheets 接続・共通操作
GASテンプレートの Utils.gs（シート操作部分）に相当。
実証済みパターン（クロス取引管理 db.py）を踏襲。
"""
import json
import os
import time

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# クライアントキャッシュ（5分間再利用）
_client: gspread.Client | None = None
_client_ts: float = 0
_CLIENT_TTL = 300

# 読み取りキャッシュ（30秒間再利用）
_read_cache: dict[str, dict] = {}
_CACHE_TTL = 30


def _get_client() -> gspread.Client:
    global _client, _client_ts
    now = time.time()
    if _client is None or now - _client_ts > _CLIENT_TTL:
        service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        _client = gspread.authorize(creds)
        _client_ts = now
    return _client


def _get_spreadsheet() -> gspread.Spreadsheet:
    return _get_client().open_by_key(os.environ["SPREADSHEET_ID"])


def get_worksheet(sheet_name: str) -> gspread.Worksheet:
    """シートを取得。存在しなければ自動作成する。"""
    ss = _get_spreadsheet()
    try:
        return ss.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        return ss.add_worksheet(title=sheet_name, rows=1000, cols=26)


def get_all_values(sheet_name: str) -> list[list]:
    """全行を取得（ヘッダー行含む）。30秒間キャッシュ。"""
    now = time.time()
    if sheet_name in _read_cache and now - _read_cache[sheet_name]["ts"] < _CACHE_TTL:
        return _read_cache[sheet_name]["data"]
    data = get_worksheet(sheet_name).get_all_values()
    _read_cache[sheet_name] = {"data": data, "ts": now}
    return data


def append_row(sheet_name: str, values: list) -> None:
    """末尾に行を追加する。"""
    get_worksheet(sheet_name).append_row(values, value_input_option="USER_ENTERED")
    _read_cache.pop(sheet_name, None)


def update_row(sheet_name: str, row_index: int, values: list) -> None:
    """指定行を丸ごと更新する（1-indexed）。"""
    ws = get_worksheet(sheet_name)
    end_col = chr(64 + len(values)) if len(values) <= 26 else "Z"
    ws.update(f"A{row_index}:{end_col}{row_index}", [values])
    _read_cache.pop(sheet_name, None)


def update_cell(sheet_name: str, row: int, col: int, value) -> None:
    """セルを1つ更新する（1-indexed）。"""
    get_worksheet(sheet_name).update_cell(row, col, value)
    _read_cache.pop(sheet_name, None)
