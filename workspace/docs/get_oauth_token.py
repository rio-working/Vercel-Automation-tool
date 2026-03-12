"""
get_oauth_token.py
==================
Google Tasks + Google Drive のリフレッシュトークンを取得するスクリプト。

【実行方法】
  python docs/get_oauth_token.py

【事前準備】
  - GOOGLE_CLIENT_ID と GOOGLE_CLIENT_SECRET を環境変数にセットするか、
    下記 CLIENT_ID / CLIENT_SECRET に直接入力してください。

【出力】
  GOOGLE_REFRESH_TOKEN の値が表示されます。
  Vercel の環境変数 GOOGLE_REFRESH_TOKEN を新しい値に更新してください。
"""

import os
import urllib.parse
import urllib.request
import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── 認証情報（環境変数 → なければ対話入力） ───────────────────
CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
REDIRECT_URI  = "http://localhost:8765/callback"

# ── 必要なスコープ ─────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/drive.file",
]

# ─────────────────────────────────────────────────────────────
if not CLIENT_ID:
    CLIENT_ID = input("GOOGLE_CLIENT_ID を入力してください: ").strip()
if not CLIENT_SECRET:
    CLIENT_SECRET = input("GOOGLE_CLIENT_SECRET を入力してください: ").strip()

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: CLIENT_ID / CLIENT_SECRET が空です。")
    exit(1)

auth_code_holder = []

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [""])[0]
        if code:
            auth_code_holder.append(code)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h2>認証完了 ✅ このタブを閉じてください。</h2>".encode())
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args):
        pass  # サーバーログを非表示

# 認証 URL を生成してブラウザを開く
params = urllib.parse.urlencode({
    "client_id":     CLIENT_ID,
    "redirect_uri":  REDIRECT_URI,
    "response_type": "code",
    "scope":         " ".join(SCOPES),
    "access_type":   "offline",
    "prompt":        "consent",   # 必ず新しいリフレッシュトークンを発行
})
auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{params}"

print("ブラウザで認証画面を開きます...")
webbrowser.open(auth_url)

# ローカルサーバーでコールバックを待つ
server = HTTPServer(("localhost", 8765), CallbackHandler)
server.handle_request()

if not auth_code_holder:
    print("ERROR: 認証コードを取得できませんでした。")
    exit(1)

# 認証コードをリフレッシュトークンに交換
data = urllib.parse.urlencode({
    "code":          auth_code_holder[0],
    "client_id":     CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri":  REDIRECT_URI,
    "grant_type":    "authorization_code",
}).encode()

req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
with urllib.request.urlopen(req) as resp:
    token_data = json.loads(resp.read())

refresh_token = token_data.get("refresh_token", "")
if not refresh_token:
    print("ERROR: リフレッシュトークンを取得できませんでした。")
    print(token_data)
    exit(1)

print()
print("=" * 60)
print("✅ リフレッシュトークンを取得しました")
print("=" * 60)
print()
print("【Vercel 環境変数に設定する値】")
print(f"GOOGLE_REFRESH_TOKEN = {refresh_token}")
print()
print("Vercel ダッシュボード → Settings → Environment Variables で")
print("GOOGLE_REFRESH_TOKEN を上記の値に更新してください。")
print("更新後は Vercel の Redeploy（または次回プッシュ）で反映されます。")
