import json
import os
from datetime import datetime, timezone, timedelta

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

JST = timezone(timedelta(hours=9))
NEW_BADGE_DAYS = 3

# アプリ一覧シートの列定数（1-indexed）
COL = {
    "ID": 1, "DATE": 2, "TITLE": 3, "DESCRIPTION": 4,
    "LIKES": 5, "ZIP_URL": 6, "SHEET_URL": 7, "NOTE_URL": 8,
    "APP_URL": 9, "CATEGORY": 10,
}


def _get_ws(sheet_name: str):
    creds = Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]),
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)
    ss = client.open_by_key(os.environ["SPREADSHEET_ID"])
    return ss.worksheet(sheet_name)


def _to_int(val, default=0):
    try:
        return int(float(str(val).replace(",", ""))) if val else default
    except (ValueError, TypeError):
        return default


def _format_date(val) -> str:
    if isinstance(val, datetime):
        return val.strftime("%Y/%m/%d")
    if val:
        for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(str(val).split()[0], fmt).strftime("%Y/%m/%d")
            except ValueError:
                continue
    return ""


def _row_to_app(row: list, row_num: int) -> dict:
    def cell(col):
        idx = col - 1
        return row[idx] if idx < len(row) else ""

    now = datetime.now(JST)
    three_days_ago = now - timedelta(days=NEW_BADGE_DAYS)
    date_raw = cell(COL["DATE"])
    date_str = _format_date(date_raw)

    is_new = False
    if date_raw:
        try:
            if isinstance(date_raw, datetime):
                pub = date_raw.replace(tzinfo=JST) if date_raw.tzinfo is None else date_raw
            else:
                pub = datetime.strptime(str(date_raw).split()[0], "%Y/%m/%d").replace(tzinfo=JST)
            is_new = pub > three_days_ago
        except ValueError:
            pass

    return {
        "rowNum": row_num,
        "id": _to_int(cell(COL["ID"]), row_num - 1),
        "date": date_str,
        "title": str(cell(COL["TITLE"])),
        "description": str(cell(COL["DESCRIPTION"])),
        "likes": _to_int(cell(COL["LIKES"])),
        "zipUrl": str(cell(COL["ZIP_URL"])),
        "sheetUrl": str(cell(COL["SHEET_URL"])),
        "noteUrl": str(cell(COL["NOTE_URL"])),
        "appUrl": str(cell(COL["APP_URL"])),
        "category": str(cell(COL["CATEGORY"])) or "未分類",
        "isNew": is_new,
    }


# ---------------------------------------------------------------------------
# アプリ一覧
# ---------------------------------------------------------------------------

def get_apps() -> list:
    ws = _get_ws("アプリ一覧")
    all_rows = ws.get_all_values()
    result = []
    for i, row in enumerate(all_rows[1:], start=2):
        if not row or not row[0]:
            continue
        result.append(_row_to_app(row, i))
    return result


def add_like(app_id: int) -> int:
    ws = _get_ws("アプリ一覧")
    all_rows = ws.get_all_values()
    for i, row in enumerate(all_rows[1:], start=2):
        if not row or not row[0]:
            continue
        if _to_int(row[0]) == int(app_id):
            current = _to_int(row[COL["LIKES"] - 1])
            new_count = current + 1
            ws.update_cell(i, COL["LIKES"], new_count)
            return new_count
    return -1


def save_app(data: dict) -> dict:
    ws = _get_ws("アプリ一覧")
    all_rows = ws.get_all_values()

    target_row = -1
    max_id = 0

    for i, row in enumerate(all_rows[1:], start=2):
        if not row or not row[0]:
            continue
        row_id = _to_int(row[0])
        if row_id > max_id:
            max_id = row_id
        if data.get("id") and row_id == _to_int(data["id"]):
            target_row = i

    if target_row == -1:
        # 新規追加
        new_id = max_id + 1
        date_str = datetime.now(JST).strftime("%Y/%m/%d")
        row_values = [
            new_id,
            date_str,
            str(data.get("title", "")),
            str(data.get("description", "")),
            0,
            str(data.get("zipUrl", "")),
            str(data.get("sheetUrl", "")),
            str(data.get("noteUrl", "")),
            str(data.get("appUrl", "")),
            str(data.get("category", "未分類")),
        ]
        ws.append_row(row_values, value_input_option="USER_ENTERED")
    else:
        # 更新（日付・いいね数は保持）
        current_row = all_rows[target_row - 1]
        current_likes = _to_int(current_row[COL["LIKES"] - 1]) if len(current_row) >= COL["LIKES"] else 0
        current_date = current_row[COL["DATE"] - 1] if len(current_row) >= COL["DATE"] else ""
        ws.update(
            f"A{target_row}:J{target_row}",
            [[
                _to_int(data["id"]),
                current_date,
                str(data.get("title", "")),
                str(data.get("description", "")),
                current_likes,
                str(data.get("zipUrl", "")),
                str(data.get("sheetUrl", "")),
                str(data.get("noteUrl", "")),
                str(data.get("appUrl", "")),
                str(data.get("category", "未分類")),
            ]],
            value_input_option="USER_ENTERED",
        )

    return {"success": True}


def delete_app(app_id: int) -> dict:
    ws = _get_ws("アプリ一覧")
    all_rows = ws.get_all_values()
    for i, row in enumerate(all_rows[1:], start=2):
        if not row or not row[0]:
            continue
        if _to_int(row[0]) == int(app_id):
            ws.delete_rows(i)
            return {"success": True}
    return {"success": False, "message": "アプリが見つかりません"}


# ---------------------------------------------------------------------------
# お知らせ
# ---------------------------------------------------------------------------

def get_notice() -> str:
    try:
        ws = _get_ws("お知らせ")
        rows = ws.get_all_values()
        if len(rows) <= 1:
            return ""
        last = rows[-1]
        date_str = _format_date(last[0]) if last[0] else ""
        content = last[1] if len(last) > 1 else ""
        if not content:
            return ""
        try:
            dt = datetime.strptime(date_str, "%Y/%m/%d")
            date_label = dt.strftime("%m/%d")
        except ValueError:
            date_label = date_str
        return f"{date_label}: {content}"
    except Exception:
        return ""


def save_notice(text: str) -> dict:
    ws = _get_ws("お知らせ")
    date_str = datetime.now(JST).strftime("%Y/%m/%d")
    ws.append_row([date_str, text], value_input_option="USER_ENTERED")
    return {"success": True}


# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

def get_settings() -> dict:
    try:
        ws = _get_ws("設定")
        rows = ws.get_all_values()
        settings = {}
        for row in rows[1:]:
            if row and row[0]:
                settings[row[0]] = row[1] if len(row) > 1 else ""
        return settings
    except Exception:
        return {}


def save_settings(data: dict) -> dict:
    ws = _get_ws("設定")
    rows = ws.get_all_values()
    existing = {row[0]: i + 1 for i, row in enumerate(rows) if row and row[0]}
    for key, value in data.items():
        value = str(value)
        if key in existing:
            ws.update_cell(existing[key], 2, value)
        else:
            ws.append_row([key, value])
    return {"success": True}
