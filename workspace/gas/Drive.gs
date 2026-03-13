/**
 * Drive.gs — Google Drive Markdown保存
 * DriveApp を使用（ユーザー認証で動作・サービスアカウント不要）
 */

function saveToDrive(folderId, date, content) {
  if (!folderId) throw new Error('フォルダIDが未設定です');

  const folder = DriveApp.getFolderById(folderId);
  const filename = '日報_' + date + '.md';
  const markdown = [
    '---',
    'date: ' + date,
    'tags: [日報]',
    '---',
    '',
    '# 日報 ' + date,
    '',
    content,
  ].join('\n');

  // 同名ファイルが存在する場合は上書き
  const existing = folder.getFilesByName(filename);
  if (existing.hasNext()) {
    existing.next().setContent(markdown);
  } else {
    folder.createFile(filename, markdown, MimeType.PLAIN_TEXT);
  }

  return { success: true, filename: filename };
}
