"""
core/logger.py  ─  ログ管理
GASテンプレートの Utils.gs（ログ部分）に相当。
INFO / WARN / ERROR の3レベルをログシートに記録する。
"""
from datetime import datetime, timezone, timedelta

_JST = timezone(timedelta(hours=9))

from config import APP_CONFIG
from core.sheets import get_worksheet, append_row

_LOG_SHEET = APP_CONFIG["sheet_names"]["logs"]
_HEADERS = ["タイムスタンプ", "レベル", "発生元", "メッセージ"]


def _ensure_headers() -> None:
    """ログシートにヘッダーがなければ作成する。"""
    ws = get_worksheet(_LOG_SHEET)
    if not ws.get_all_values():
        ws.append_row(_HEADERS)


def _write(level: str, source: str, message: str) -> None:
    try:
        _ensure_headers()
        now = datetime.now(_JST).strftime("%Y-%m-%d %H:%M:%S")
        append_row(_LOG_SHEET, [now, level, source, message])
    except Exception:
        pass  # ログ書き込み失敗は処理を止めない


def log_info(source: str, message: str) -> None:
    _write("INFO", source, message)


def log_warn(source: str, message: str) -> None:
    _write("WARN", source, message)


def log_error(source: str, message: str, error: Exception = None) -> None:
    full = f"{message}: {error}" if error else message
    _write("ERROR", source, full)
