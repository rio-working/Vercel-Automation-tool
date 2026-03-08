"""
integrations/drive.py  ─  Google Drive ファイル操作
サービスアカウントで指定フォルダにMarkdownファイルを保存する。

前提: 保存先フォルダをサービスアカウントのメールに共有しておくこと。
"""
import json
import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

from core.logger import log_error

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def _get_drive_service():
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
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
