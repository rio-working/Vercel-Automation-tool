/**
 * Code.gs — Workspace GAS Web App ルーター（Google 系操作のみ）
 *
 * スクリプトプロパティ（Script Properties）に以下を設定すること:
 *   SPREADSHEET_ID       : 設定シート読み取り用スプレッドシートID
 *   API_SECRET_TOKEN     : Vercelと共通のAPIトークン
 *   GOOGLE_CALENDAR_ID   : メインカレンダーID（任意）
 *   GOOGLE_EXTRA_CALENDAR_IDS : 追加カレンダーIDのカンマ区切り（任意）
 *
 * 受け付けるアクション:
 *   getAgenda / getCalendarLists / getTasks / completeTask / getTaskLists / saveToDrive
 *   createTask / updateTask / createEvent / updateEvent
 */

function doGet(e) {
  return handleRequest(e, 'GET');
}

function doPost(e) {
  return handleRequest(e, 'POST');
}

function handleRequest(e, method) {
  try {
    // リクエストパラメータを取得（POST: body JSON / GET: URLパラメータ）
    let params = {};
    if (method === 'POST' && e.postData && e.postData.contents) {
      try { params = JSON.parse(e.postData.contents); } catch (err) {}
    }
    if (e.parameter) {
      for (const k in e.parameter) {
        if (!(k in params)) params[k] = e.parameter[k];
      }
    }

    // 認証チェック
    const secret = PropertiesService.getScriptProperties().getProperty('API_SECRET_TOKEN');
    if (secret && params.token !== secret) {
      return respond({ ok: false, error: '認証エラー' });
    }

    const action = params.action;
    let result;

    switch (action) {
      // ── アジェンダ / カレンダー ────────────
      case 'getAgenda':          result = getAgenda(); break;
      case 'getCalendarLists':   result = getCalendarLists(); break;

      // ── Google Tasks ──────────────────────
      case 'getTasks':      result = getTasks(); break;
      case 'completeTask':  result = completeTask(params.task_id, params.list_id); break;
      case 'getTaskLists':  result = getTaskLists(); break;
      case 'createTask':    result = createTask(params.list_id, params.title, params.due, params.notes); break;
      case 'updateTask':    result = updateTask(params.list_id, params.task_id, params.title, params.due, params.notes); break;

      // ── カレンダー書き込み ──────────────────
      case 'createEvent':   result = createEvent(params.calendar_id, params.title, params.start_time, params.end_time, params.location, params.description); break;
      case 'updateEvent':   result = updateEvent(params.calendar_id, params.event_id, params.title, params.start_time, params.end_time, params.location, params.description); break;

      // ── Drive 保存 ─────────────────────────
      case 'saveToDrive':   result = saveToDrive(params.folder_id, params.date, params.content); break;

      default:
        return respond({ ok: false, error: 'Unknown action: ' + action });
    }

    return respond({ ok: true, data: result });

  } catch (err) {
    return respond({ ok: false, error: err.toString() });
  }
}

function respond(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
