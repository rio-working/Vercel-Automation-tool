/**
 * Code.gs — Workspace GAS Web App ルーター
 *
 * スクリプトプロパティ（Script Properties）に以下を設定すること:
 *   SPREADSHEET_ID       : 対象スプレッドシートのID
 *   API_SECRET_TOKEN     : Vercelと共通のAPIトークン
 *   GOOGLE_CALENDAR_ID   : メインカレンダーID（任意）
 *   GOOGLE_EXTRA_CALENDAR_IDS : 追加カレンダーIDのカンマ区切り（任意）
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
      // ── ToDo ──────────────────────────────
      case 'getTodos':        result = getTodos(); break;
      case 'createTodo':      result = createTodo(params.data); break;
      case 'updateTodo':      result = updateTodo(Number(params.row), params.data); break;
      case 'deleteTodo':      result = deleteTodo(Number(params.row)); break;

      // ── アジェンダ / カレンダー ────────────
      case 'getAgenda':          result = getAgenda(); break;
      case 'getCalendarLists':   result = getCalendarLists(); break;

      // ── Google Tasks ──────────────────────
      case 'getTasks':      result = getTasks(); break;
      case 'completeTask':  result = completeTask(params.task_id, params.list_id); break;
      case 'getTaskLists':  result = getTaskLists(); break;

      // ── 日報 ──────────────────────────────
      case 'getJournals':    result = getJournals(); break;
      case 'createJournal':  result = createJournal(params.data); break;

      // ── リンク ────────────────────────────
      case 'getLinks':    result = getLinks(); break;
      case 'createLink':  result = createLink(params.data); break;
      case 'deleteLink':  result = deleteLink(Number(params.row)); break;

      // ── メモ ──────────────────────────────
      case 'getMemos':    result = getMemos(); break;
      case 'createMemo':  result = createMemo(params.data); break;
      case 'deleteMemo':  result = deleteMemo(Number(params.row)); break;

      // ── お知らせ ──────────────────────────
      case 'getAnnouncements': result = getAnnouncements(); break;

      // ── 設定 ──────────────────────────────
      case 'getSettings':    result = getSettings(); break;
      case 'updateSetting':  result = updateSetting(params.key, params.value, params.description); break;

      // ── ログ ──────────────────────────────
      case 'getLogs': result = getLogs(); break;

      default:
        return respond({ ok: false, error: 'Unknown action: ' + action });
    }

    return respond({ ok: true, data: result });

  } catch (err) {
    try { gasLogError('Router', err.toString()); } catch (e2) {}
    return respond({ ok: false, error: err.toString() });
  }
}

function respond(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
