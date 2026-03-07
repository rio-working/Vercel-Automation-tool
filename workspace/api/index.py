"""
api/index.py  ─  Vercel エントリポイント
"""
import sys
import os
import traceback

# Vercel Lambda のルートディレクトリ（/var/task）とその親を両方追加
_here = os.path.dirname(os.path.abspath(__file__))          # /var/task/api
_root = os.path.dirname(_here)                               # /var/task
for _p in [_root, '/var/task']:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from main import handler  # noqa: F401
except Exception as _e:
    # インポート失敗時はエラー内容をレスポンスとして返す
    import json
    _tb = traceback.format_exc()

    def handler(event, context):
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": str(_e),
                "traceback": _tb,
                "sys_path": sys.path,
                "cwd": os.getcwd(),
                "files": os.listdir(_root) if os.path.exists(_root) else []
            })
        }
