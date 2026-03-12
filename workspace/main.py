"""
main.py  ─  Workspace Next v3 FastAPI エントリポイント

Vercel 担当:
  - UI 配信（index.html）
  - Gemini AI エンドポイント群

Google 系操作（Sheets / Tasks / Calendar / Drive）は
GAS Web App（GAS_WEB_APP_URL）に委譲。
"""
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error, log_info

app = FastAPI(
    title=APP_CONFIG["app_name"],
    version=APP_CONFIG["version"],
    docs_url="/api/docs",
    redoc_url=None,
)


# ── 設定 API ─────────────────────────────────────────────────
@app.get("/api/config")
def get_config():
    return {
        "app_name":  APP_CONFIG["app_name"],
        "icon":      APP_CONFIG["icon"],
        "version":   APP_CONFIG["version"],
        "auth_mode": APP_CONFIG["auth"]["mode"],
        "gas_url":   os.environ.get("GAS_WEB_APP_URL", ""),
    }


# ── AI エンドポイント ─────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    context: dict | None = None


class AnalyzeTodoRequest(BaseModel):
    content: str


class GenerateJournalRequest(BaseModel):
    completed_todos: list[str] = []
    agenda: list[str] = []
    task_comments: list[dict] = []
    event_comments: list[dict] = []


class SuggestFocusRequest(BaseModel):
    agenda: list[dict] = []


class StructureChatRequest(BaseModel):
    messages: list[dict] = []


@app.post("/api/ai/chat")
def ai_chat(body: ChatRequest, _token=Depends(verify_token)):
    try:
        from integrations.gemini import chat
        result = chat(body.message, body.context)
        return {"reply": result}
    except Exception as e:
        log_error("ai.chat", "AI壁打ちエラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/analyze-todo")
def ai_analyze_todo(body: AnalyzeTodoRequest, _token=Depends(verify_token)):
    try:
        from integrations.gemini import analyze_todo
        return analyze_todo(body.content)
    except Exception as e:
        log_error("ai.analyze_todo", "ToDo分析エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/generate-journal")
def ai_generate_journal(body: GenerateJournalRequest, _token=Depends(verify_token)):
    try:
        from integrations.gemini import generate_journal
        result = generate_journal(
            body.completed_todos,
            body.agenda,
            task_comments=body.task_comments or None,
            event_comments=body.event_comments or None,
        )
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
        return {"result": result}
    except Exception as e:
        log_error("ai.structure_chat", "会話整理エラー", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── フロントエンド配信 ─────────────────────────────────────────
@app.get("/{full_path:path}")
def frontend(full_path: str = ""):
    template = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(template.read_text(encoding="utf-8"))
