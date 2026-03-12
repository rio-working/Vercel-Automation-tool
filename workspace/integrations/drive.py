"""
integrations/drive.py  ─  Google Drive ファイル操作
ユーザーの OAuth リフレッシュトークンで指定フォルダにMarkdownファイルを保存する。
サービスアカウントはストレージクォータを持たないため OAuth を使用。

必要な環境変数:
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
  GOOGLE_REFRESH_TOKEN  （drive.file または drive スコープ付きで取得したもの）
"""
import os

import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

from core.logger import log_error


def _get_drive_service():
    """リフレッシュトークンからアクセストークンを取得してDriveサービスを構築する。"""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN", "")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Google Drive用の環境変数が未設定です (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REFRESH_TOKEN)")

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
    access_token = resp.json()["access_token"]

    creds = Credentials(token=access_token)
    return build("drive", "v3", credentials=creds)


def upload_markdown(folder_id: str, filename: str, content: str) -> str:
    """
    Markdownファイルをフォルダにアップロード。
    同名ファイルが既にあれば上書き更新する。
    Returns: Google Drive ファイルID
    """
    try:
        service = _get_drive_service()
        media = MediaInMemoryUpload(
            content.encode("utf-8"),
            mimetype="text/plain",
        )

        # 既存ファイル検索（同名 & 同フォルダ）
        escaped = filename.replace("'", "\\'")
        existing = service.files().list(
            q=f"name='{escaped}' and '{folder_id}' in parents and trashed=false",
            fields="files(id)",
        ).execute().get("files", [])

        if existing:
            file_id = existing[0]["id"]
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            meta = {
                "name": filename,
                "parents": [folder_id],
                "mimeType": "text/plain",
            }
            file_id = service.files().create(
                body=meta, media_body=media, fields="id"
            ).execute()["id"]

        return file_id

    except Exception as e:
        log_error("drive.upload", f"Driveアップロードエラー: {filename}", e)
        raise


def get_service_account_email() -> str:
    """サービスアカウントのメールアドレスを返す（共有設定案内用）。"""
    info = json.loads(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "{}"))
    return info.get("client_email", "")
