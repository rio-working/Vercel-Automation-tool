"""
main.py  ─  FastAPI エントリポイント
議事録AI分析ツール：プロジェクト/会議管理、GASへのAI処理依頼を担う。
"""
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from mangum import Mangum

from config import APP_CONFIG
from core.auth import verify_token
from core.logger import log_error, log_info
from core.sheets import get_worksheet
from routers import logs, projects, meetings

# ── アプリ初期化 ─────────────────────────────────────────────
app = FastAPI(
    title=APP_CONFIG["app_name"],
    version=APP_CONFIG["version"],
    docs_url="/api/docs",
    redoc_url=None,
)

# ── ルーター登録 ─────────────────────────────────────────────
app.include_router(projects.router)
app.include_router(meetings.router)
app.include_router(logs.router)

if APP_CONFIG["integrations"]["slack"]["enabled"]:
    from integrations import slack
    app.include_router(slack.router)


# ── 設定 API（フロントエンドが起動時に呼び出す）──────────────
@app.get("/api/config")
def get_config():
    return {
        "app_name":  APP_CONFIG["app_name"],
        "icon":      APP_CONFIG["icon"],
        "theme":     APP_CONFIG["theme"],
        "features":  APP_CONFIG["features"],
        "gas_url":   os.environ.get("GAS_WEB_APP_URL", ""),
        "auth_mode": APP_CONFIG["auth"]["mode"],
    }


# ── 初期セットアップ（シート自動作成）────────────────────────
@app.post("/api/setup")
def setup(_token=Depends(verify_token)):
    """スプレッドシートにシート・ヘッダーを自動作成する。"""
    try:
        sn = APP_CONFIG["sheet_names"]

        # プロジェクトシート
        ws_p = get_worksheet(sn["projects"])
        if not ws_p.get_all_values():
            ws_p.append_row(["ID", "プロジェクト名", "作成日", "説明"])

        # 会議履歴シート
        ws_m = get_worksheet(sn["meetings"])
        if not ws_m.get_all_values():
            ws_m.append_row([
                "ID", "プロジェクトID", "会議名", "日付",
                "ステータス", "文字起こし", "議事録JSON", "MermaidCode", "ガントJSON"
            ])

        # 設定シート
        ws_s = get_worksheet(sn["settings"])
        if not ws_s.get_all_values():
            ws_s.append_row(["キー", "値"])
            ws_s.append_row(["アプリ名", APP_CONFIG["app_name"]])

        # ログシート
        ws_l = get_worksheet(sn["logs"])
        if not ws_l.get_all_values():
            ws_l.append_row(["タイムスタンプ", "レベル", "発生元", "メッセージ"])

        log_info("setup", "初期セットアップ完了")
        return {"success": True, "message": "初期セットアップが完了しました"}
    except Exception as e:
        log_error("setup", "初期セットアップエラー", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── フロントエンド配信 ────────────────────────────────────────
@app.get("/{full_path:path}")
def frontend(full_path: str = ""):
    template = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(template.read_text(encoding="utf-8"))


# ── Vercel サーバーレス用ハンドラー ──────────────────────────
handler = Mangum(app)
