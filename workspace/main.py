"""
main.py  ─  Workspace Next v2 FastAPI エントリポイント
"""
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error, log_info
from core.sheets import get_worksheet
from routers import todos, agenda, journal, links, announcements, logs, memos, settings_api

# ── アプリ初期化 ───────────────────────────────────────────────
app = FastAPI(
    title=APP_CONFIG["app_name"],
    version=APP_CONFIG["version"],
    docs_url="/api/docs",
    redoc_url=None,
)

# ── ルーター登録 ───────────────────────────────────────────────
app.include_router(todos.router)
app.include_router(agenda.router)
app.include_router(journal.router)
app.include_router(links.router)
app.include_router(announcements.router)
app.include_router(logs.router)
app.include_router(memos.router)
app.include_router(settings_api.router)


# ── 設定 API ─────────────────────────────────────────────────
@app.get("/api/config")
def get_config():
    return {
        "app_name": APP_CONFIG["app_name"],
        "icon": APP_CONFIG["icon"],
        "version": APP_CONFIG["version"],
        "auth_mode": APP_CONFIG["auth"]["mode"],
    }


# ── 初期セットアップ ───────────────────────────────────────────
@app.post("/api/setup")
def setup(_token=Depends(verify_token)):
    """スプレッドシートの全シート・ヘッダーを自動作成する。"""
    try:
        sn = APP_CONFIG["sheet_names"]

        sheet_headers = {
            sn["todos"]:         ["id", "content", "priority", "effort", "completed", "delete_flag", "created_at"],
            sn["links"]:         ["id", "title", "url", "category", "created_at", "delete_flag"],
            sn["journal"]:       ["id", "date", "content", "auto_summary", "created_at"],
            sn["announcements"]: ["id", "content", "active", "expires_at"],
            sn["memos"]:         ["id", "content", "color", "created_at"],
            sn["settings"]:      ["key", "value", "description"],
            sn["logs"]:          ["タイムスタンプ", "レベル", "発生元", "メッセージ"],
        }

        for sheet_name, headers in sheet_headers.items():
            ws = get_worksheet(sheet_name)
            if not ws.get_all_values():
                ws.append_row(headers)

        # 設定シートにデフォルト値
        ws_s = get_worksheet(sn["settings"])
        values = ws_s.get_all_values()
        existing_keys = {r[0] for r in values if r}
        if "app_name" not in existing_keys:
            ws_s.append_row(["app_name", APP_CONFIG["app_name"], "アプリの表示名"])
        # サービスアカウントのメールを記録（Drive共有案内用）
        if "service_account_email" not in existing_keys:
            import json as _json, os as _os
            sa_info = _json.loads(_os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "{}"))
            sa_email = sa_info.get("client_email", "")
            if sa_email:
                ws_s.append_row(["service_account_email", sa_email, "サービスアカウントメール（Drive共有用）"])

        log_info("setup", "初期セットアップ完了")
        return {"success": True, "message": "初期セットアップが完了しました"}
    except Exception as e:
        log_error("setup", "初期セットアップエラー", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── AI エンドポイント ─────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    context: dict | None = None


class AnalyzeTodoRequest(BaseModel):
    content: str


class GenerateJournalRequest(BaseModel):
    completed_todos: list[str] = []
    agenda: list[str] = []


class SuggestFocusRequest(BaseModel):
    agenda: list[dict] = []


class StructureChatRequest(BaseModel):
    messages: list[dict] = []


@app.post("/api/ai/chat")
def ai_chat(body: ChatRequest, _token=Depends(verify_token)):
    try:
        from integrations.gemini import chat
        result = chat(body.message, body.context)
        log_info("ai.chat", "AI壁打ちチャット実行")
        return {"reply": result}
    except Exception as e:
        log_error("ai.chat", "AI壁打ちエラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/analyze-todo")
def ai_analyze_todo(body: AnalyzeTodoRequest, _token=Depends(verify_token)):
    try:
        from integrations.gemini import analyze_todo
        result = analyze_todo(body.content)
        return result
    except Exception as e:
        log_error("ai.analyze_todo", "ToDo分析エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/generate-journal")
def ai_generate_journal(body: GenerateJournalRequest, _token=Depends(verify_token)):
    try:
        from integrations.gemini import generate_journal
        result = generate_journal(body.completed_todos, body.agenda)
        return {"journal": result}
    except Exception as e:
        log_error("ai.generate_journal", "日報生成エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/suggest-focus")
def ai_suggest_focus(body: SuggestFocusRequest, _token=Depends(verify_token)):
    try:
        from integrations.gemini import suggest_focus
        result = suggest_focus(body.agenda)
        return {"suggestion": result}
    except Exception as e:
        log_error("ai.suggest_focus", "集中タイム提案エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/structure-chat")
def ai_structure_chat(body: StructureChatRequest, _token=Depends(verify_token)):
    try:
        from integrations.gemini import structure_chat
        result = structure_chat(body.messages)
        log_info("ai.structure_chat", "会話整理実行")
        return {"result": result}
    except Exception as e:
        log_error("ai.structure_chat", "会話整理エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks")
def get_tasks(_token=Depends(verify_token)):
    try:
        from integrations.tasks import get_today_tasks
        tasks = get_today_tasks()
        return {"tasks": tasks}
    except ValueError as e:
        # 環境変数未設定は 503 で返す（フロント側でグレースフルに処理）
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log_error("tasks.get", "Google Tasks 取得エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/tasks/{task_id}/complete")
def complete_task(task_id: str, _token=Depends(verify_token)):
    try:
        from integrations.tasks import complete_task as _complete
        _complete(task_id)
        log_info("tasks.complete", f"タスク完了: {task_id}")
        return {"success": True}
    except Exception as e:
        log_error("tasks.complete", "タスク完了エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── フロントエンド配信 ─────────────────────────────────────────
@app.get("/{full_path:path}")
def frontend(full_path: str = ""):
    template = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(template.read_text(encoding="utf-8"))


# ── Vercel: app変数をそのまま公開（@vercel/python がASGIを自動検出）
