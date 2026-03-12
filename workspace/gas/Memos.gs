/**
 * Memos.gs — 付箋メモ CRUD
 * シート列: id, content, color, created_at
 */

const MEMOS_SHEET = 'Memos';
const MEMOS_HEADERS = ['id', 'content', 'color', 'created_at'];

function getMemos() {
  ensureHeaders(MEMOS_SHEET, MEMOS_HEADERS);
  const rows = getAllValues(MEMOS_SHEET);
  const result = [];
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i];
    if (!r || !r[0]) continue;
    result.push({
      row: i + 1,
      id: r[0],
      content: r[1],
      color: r[2] || 'yellow',
      created_at: r[3] || '',
    });
  }
  return result;
}

function createMemo(data) {
  ensureHeaders(MEMOS_SHEET, MEMOS_HEADERS);
  const id = shortUuid();
  getSheet(MEMOS_SHEET).appendRow([id, data.content, data.color || 'yellow', nowStr()]);
  return { id };
}

function deleteMemo(row) {
  getSheet(MEMOS_SHEET).deleteRow(row);
  return { success: true };
}
