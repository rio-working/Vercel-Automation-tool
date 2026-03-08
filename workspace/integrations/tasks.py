"""
integrations/tasks.py  ─  Google Tasks API 連携
リフレッシュトークン方式でアクセストークンを取得し、今日のタスクを返す。

必要な環境変数:
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
  GOOGLE_REFRESH_TOKEN

トークン取得手順: /tmp/get_oauth_token.py を実行してください。
"""
import os
from datetime import date, datetime, timezone

import httpx

from core.logger import log_error


def _get_access_token() -> str:
    """リフレッシュトークンからアクセストークンを取得する。"""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN", "")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Google Tasks 用の環境変数が未設定です (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REFRESH_TOKEN)")

    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_today_tasks() -> list[dict]:
    """今日が期限のタスク（またはすべてのタスク）を返す。"""
    try:
        access_token = _get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        # タスクリスト一覧を取得
        lists_resp = httpx.get(
            "https://tasks.googleapis.com/tasks/v1/users/@me/lists",
            headers=headers,
            timeout=10,
        )
        lists_resp.raise_for_status()
        task_lists = lists_resp.json().get("items", [])

        if not task_lists:
            return []

        # 最初のタスクリストからタスクを取得（未完了のみ）
        list_id = task_lists[0]["id"]
        today_str = date.today().isoformat()  # YYYY-MM-DD

        tasks_resp = httpx.get(
            f"https://tasks.googleapis.com/tasks/v1/lists/{list_id}/tasks",
            headers=headers,
            params={
                "showCompleted": "false",
                "showHidden": "false",
                "maxResults": 20,
            },
            timeout=10,
        )
        tasks_resp.raise_for_status()
        raw_tasks = tasks_resp.json().get("items", [])

        result = []
        for t in raw_tasks:
            due = t.get("due", "")
            # due は RFC3339 形式: 2024-01-15T00:00:00.000Z
            due_date = due[:10] if due else ""
            result.append({
                "id": t.get("id", ""),
                "title": t.get("title", ""),
                "due": due_date,
                "is_today": due_date == today_str,
                "notes": t.get("notes", ""),
            })

        return result

    except Exception as e:
        log_error("tasks.get_today", "Google Tasks 取得エラー", e)
        raise


def _get_default_list_id() -> tuple[str, str]:
    """アクセストークンとデフォルトタスクリストIDを返す。"""
    access_token = _get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = httpx.get(
        "https://tasks.googleapis.com/tasks/v1/users/@me/lists",
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    list_id = resp.json()["items"][0]["id"]
    return access_token, list_id


def complete_task(task_id: str) -> None:
    """指定タスクを完了済みにする。"""
    try:
        access_token, list_id = _get_default_list_id()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        resp = httpx.patch(
            f"https://tasks.googleapis.com/tasks/v1/lists/{list_id}/tasks/{task_id}",
            headers=headers,
            json={"status": "completed"},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        log_error("tasks.complete", "タスク完了エラー", e)
        raise
