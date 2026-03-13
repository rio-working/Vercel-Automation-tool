/**
 * Utils.gs — 共通ユーティリティ（設定シート読み取り用）
 * Agenda.gs / Tasks.gs がカレンダー・タスクリスト選択設定を読み取るために使用する。
 */

function getSpreadsheet() {
  const id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!id) throw new Error('スクリプトプロパティ SPREADSHEET_ID が未設定です');
  return SpreadsheetApp.openById(id);
}

function getSheet(name) {
  const ss = getSpreadsheet();
  const sheet = ss.getSheetByName(name);
  if (!sheet) throw new Error('シートが見つかりません: ' + name);
  return sheet;
}

function getAllValues(sheetName) {
  const sheet = getSheet(sheetName);
  const range = sheet.getDataRange();
  return range.getNumRows() > 0 ? range.getValues() : [];
}

function getSettingsMap() {
  try {
    const rows = getAllValues('設定');
    const map = {};
    for (let i = 1; i < rows.length; i++) {
      if (rows[i] && rows[i][0]) map[rows[i][0]] = String(rows[i][1] || '');
    }
    return map;
  } catch (e) {
    return {};
  }
}
