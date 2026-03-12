/**
 * Announcements.gs — お知らせテロップ
 * シート列: id, content, active, expires_at
 */

const ANN_SHEET = 'Announcements';
const ANN_HEADERS = ['id', 'content', 'active', 'expires_at'];

function getAnnouncements() {
  ensureHeaders(ANN_SHEET, ANN_HEADERS);
  const rows = getAllValues(ANN_SHEET);
  const now = new Date();
  const result = [];
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i];
    if (!r || !r[0]) continue;
    if (r[2] !== true && r[2] !== 'TRUE') continue;
    if (r[3]) {
      try {
        const exp = new Date(r[3]);
        if (exp < now) continue;
      } catch (e) {}
    }
    result.push({ row: i + 1, id: r[0], content: r[1], expires_at: r[3] || '' });
  }
  return result;
}
