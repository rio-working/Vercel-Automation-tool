import os

from flask import Flask, jsonify, render_template, request

import db

app = Flask(__name__)

SPREADSHEET_URL = os.environ.get("SPREADSHEET_URL", "")


def _check_admin() -> bool:
    admin_key = os.environ.get("ADMIN_KEY", "")
    if not admin_key:
        return False
    return request.headers.get("X-Admin-Key", "") == admin_key


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@app.route("/api/data", methods=["GET"])
def api_get_data():
    apps = db.get_apps()
    notice = db.get_notice()
    return jsonify({
        "apps": apps,
        "notice": notice,
        "spreadsheetUrl": SPREADSHEET_URL,
    })


# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------

@app.route("/api/apps/<int:app_id>/like", methods=["POST"])
def api_add_like(app_id):
    new_count = db.add_like(app_id)
    if new_count == -1:
        return jsonify({"success": False, "message": "アプリが見つかりません"}), 404
    return jsonify({"success": True, "count": new_count})


@app.route("/api/apps", methods=["POST"])
def api_save_app():
    if not _check_admin():
        return jsonify({"success": False, "message": "権限がありません"}), 403
    data = request.get_json(force=True)
    if not data.get("title"):
        return jsonify({"success": False, "message": "タイトルは必須です"}), 400
    result = db.save_app(data)
    return jsonify(result)


@app.route("/api/apps/<int:app_id>", methods=["DELETE"])
def api_delete_app(app_id):
    if not _check_admin():
        return jsonify({"success": False, "message": "権限がありません"}), 403
    result = db.delete_app(app_id)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Notice
# ---------------------------------------------------------------------------

@app.route("/api/notice", methods=["POST"])
def api_save_notice():
    if not _check_admin():
        return jsonify({"success": False, "message": "権限がありません"}), 403
    data = request.get_json(force=True)
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"success": False, "message": "お知らせ内容は必須です"}), 400
    result = db.save_notice(text)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Settings（管理者用）
# ---------------------------------------------------------------------------

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    if not _check_admin():
        return jsonify({"success": False, "message": "権限がありません"}), 403
    result = db.get_settings()
    return jsonify(result)


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    if not _check_admin():
        return jsonify({"success": False, "message": "権限がありません"}), 403
    data = request.get_json(force=True)
    result = db.save_settings(data)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
