"""
core/logger.py  ─  ログ管理（Vercel 用）
Vercel コンソールとスプレッドシートの「ログ」シートの両方に記録する。
"""
import logging
from datetime import datetime

from config import APP_CONFIG

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("workspace")

_LOG_SHEET = APP_CONFIG["sheet_names"]["logs"]


def _write_to_sheet(level: str, source: str, message: str) -> None:
    try:
        from core.sheets import append_row
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        append_row(_LOG_SHEET, [timestamp, level, source, message])
    except Exception:
        pass


def log_info(source: str, message: str) -> None:
    _logger.info(f"[{source}] {message}")
    _write_to_sheet("INFO", source, message)


def log_warn(source: str, message: str) -> None:
    _logger.warning(f"[{source}] {message}")
    _write_to_sheet("WARN", source, message)


def log_error(source: str, message: str, error: Exception = None) -> None:
    full = f"{message}: {error}" if error else message
    _logger.error(f"[{source}] {full}")
    _write_to_sheet("ERROR", source, full)
