/**
 * Logs.gs — ログ一覧取得
 * シート列: タイムスタンプ, レベル, 発生元, メッセージ
 */

const LOG_SHEET = 'ログ';

function getLogs() {
  const rows = getAllValues(LOG_SHEET);
  if (rows.length <= 1) return [];
  const result = rows.slice(1)
    .filter(r => r && r[0])
    .map(r => ({
      timestamp: r[0] ? String(r[0]) : '',
      level: r[1] || '',
      source: r[2] || '',
      message: r[3] || '',
    }));
  return result.slice(-100).reverse();
}
