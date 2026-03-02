import os
import re
from datetime import datetime

import requests
from flask import Flask, jsonify, render_template, request

import db

app = Flask(__name__)



# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

@app.route("/api/trades", methods=["GET"])
def api_get_trades():
    settled_raw = request.args.get("settled")
    broker = request.args.get("broker") or None
    start_date = request.args.get("start_date") or None
    end_date = request.args.get("end_date") or None

    if settled_raw == "true":
        settled = True
    elif settled_raw == "false":
        settled = False
    else:
        settled = None

    trades = db.get_trades(settled, broker, start_date, end_date)
    return jsonify(trades)


@app.route("/api/trades", methods=["POST"])
def api_add_master():
    data = request.get_json(force=True)
    if not data.get("コード"):
        return jsonify({"success": False, "message": "銘柄コードは必須です"}), 400

    if not data.get("銘柄"):
        data["銘柄"] = _get_stock_name(str(data["コード"]))

    result = db.add_master(data)
    return jsonify(result)


@app.route("/api/trades/<int:trade_id>", methods=["PUT"])
def api_update_trade(trade_id):
    data = request.get_json(force=True)
    result = db.update_trade(trade_id, data)
    return jsonify(result)


@app.route("/api/trades/<int:trade_id>", methods=["DELETE"])
def api_delete_trade(trade_id):
    result = db.delete_trade(trade_id)
    return jsonify(result)


# ---------------------------------------------------------------------------
# P&L
# ---------------------------------------------------------------------------

@app.route("/api/pl", methods=["GET"])
def api_pl():
    broker = request.args.get("broker") or None
    start_date = request.args.get("start_date") or None
    end_date = request.args.get("end_date") or None
    result = db.calculate_pl(broker, start_date, end_date)
    return jsonify(result)


@app.route("/api/pl/monthly", methods=["GET"])
def api_monthly_pl():
    year = request.args.get("year", datetime.now().year, type=int)
    result = db.get_monthly_pl(year)
    return jsonify(result)


@app.route("/api/pl/yearly", methods=["GET"])
def api_yearly_pl():
    result = db.get_yearly_pl()
    return jsonify(result)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    result = db.get_settings()
    return jsonify(result)


@app.route("/api/settings", methods=["POST"])
def api_update_settings():
    data = request.get_json(force=True)
    result = db.update_settings(data)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Stock name lookup
# ---------------------------------------------------------------------------

@app.route("/api/stock-name", methods=["GET"])
def api_stock_name():
    code = request.args.get("code", "")
    name = _get_stock_name(code)
    return jsonify({"name": name})


def _get_stock_name(code: str) -> str:
    try:
        stock_code = re.sub(r"\D", "", code)[:4]
        if len(stock_code) != 4:
            return ""
        url = f"https://kabutan.jp/stock/?code={stock_code}"
        resp = requests.get(
            url,
            timeout=5,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if resp.status_code != 200:
            return ""
        match = re.search(r"<title>(.+?)【\d+】", resp.text)
        if match:
            return match.group(1).strip()
        return ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
