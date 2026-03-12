/**
 * Links.gs — クイックリンク CRUD
 * シート列: id, title, url, category, created_at, delete_flag
 */

const LINKS_SHEET = 'Links';
const LINKS_HEADERS = ['id', 'title', 'url', 'category', 'created_at', 'delete_flag'];

function getLinks() {
  ensureHeaders(LINKS_SHEET, LINKS_HEADERS);
  const rows = getAllValues(LINKS_SHEET);
  const result = [];
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i];
    if (!r || !r[0]) continue;
    if (r[5] === true || r[5] === 'TRUE') continue;
    result.push({
      row: i + 1,
      id: r[0],
      title: r[1],
      url: r[2],
      category: r[3],
      created_at: r[4] || '',
    });
  }
  return result;
}

function createLink(data) {
  ensureHeaders(LINKS_SHEET, LINKS_HEADERS);
  const id = shortUuid();
  getSheet(LINKS_SHEET).appendRow([id, data.title, data.url, data.category || 'その他', nowStr(), false]);
  gasLogInfo('Links', 'リンク追加: ' + data.title);
  return { id };
}

function deleteLink(row) {
  getSheet(LINKS_SHEET).getRange(row, 6).setValue(true);
  return { success: true };
}
