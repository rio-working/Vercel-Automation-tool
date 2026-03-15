/**
 * Sheets.gs — スプレッドシート書き込み（会議結果・ステータス更新）
 */

const SHEET_MEETINGS = '会議履歴';
const SHEET_LOGS     = 'ログ';

// 列インデックス（1-based for Sheets API）
const COL_MEETING_ID     = 1;
const COL_PROJECT_ID     = 2;
const COL_NAME           = 3;
const COL_DATE           = 4;
const COL_STATUS         = 5;
const COL_TRANSCRIPT     = 6;
const COL_MINUTES_JSON   = 7;
const COL_MERMAID        = 8;
const COL_GANTT_JSON     = 9;

/**
 * 会議のAI処理結果をシートに保存してステータスを「完了」に更新する
 */
function updateMeetingResults(meetingId, transcript, minutesJson, mermaidCode, ganttJson) {
  const props = PropertiesService.getScriptProperties();
  const ss = SpreadsheetApp.openById(props.getProperty('SPREADSHEET_ID'));
  const sheet = ss.getSheetByName(SHEET_MEETINGS);
  if (!sheet) throw new Error(`シート "${SHEET_MEETINGS}" が見つかりません`);

  const values = sheet.getDataRange().getValues();
  for (let i = 1; i < values.length; i++) {
    if (values[i][0] === meetingId) {
      const rowNum = i + 1;
      sheet.getRange(rowNum, COL_STATUS).setValue('完了');
      sheet.getRange(rowNum, COL_TRANSCRIPT).setValue(transcript.substring(0, 50000));
      sheet.getRange(rowNum, COL_MINUTES_JSON).setValue(minutesJson.substring(0, 50000));
      sheet.getRange(rowNum, COL_MERMAID).setValue(mermaidCode.substring(0, 10000));
      sheet.getRange(rowNum, COL_GANTT_JSON).setValue(ganttJson.substring(0, 50000));
      logSheet('INFO', 'updateMeetingResults', `会議結果保存完了: ${meetingId}`);
      return;
    }
  }
  throw new Error(`会議ID ${meetingId} が見つかりません`);
}

/**
 * 会議のステータスのみ更新（エラー時など）
 */
function updateMeetingStatus(meetingId, status, transcript, minutesJson, mermaidCode, ganttJson) {
  const props = PropertiesService.getScriptProperties();
  const ss = SpreadsheetApp.openById(props.getProperty('SPREADSHEET_ID'));
  const sheet = ss.getSheetByName(SHEET_MEETINGS);
  if (!sheet) return;

  const values = sheet.getDataRange().getValues();
  for (let i = 1; i < values.length; i++) {
    if (values[i][0] === meetingId) {
      const rowNum = i + 1;
      sheet.getRange(rowNum, COL_STATUS).setValue(status);
      if (transcript  !== undefined) sheet.getRange(rowNum, COL_TRANSCRIPT).setValue(transcript);
      if (minutesJson !== undefined) sheet.getRange(rowNum, COL_MINUTES_JSON).setValue(minutesJson);
      if (mermaidCode !== undefined) sheet.getRange(rowNum, COL_MERMAID).setValue(mermaidCode);
      if (ganttJson   !== undefined) sheet.getRange(rowNum, COL_GANTT_JSON).setValue(ganttJson);
      return;
    }
  }
}

/**
 * 文字起こし列のみ更新（ステータスを「文字起こし完了」に変更）
 */
function updateTranscript(meetingId, transcript) {
  const props = PropertiesService.getScriptProperties();
  const ss = SpreadsheetApp.openById(props.getProperty('SPREADSHEET_ID'));
  const sheet = ss.getSheetByName(SHEET_MEETINGS);
  if (!sheet) throw new Error(`シート "${SHEET_MEETINGS}" が見つかりません`);

  const values = sheet.getDataRange().getValues();
  for (let i = 1; i < values.length; i++) {
    if (values[i][0] === meetingId) {
      const rowNum = i + 1;
      sheet.getRange(rowNum, COL_STATUS).setValue('文字起こし完了');
      sheet.getRange(rowNum, COL_TRANSCRIPT).setValue(transcript.substring(0, 50000));
      logSheet('INFO', 'updateTranscript', `文字起こし保存完了: ${meetingId}`);
      return;
    }
  }
  throw new Error(`会議ID ${meetingId} が見つかりません`);
}

/**
 * 議事録JSON列のみ更新（ステータスを「文字起こし完了」に戻す）
 */
function updateMinutesJson(meetingId, minutesJson) {
  const props = PropertiesService.getScriptProperties();
  const ss = SpreadsheetApp.openById(props.getProperty('SPREADSHEET_ID'));
  const sheet = ss.getSheetByName(SHEET_MEETINGS);
  if (!sheet) throw new Error(`シート "${SHEET_MEETINGS}" が見つかりません`);

  const values = sheet.getDataRange().getValues();
  for (let i = 1; i < values.length; i++) {
    if (values[i][0] === meetingId) {
      const rowNum = i + 1;
      sheet.getRange(rowNum, COL_STATUS).setValue('文字起こし完了');
      sheet.getRange(rowNum, COL_MINUTES_JSON).setValue(minutesJson.substring(0, 50000));
      logSheet('INFO', 'updateMinutesJson', `議事録JSON保存完了: ${meetingId}`);
      return;
    }
  }
  throw new Error(`会議ID ${meetingId} が見つかりません`);
}

/**
 * MermaidCode列のみ更新（ステータスを「文字起こし完了」に戻す）
 */
function updateMermaidCode(meetingId, mermaidCode) {
  const props = PropertiesService.getScriptProperties();
  const ss = SpreadsheetApp.openById(props.getProperty('SPREADSHEET_ID'));
  const sheet = ss.getSheetByName(SHEET_MEETINGS);
  if (!sheet) throw new Error(`シート "${SHEET_MEETINGS}" が見つかりません`);

  const values = sheet.getDataRange().getValues();
  for (let i = 1; i < values.length; i++) {
    if (values[i][0] === meetingId) {
      const rowNum = i + 1;
      sheet.getRange(rowNum, COL_STATUS).setValue('文字起こし完了');
      sheet.getRange(rowNum, COL_MERMAID).setValue(mermaidCode.substring(0, 10000));
      logSheet('INFO', 'updateMermaidCode', `MermaidCode保存完了: ${meetingId}`);
      return;
    }
  }
  throw new Error(`会議ID ${meetingId} が見つかりません`);
}

/**
 * ガントJSON列のみ更新（ステータスを「文字起こし完了」に戻す）
 */
function updateGanttJson(meetingId, ganttJson) {
  const props = PropertiesService.getScriptProperties();
  const ss = SpreadsheetApp.openById(props.getProperty('SPREADSHEET_ID'));
  const sheet = ss.getSheetByName(SHEET_MEETINGS);
  if (!sheet) throw new Error(`シート "${SHEET_MEETINGS}" が見つかりません`);

  const values = sheet.getDataRange().getValues();
  for (let i = 1; i < values.length; i++) {
    if (values[i][0] === meetingId) {
      const rowNum = i + 1;
      sheet.getRange(rowNum, COL_STATUS).setValue('文字起こし完了');
      sheet.getRange(rowNum, COL_GANTT_JSON).setValue(ganttJson.substring(0, 50000));
      logSheet('INFO', 'updateGanttJson', `ガントJSON保存完了: ${meetingId}`);
      return;
    }
  }
  throw new Error(`会議ID ${meetingId} が見つかりません`);
}

/**
 * ログシートに記録する
 */
function logSheet(level, source, message) {
  try {
    const props = PropertiesService.getScriptProperties();
    const ssId = props.getProperty('SPREADSHEET_ID');
    if (!ssId) return;

    const ss = SpreadsheetApp.openById(ssId);
    let sheet = ss.getSheetByName(SHEET_LOGS);
    if (!sheet) {
      sheet = ss.insertSheet(SHEET_LOGS);
      sheet.appendRow(['タイムスタンプ', 'レベル', '発生元', 'メッセージ']);
    }

    const now = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd HH:mm:ss');
    sheet.appendRow([now, level, source, message]);

    // ERRORは赤背景
    if (level === 'ERROR') {
      const lastRow = sheet.getLastRow();
      sheet.getRange(lastRow, 1, 1, 4).setBackground('#fecaca');
    }
  } catch (e) {
    console.error('logSheet エラー:', e);
  }
}
