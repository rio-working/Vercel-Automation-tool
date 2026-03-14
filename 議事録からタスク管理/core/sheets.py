"""
core/sheets.py  ─  Google Sheets 接続・共通操作
GASテンプレートの Utils.gs（シート操作部分）に相当。
実証済みパターン（クロス取引管理 db.py）を踏襲。
"""
import json
import os

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# 同一Lambda実行内でクライアントを再利用してAPI呼び出し回数を削減
_client_cache: gspread.Client | None = None
_spreadsheet_cache: gspread.Spreadsheet | None = None


def _get_client() -> gspread.Client:
    global _client_cache
    if _client_cache is None:
        service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        _client_cache = gspread.authorize(creds)
    return _client_cache


def _get_spreadsheet() -> gspread.Spreadsheet:
    global _spreadsheet_cache
    if _spreadsheet_cache is None:
        _spreadsheet_cache = _get_client().open_by_key(os.environ["SPREADSHEET_ID"])
    return _spreadsheet_cache


def get_worksheet(sheet_name: str) -> gspread.Worksheet:
    """シートを取得。存在しなければ自動作成する。"""
    ss = _get_spreadsheet()
    try:
        return ss.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        return ss.add_worksheet(title=sheet_name, rows=1000, cols=26)


def get_all_values(sheet_name: str) -> list[list]:
    """全行を取得（ヘッダー行含む）。"""
    return get_worksheet(sheet_name).get_all_values()


def append_row(sheet_name: str, values: list) -> None:
    """末尾に行を追加する。"""
    get_worksheet(sheet_name).append_row(values, value_input_option="USER_ENTERED")


def update_row(sheet_name: str, row_index: int, values: list) -> None:
    """指定行を丸ごと更新する（1-indexed）。"""
    ws = get_worksheet(sheet_name)
    end_col = chr(64 + len(values)) if len(values) <= 26 else "Z"
    ws.update(f"A{row_index}:{end_col}{row_index}", [values])


def update_cell(sheet_name: str, row: int, col: int, value) -> None:
    """セルを1つ更新する（1-indexed）。"""
    get_worksheet(sheet_name).update_cell(row, col, value)
