/**
 * Utils.gs — 共通ユーティリティ
 */

function getSpreadsheet() {
  const id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!id) throw new Error('スクリプトプロパティ SPREADSHEET_ID が未設定です');
  return SpreadsheetApp.openById(id);
}

function getSheet(name) {
  const ss = getSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) sheet = ss.insertSheet(name);
  return sheet;
}

function getAllValues(sheetName) {
  const sheet = getSheet(sheetName);
  const range = sheet.getDataRange();
  return range.getNumRows() > 0 ? range.getValues() : [];
}

function ensureHeaders(sheetName, headers) {
  const sheet = getSheet(sheetName);
  const values = getAllValues(sheetName);
  if (!values.length || !values[0] || !values[0][0] || values[0][0] !== headers[0]) {
    if (values.length > 0) {
      sheet.insertRowBefore(1);
    }
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  }
}

function getSettingsMap() {
  const rows = getAllValues('設定');
  const map = {};
  for (let i = 1; i < rows.length; i++) {
    if (rows[i] && rows[i][0]) map[rows[i][0]] = String(rows[i][1] || '');
  }
  return map;
}

function gasLogInfo(source, message) {
  try {
    const sheet = getSheet('ログ');
    const now = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd HH:mm:ss');
    sheet.appendRow([now, 'INFO', source, message]);
  } catch (e) {}
}

function gasLogError(source, message) {
  try {
    const sheet = getSheet('ログ');
    const now = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd HH:mm:ss');
    sheet.appendRow([now, 'ERROR', source, message]);
  } catch (e) {}
}

function shortUuid() {
  return Utilities.getUuid().replace(/-/g, '').substring(0, 8);
}

function nowStr() {
  return Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd HH:mm:ss');
}
