"""
integrations/calendar.py  ─  Google Calendar API 連携
認証: サービスアカウント（GOOGLE_SERVICE_ACCOUNT_JSON）

取得方針:
  - GOOGLE_CALENDAR_ID に指定されたカレンダーを取得
  - 加えて、サービスアカウントにアクセス権があるカレンダーを全件自動集約
  - 重複イベントは id で除外
  - 結果は時刻順ソート（終日イベントは先頭）
"""
import json
import os
from datetime import datetime, timezone, timedelta

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from core.logger import log_error, log_warn

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
JST = timezone(timedelta(hours=9))


def _get_service():
    service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds)


def _fetch_events(service, calendar_id: str, time_min: str, time_max: str) -> list[dict]:
    """指定カレンダーから本日の予定を取得する。"""
    try:
        result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            maxResults=50,
        ).execute()
        return result.get("items", [])
    except Exception as e:
        log_warn("calendar._fetch_events", f"カレンダー取得スキップ [{calendar_id}]: {e}")
        return []


def _item_to_event(item: dict) -> dict:
    """APIレスポンスをフロントエンド向け辞書に変換する。"""
    start = item.get("start", {})
    all_day = "date" in start and "dateTime" not in start

    if all_day:
        time_str = "終日"
        start_dt = None
    else:
        raw = start.get("dateTime", "")
        try:
            dt = datetime.fromisoformat(raw).astimezone(JST)
            time_str = dt.strftime("%H:%M")
            start_dt = dt.isoformat()
        except Exception:
            time_str = raw[:5] if raw else ""
            start_dt = raw

    return {
        "id":          item.get("id", ""),
        "title":       item.get("summary", "（タイトルなし）"),
        "time":        time_str,
        "start":       start_dt,
        "location":    item.get("location", ""),
        "description": item.get("description", ""),
        "all_day":     all_day,
        "html_link":   item.get("htmlLink", ""),
        "calendar_id": item.get("organizer", {}).get("email", ""),
    }


def get_calendar_list() -> list[dict]:
    """環境変数に設定されたカレンダーIDの名称を取得して返す: [{id, summary}, ...]"""
    try:
        service = _get_service()
        cal_ids: list[str] = []

        primary_id = os.environ.get("GOOGLE_CALENDAR_ID", "").strip()
        if primary_id:
            cal_ids.append(primary_id)

        extra = os.environ.get("GOOGLE_EXTRA_CALENDAR_IDS", "")
        for cid in extra.split(","):
            cid = cid.strip()
            if cid and cid not in cal_ids:
                cal_ids.append(cid)

        # SA のカレンダー一覧も追加
        try:
            cal_list = service.calendarList().list().execute()
            for cal in cal_list.get("items", []):
                if cal["id"] not in cal_ids:
                    cal_ids.append(cal["id"])
        except Exception as e:
            log_warn("calendar.get_calendar_list", f"calendarList取得スキップ: {e}")

        result = []
        for cid in cal_ids:
            try:
                cal = service.calendars().get(calendarId=cid).execute()
                result.append({"id": cid, "summary": cal.get("summary", cid)})
            except Exception:
                result.append({"id": cid, "summary": cid})

        return result

    except Exception as e:
        log_error("calendar.get_calendar_list", "カレンダーリスト取得エラー", e)
        raise


def get_today_events(selected_ids: list[str] | None = None) -> list[dict]:
    """本日の予定を集約して返す。
    selected_ids が指定された場合はそのIDのみ、なければ既存の動作（env var + SA全カレンダー）。
    """
    try:
        service = _get_service()

        now_jst = datetime.now(JST)
        day_start = now_jst.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = now_jst.replace(hour=23, minute=59, second=59, microsecond=0)
        time_min  = day_start.isoformat()
        time_max  = day_end.isoformat()

        # 取得対象カレンダーIDを収集
        cal_ids: set[str] = set()

        if selected_ids is not None:
            # selected_ids が指定された場合はそのIDのみ
            for cid in selected_ids:
                if cid:
                    cal_ids.add(cid)
        else:
            # 既存の動作: env var + SA全カレンダー
            primary_id = os.environ.get("GOOGLE_CALENDAR_ID", "").strip()
            if primary_id:
                cal_ids.add(primary_id)

            extra = os.environ.get("GOOGLE_EXTRA_CALENDAR_IDS", "")
            for cid in extra.split(","):
                cid = cid.strip()
                if cid:
                    cal_ids.add(cid)

            try:
                cal_list = service.calendarList().list().execute()
                for cal in cal_list.get("items", []):
                    cal_ids.add(cal["id"])
            except Exception as e:
                log_warn("calendar.get_today_events", f"カレンダー一覧取得スキップ: {e}")

        # 全カレンダーから予定を取得・重複排除
        seen_ids: set[str] = set()
        all_events: list[dict] = []

        for cal_id in cal_ids:
            items = _fetch_events(service, cal_id, time_min, time_max)
            for item in items:
                eid = item.get("id", "")
                if eid and eid in seen_ids:
                    continue
                seen_ids.add(eid)
                all_events.append(_item_to_event(item))

        # 時刻順ソート（終日イベントを先頭、その後 start 昇順）
        def sort_key(e):
            if e["all_day"]:
                return "00:00"
            return e["time"] or "99:99"

        all_events.sort(key=sort_key)
        return all_events

    except Exception as e:
        log_error("calendar.get_today_events", "カレンダー取得エラー", e)
        return []
