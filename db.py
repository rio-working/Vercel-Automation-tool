import json
import os
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# 列定数（1-indexed、スプレッドシートと同じ）
COL = {
    "CODE": 1, "NAME": 2, "BENEFIT": 3, "BENEFIT_VALUE": 4,
    "KENRI_MONTH": 5, "TRADE_DATE": 6, "SETTLED": 7, "QTY": 8,
    "SELL_PRICE": 9, "BUY_PRICE": 10, "SPREAD": 11, "GENRIKI": 12,
    "GENWATASHI": 13, "TOTAL_FEE": 14, "PROFIT": 15, "BROKER": 16, "NOTE": 17,
}


def _get_ws(sheet_name: str):
    creds = Credentials.from_service_account_info(
        json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]),
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)
    ss = client.open_by_id(os.environ["SPREADSHEET_ID"])
    return ss.worksheet(sheet_name)


def _to_float(val) -> float:
    try:
        return float(str(val).replace(",", "")) if val else 0.0
    except (ValueError, TypeError):
        return 0.0


def _to_int(val):
    try:
        return int(float(str(val).replace(",", ""))) if val else None
    except (ValueError, TypeError):
        return None


def _row_to_dict(row: list, row_num: int) -> dict:
    """スプレッドシートの1行（list）を辞書に変換"""
    def _cell(col):
        idx = col - 1
        return row[idx] if idx < len(row) else ""

    # 取得日のフォーマット統一
    trade_date_raw = _cell(COL["TRADE_DATE"])
    trade_date = ""
    if trade_date_raw:
        for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                trade_date = datetime.strptime(str(trade_date_raw), fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
        if not trade_date:
            trade_date = str(trade_date_raw)

    settled_raw = _cell(COL["SETTLED"])
    settled = settled_raw is True or str(settled_raw).upper() == "TRUE"

    return {
        "行番号": row_num,
        "コード": str(_cell(COL["CODE"])),
        "銘柄": str(_cell(COL["NAME"])),
        "優待内容": str(_cell(COL["BENEFIT"])),
        "優待価値": _to_float(_cell(COL["BENEFIT_VALUE"])),
        "権利月": _to_int(_cell(COL["KENRI_MONTH"])),
        "取得日": trade_date,
        "決済済み": settled,
        "株数": _to_int(_cell(COL["QTY"])) or 0,
        "売単価": _to_float(_cell(COL["SELL_PRICE"])),
        "買単価": _to_float(_cell(COL["BUY_PRICE"])),
        "差益": _to_float(_cell(COL["SPREAD"])),
        "現引": _to_float(_cell(COL["GENRIKI"])),
        "現渡": _to_float(_cell(COL["GENWATASHI"])),
        "手数料合計": _to_float(_cell(COL["TOTAL_FEE"])),
        "利益": _to_float(_cell(COL["PROFIT"])),
        "証券会社": str(_cell(COL["BROKER"])),
        "備考": str(_cell(COL["NOTE"])),
    }


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

def get_trades(settled=None, broker=None, start_date=None, end_date=None):
    ws = _get_ws("TradeData")
    all_rows = ws.get_all_values()  # 1回のAPI呼び出しで全行取得

    result = []
    for i, row in enumerate(all_rows[1:], start=2):  # 1行目はヘッダーなのでスキップ
        if not row or not row[0]:
            continue

        trade = _row_to_dict(row, i)

        # フィルタリング
        if settled is True and not trade["決済済み"]:
            continue
        if settled is False and trade["決済済み"]:
            continue
        if broker and trade["証券会社"] != broker:
            continue
        if start_date and trade["取得日"] and trade["取得日"] < start_date:
            continue
        if end_date and trade["取得日"] and trade["取得日"] > end_date:
            continue

        result.append(trade)

    return result


def add_master(data: dict) -> dict:
    ws = _get_ws("TradeData")
    benefit_value = _to_float(data.get("優待価値"))

    row = [
        str(data.get("コード", "")),
        str(data.get("銘柄", "")),
        str(data.get("優待内容", "")),
        benefit_value,
        data.get("権利月") or "",
        "",        # 取得日
        "FALSE",   # ✅
        "",        # 株数
        "",        # 売単価
        "",        # 買単価
        "",        # 差益
        "",        # 現引
        "",        # 現渡
        "",        # 手数料
        "",        # 利益
        "",        # 証券会社
        str(data.get("備考", "")),
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    return {"success": True, "message": "登録完了", "銘柄名": data.get("銘柄", "")}


def update_trade(row_num: int, data: dict) -> dict:
    ws = _get_ws("TradeData")

    qty = _to_float(data.get("株数"))
    sell_price = _to_float(data.get("売単価"))
    buy_price = _to_float(data.get("買単価"))
    genriki = _to_float(data.get("現引"))
    genwatashi = _to_float(data.get("現渡"))
    benefit_value = _to_float(data.get("優待価値"))

    spread = (sell_price - buy_price) * qty
    total_fee = genriki + genwatashi
    profit = benefit_value + spread - total_fee

    settled = data.get("決済済み", False)

    values = [[
        "",  # コード（読み取り専用）
        "",  # 銘柄（読み取り専用）
        str(data.get("優待内容", "")),
        benefit_value,
        data.get("権利月") or "",
        str(data.get("取得日") or ""),
        "TRUE" if settled else "FALSE",
        int(qty) if qty else "",
        sell_price if sell_price else "",
        buy_price if buy_price else "",
        spread if qty else "",
        genriki,
        genwatashi,
        total_fee,
        profit,
        str(data.get("証券会社", "")),
        str(data.get("備考", "")),
    ]]

    # コード・銘柄は変えないのでC列（3列目）〜Q列（17列目）のみ更新
    ws.update(
        f"C{row_num}:Q{row_num}",
        [[
            str(data.get("優待内容", "")),
            benefit_value,
            data.get("権利月") or "",
            str(data.get("取得日") or ""),
            "TRUE" if settled else "FALSE",
            int(qty) if qty else "",
            sell_price if sell_price else "",
            buy_price if buy_price else "",
            spread if qty else "",
            genriki,
            genwatashi,
            total_fee,
            profit,
            str(data.get("証券会社", "")),
            str(data.get("備考", "")),
        ]],
        value_input_option="USER_ENTERED",
    )
    return {"success": True, "message": "更新完了"}


def delete_trade(row_num: int) -> dict:
    ws = _get_ws("TradeData")
    ws.delete_rows(row_num)
    return {"success": True, "message": "削除完了"}


# ---------------------------------------------------------------------------
# P&L（Pythonで集計、API呼び出しはget_tradesの1回のみ）
# ---------------------------------------------------------------------------

def calculate_pl(broker=None, start_date=None, end_date=None) -> dict:
    all_trades = get_trades(None, broker, start_date, end_date)
    settled = [t for t in all_trades if t["決済済み"]]
    unsettled = [t for t in all_trades if not t["決済済み"]]

    return {
        "優待価値合計": sum(t["優待価値"] for t in settled),
        "差益合計": sum(t["差益"] for t in settled),
        "手数料合計": sum(t["手数料合計"] for t in settled),
        "利益合計": sum(t["利益"] for t in settled),
        "決済済み件数": len(settled),
        "未決済件数": len(unsettled),
    }


def get_monthly_pl(year: int) -> list:
    all_trades = get_trades()
    monthly = [{
        "月": m, "取引数": 0, "決済済み": 0, "未決済": 0,
        "優待価値": 0.0, "差益": 0.0, "手数料": 0.0, "利益": 0.0,
    } for m in range(1, 13)]

    for t in all_trades:
        kenri_month = t["権利月"]
        if not kenri_month or not (1 <= kenri_month <= 12):
            continue
        if t["取得日"]:
            try:
                if datetime.strptime(t["取得日"], "%Y-%m-%d").year != year:
                    continue
            except ValueError:
                continue

        m = monthly[kenri_month - 1]
        m["取引数"] += 1
        if t["決済済み"]:
            m["決済済み"] += 1
        else:
            m["未決済"] += 1
        m["優待価値"] += t["優待価値"]
        m["差益"] += t["差益"]
        m["手数料"] += t["手数料合計"]
        m["利益"] += t["利益"]

    return monthly


def get_yearly_pl() -> list:
    all_trades = get_trades(settled=True)
    yearly: dict[int, dict] = {}

    for t in all_trades:
        if not t["取得日"]:
            continue
        try:
            yr = datetime.strptime(t["取得日"], "%Y-%m-%d").year
        except ValueError:
            continue
        if yr not in yearly:
            yearly[yr] = {"年": yr, "取引数": 0, "優待価値": 0.0, "差益": 0.0, "手数料": 0.0, "利益": 0.0}
        yearly[yr]["取引数"] += 1
        yearly[yr]["優待価値"] += t["優待価値"]
        yearly[yr]["差益"] += t["差益"]
        yearly[yr]["手数料"] += t["手数料合計"]
        yearly[yr]["利益"] += t["利益"]

    return sorted(yearly.values(), key=lambda x: x["年"], reverse=True)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

DEFAULT_BROKERS = ["SBI証券", "楽天証券", "マネックス証券", "松井証券",
                   "auカブコム証券", "GMOクリック証券", "SMBC日興証券"]


def get_settings() -> dict:
    try:
        ws = _get_ws("Settings")
        rows = ws.get_all_values()
        settings = {}
        for row in rows[1:]:
            if row and row[0]:
                settings[row[0]] = row[1] if len(row) > 1 else ""

        brokers_raw = settings.get("証券会社一覧", "")
        settings["証券会社一覧"] = (
            [b.strip() for b in brokers_raw.split(",") if b.strip()]
            if brokers_raw else DEFAULT_BROKERS
        )
        try:
            settings["デフォルト株数"] = int(settings.get("デフォルト株数", 100))
        except (ValueError, TypeError):
            settings["デフォルト株数"] = 100

        return settings
    except Exception:
        return {"デフォルト証券会社": "SBI証券", "デフォルト株数": 100, "証券会社一覧": DEFAULT_BROKERS}


def update_settings(data: dict) -> dict:
    ws = _get_ws("Settings")
    rows = ws.get_all_values()

    existing = {row[0]: i + 1 for i, row in enumerate(rows) if row and row[0]}

    for key, value in data.items():
        if isinstance(value, list):
            value = ",".join(value)
        value = str(value)
        if key in existing:
            ws.update_cell(existing[key], 2, value)
        else:
            ws.append_row([key, value])

    return {"success": True}
