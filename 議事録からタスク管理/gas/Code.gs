/**
 * Code.gs — 議事録AI分析ツール GAS Web App ルーター
 *
 * スクリプトプロパティ（Script Properties）に以下を設定すること:
 *   GEMINI_API_KEY       : Gemini API キー
 *   SPREADSHEET_ID       : スプレッドシートID
 *   API_SECRET_TOKEN     : Vercelと共通のAPIトークン
 *   SLACK_WEBHOOK_URL    : Slack通知URL（任意）
 *   NOTIFY_EMAIL         : メール通知先（任意）
 *
 * 受け付けるアクション:
 *   processMeeting  : 音声ファイルをAI処理して議事録・タスク・Mermaidを生成
 */

function doGet(e) {
  return handleRequest(e, 'GET');
}

function doPost(e) {
  return handleRequest(e, 'POST');
}

function handleRequest(e, method) {
  try {
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
      case 'processMeeting':
        result = processMeeting(params.meeting_id, params.drive_file_id, params.prev_meeting_id);
        break;
      default:
        return respond({ ok: false, error: 'Unknown action: ' + action });
    }

    return respond({ ok: true, data: result });

  } catch (err) {
    logSheet('ERROR', 'handleRequest', err.toString());
    return respond({ ok: false, error: err.toString() });
  }
}

function respond(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * onOpen メニュー（エディタ不要で設定変更可能）
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🎙️ 議事録ツール')
    .addItem('⚙️ 設定を開く', 'openSettings')
    .addItem('🧪 設定テスト', 'testSettings')
    .addSeparator()
    .addItem('📋 ログを確認', 'openLogSheet')
    .addToUi();
}

function openSettings() {
  const html = HtmlService.createHtmlOutputFromFile('Settings')
    .setWidth(480).setHeight(520);
  SpreadsheetApp.getUi().showModalDialog(html, '⚙️ 設定');
}

function openLogSheet() {
  const ss = SpreadsheetApp.openById(
    PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID')
  );
  const sheet = ss.getSheetByName('ログ');
  if (sheet) ss.setActiveSheet(sheet);
}

function testSettings() {
  const props = PropertiesService.getScriptProperties();
  const geminiKey = props.getProperty('GEMINI_API_KEY');
  const ssId = props.getProperty('SPREADSHEET_ID');
  const token = props.getProperty('API_SECRET_TOKEN');

  const missing = [];
  if (!geminiKey) missing.push('GEMINI_API_KEY');
  if (!ssId) missing.push('SPREADSHEET_ID');
  if (!token) missing.push('API_SECRET_TOKEN');

  if (missing.length > 0) {
    SpreadsheetApp.getUi().alert('❌ 未設定: ' + missing.join(', '));
  } else {
    SpreadsheetApp.getUi().alert('✅ 必須設定は完了しています');
  }
}

function saveSettings(formData) {
  const props = PropertiesService.getScriptProperties();
  const keys = ['GEMINI_API_KEY', 'SPREADSHEET_ID', 'API_SECRET_TOKEN', 'SLACK_WEBHOOK_URL', 'NOTIFY_EMAIL'];
  keys.forEach(k => {
    if (formData[k] !== undefined && formData[k] !== '') {
      props.setProperty(k, formData[k]);
    }
  });
  return { ok: true };
}

function getSettings() {
  const props = PropertiesService.getScriptProperties();
  return {
    SPREADSHEET_ID:    props.getProperty('SPREADSHEET_ID') || '',
    API_SECRET_TOKEN:  props.getProperty('API_SECRET_TOKEN') || '',
    SLACK_WEBHOOK_URL: props.getProperty('SLACK_WEBHOOK_URL') || '',
    NOTIFY_EMAIL:      props.getProperty('NOTIFY_EMAIL') || '',
    // APIキーはセキュリティ上マスク
    GEMINI_API_KEY:    props.getProperty('GEMINI_API_KEY') ? '****設定済み****' : '',
  };
}
