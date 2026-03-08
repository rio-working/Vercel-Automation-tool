# ============================================================
# config.py  ─  Workspace Next v2 設定
# ============================================================

APP_CONFIG = {

    # ── 基本情報 ──────────────────────────────────────────────
    "app_name": "Workspace Next",
    "icon": "🚀",
    "version": "2.0.0",

    # ── スプレッドシートのシート名 ──────────────────────────────
    "sheet_names": {
        "todos":         "Todos",
        "links":         "Links",
        "journal":       "Journal",
        "announcements": "Announcements",
        "memos":         "Memos",
        "settings":      "設定",
        "logs":          "ログ",
    },

    # ── 認証 ──────────────────────────────────────────────────
    # "token": X-Api-Tokenヘッダーで認証（API_SECRET_TOKEN環境変数）
    # "none":  認証なし
    "auth": {
        "mode": "none",
    },
}
