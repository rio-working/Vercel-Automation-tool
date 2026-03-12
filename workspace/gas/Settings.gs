/**
 * Settings.gs — 設定シート CRUD
 * シート列: key, value, description
 */

const SETTINGS_SHEET = '設定';
const SETTINGS_HEADERS = ['key', 'value', 'description'];

function getSettings() {
  ensureHeaders(SETTINGS_SHEET, SETTINGS_HEADERS);
  return getSettingsMap();
}

function updateSetting(key, value, description) {
  ensureHeaders(SETTINGS_SHEET, SETTINGS_HEADERS);
  const sheet = getSheet(SETTINGS_SHEET);
  const rows = getAllValues(SETTINGS_SHEET);
  for (let i = 1; i < rows.length; i++) {
    if (rows[i] && rows[i][0] === key) {
      sheet.getRange(i + 1, 2).setValue(value);
      return { success: true };
    }
  }
  sheet.appendRow([key, value, description || '']);
  return { success: true };
}
