APP_CONFIG = {
    "app_name": "議事録AI分析ツール",
    "icon": "🎙️",
    "version": "1.0.0",
    "theme": "blue",

    "sheet_names": {
        "projects":  "プロジェクト",
        "meetings":  "会議履歴",
        "settings":  "設定",
        "logs":      "ログ",
    },

    "features": {
        "export_csv":    True,
        "slack_notify":  True,
        "email_notify":  True,
    },

    "integrations": {
        "slack": {"enabled": True},
    },

    "auth": {
        "mode": "token",
    },
}
