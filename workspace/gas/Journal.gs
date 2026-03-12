/**
 * Journal.gs — 日報 CRUD + Google Drive 保存
 * シート列: id, date, content, auto_summary, created_at
 */

const JOURNAL_SHEET = 'Journal';
const JOURNAL_HEADERS = ['id', 'date', 'content', 'auto_summary', 'created_at'];

function getJournals() {
  ensureHeaders(JOURNAL_SHEET, JOURNAL_HEADERS);
  const rows = getAllValues(JOURNAL_SHEET);
  const result = [];
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i];
    if (!r || !r[0]) continue;
    result.push({
      row: i + 1,
      id: r[0],
      date: r[1] ? Utilities.formatDate(new Date(r[1]), 'Asia/Tokyo', 'yyyy-MM-dd') : '',
      content: r[2],
      auto_summary: r[3],
      created_at: r[4] || '',
    });
  }
  result.reverse();
  return result;
}

function createJournal(data) {
  ensureHeaders(JOURNAL_SHEET, JOURNAL_HEADERS);
  const id = shortUuid();
  getSheet(JOURNAL_SHEET).appendRow([id, data.date, data.content, data.auto_summary || '', nowStr()]);
  gasLogInfo('Journal', '日報保存: ' + data.date);

  // Google Drive 保存
  let driveFileId = null;
  let driveError = null;
  try {
    const settings = getSettingsMap();
    const folderId = settings['journal_drive_folder_id'];
    if (folderId) {
      const md = buildJournalMarkdown(data.date, data.content);
      const filename = '日報_' + data.date + '.md';
      driveFileId = saveMarkdownToDrive(folderId, filename, md);
      gasLogInfo('Journal', 'Drive保存: ' + filename);
    }
  } catch (e) {
    driveError = e.toString();
    gasLogError('Journal', 'Drive保存エラー: ' + e);
  }

  return { id, drive_file_id: driveFileId, drive_error: driveError };
}

function buildJournalMarkdown(date, content) {
  return '---\ndate: ' + date + '\ntags: [日報]\n---\n\n# 日報 ' + date + '\n\n' + content + '\n';
}

function saveMarkdownToDrive(folderId, filename, content) {
  const folder = DriveApp.getFolderById(folderId);
  const files = folder.getFilesByName(filename);
  if (files.hasNext()) {
    const file = files.next();
    file.setContent(content);
    return file.getId();
  }
  const file = folder.createFile(filename, content, MimeType.PLAIN_TEXT);
  return file.getId();
}
