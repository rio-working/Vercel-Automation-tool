"""
core/logger.py  ─  ログ管理（Vercel 用シンプル版）
Google 系処理は GAS に移行済みのため、コンソール出力のみ。
"""
import logging

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("workspace")


def log_info(source: str, message: str) -> None:
    _logger.info(f"[{source}] {message}")


def log_warn(source: str, message: str) -> None:
    _logger.warning(f"[{source}] {message}")


def log_error(source: str, message: str, error: Exception = None) -> None:
    full = f"[{source}] {message}: {error}" if error else f"[{source}] {message}"
    _logger.error(full)
