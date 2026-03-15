/**
 * AI.gs — Gemini API を使った音声処理・議事録生成
 *
 * 処理フロー:
 *   1. Drive API で音声ファイルをダウンロード
 *   2. Base64エンコードして inline_data で Gemini に送信（Files API不使用）
 *   3. gemini-2.0-flash で一括生成
 *   4. 結果をシートに保存 → 通知
 *
 * ※ GAS は Content-Length を含むヘッダー名を全てブロックするため
 *    Files API の resumable upload は使用不可。inline_data で回避。
 */

const GEMINI_MODEL = 'gemini-2.0-flash';
const GEMINI_GENERATE_URL = 'https://generativelanguage.googleapis.com/v1beta/models/' + GEMINI_MODEL + ':generateContent';

/**
 * メイン処理エントリポイント（Code.gsから呼び出し）
 */
function processMeeting(meetingId, driveFileId, prevMeetingId) {
  const props = PropertiesService.getScriptProperties();
  const apiKey = props.getProperty('GEMINI_API_KEY');
  if (!apiKey) throw new Error('GEMINI_API_KEY が未設定です');

  logSheet('INFO', 'processMeeting', `処理開始: ${meetingId}`);

  // 1. ファイルサイズチェック（UrlFetchApp上限50MBより余裕を持って48MB）
  const file = DriveApp.getFileById(driveFileId);
  const fileSize = file.getSize();
  const MAX_BYTES = 48 * 1024 * 1024;
  if (fileSize > MAX_BYTES) {
    const msg = `ファイルサイズ超過: ${Math.round(fileSize / 1024 / 1024)}MB（上限48MB）。音声を圧縮・分割してください。`;
    logSheet('ERROR', 'processMeeting', msg);
    updateMeetingStatus(meetingId, 'エラー', '', '{}', msg, '[]');
    return { meeting_id: meetingId, status: 'エラー' };
  }

  // 前回会議の未完了タスクを取得
  const prevContext = prevMeetingId ? getPrevMeetingContext(prevMeetingId) : '';

  let transcript = '';
  let minutesJson = '{}';
  let mermaidCode = '';
  let ganttJson = '[]';

  try {
    // 2. Drive API 経由でダウンロード → Base64エンコード
    const token = ScriptApp.getOAuthToken();
    const dlRes = UrlFetchApp.fetch(
      `https://www.googleapis.com/drive/v3/files/${driveFileId}?alt=media`,
      { headers: { Authorization: 'Bearer ' + token }, muteHttpExceptions: true }
    );
    if (dlRes.getResponseCode() !== 200) {
      throw new Error('Driveダウンロード失敗: ' + dlRes.getContentText().substring(0, 200));
    }
    const mimeType = file.getMimeType() || 'audio/mp4';
    const base64Audio = Utilities.base64Encode(dlRes.getContent());
    logSheet('INFO', 'processMeeting', 'Base64エンコード完了。Gemini処理開始...');

    // 3. inline_data で Gemini に直接送信（Files API不使用でContent-Length問題を回避）
    const result = generateMinutes(apiKey, base64Audio, mimeType, prevContext);
    transcript   = result.transcript   || '';
    minutesJson  = result.minutes_json || '{}';
    mermaidCode  = result.mermaid_code || '';
    ganttJson    = result.gantt_json   || '[]';

    logSheet('INFO', 'processMeeting', `AI生成完了: ${meetingId}`);
  } catch (err) {
    logSheet('ERROR', 'processMeeting', `AI処理エラー: ${err}`);
    updateMeetingStatus(meetingId, 'エラー', '', '{}', '', '[]');
    throw err;
  }

  // 4. シートに保存
  updateMeetingResults(meetingId, transcript, minutesJson, mermaidCode, ganttJson);

  // 5. 通知
  try {
    const minutesObj = JSON.parse(minutesJson);
    const summary = minutesObj.summary || '';
    sendNotifications(meetingId, summary);
  } catch (e) {
    logSheet('WARN', 'processMeeting', `通知送信エラー（処理は完了）: ${e}`);
  }

  return { meeting_id: meetingId, status: '完了' };
}

/**
 * Gemini で議事録を一括生成する（inline_data 方式）
 */
function generateMinutes(apiKey, base64Audio, mimeType, prevContext) {
  const prevSection = prevContext
    ? `\n\n【前回会議の未完了タスク】\n${prevContext}\n上記を今回の議事録に引き継いでください。\n`
    : '';

  const prompt = `
あなたは経営者向けの議事録アシスタントです。
添付の音声ファイルを分析し、以下のJSON形式で出力してください。
JSONのみを出力し、前後に余分なテキストを含めないでください。
${prevSection}

{
  "transcript": "音声の文字起こし全文",
  "summary": "会議の要約（3〜5行）",
  "minutes_json": {
    "agenda": ["議題1", "議題2"],
    "decisions": ["決定事項1", "決定事項2"],
    "priority_tasks": [
      {"label": "A", "task": "タスク名", "deadline": "期限", "reason": "理由"}
    ],
    "delegate_tasks": [
      {"task": "タスク名", "detail": "具体的作業内容", "estimated_time": "所要時間目安"}
    ],
    "risks": [
      {"description": "放置リスクの説明", "consequence": "頓挫する内容"}
    ],
    "carryover_tasks": ["前回からの引き継ぎタスク"]
  },
  "mermaid_code": "graph TD\\n  A[開始] --> B[議題1]\\n  B --> C[決定事項]",
  "gantt_json": [
    {"task": "タスク名", "start": "2024-01-01", "end": "2024-01-31", "assignee": "担当者", "status": "未着手"}
  ]
}

放置リスクの検出条件:
- 期日が設定されていないタスク
- 担当者が未定のタスク
- 言及されたが結論が出ていない議題
`;

  const requestBody = {
    contents: [{
      parts: [
        { inline_data: { mime_type: mimeType, data: base64Audio } },
        { text: prompt },
      ]
    }],
    generation_config: {
      response_mime_type: 'application/json',
      temperature: 0.2,
    }
  };

  const res = UrlFetchApp.fetch(`${GEMINI_GENERATE_URL}?key=${apiKey}`, {
    method: 'POST',
    contentType: 'application/json',
    payload: JSON.stringify(requestBody),
    muteHttpExceptions: true,
  });

  if (res.getResponseCode() !== 200) {
    throw new Error('Gemini generateContent エラー: ' + res.getContentText());
  }

  const resData = JSON.parse(res.getContentText());
  const text = resData.candidates?.[0]?.content?.parts?.[0]?.text || '{}';

  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (e) {
    // JSONのみ抽出を試みる
    const match = text.match(/\{[\s\S]*\}/);
    parsed = match ? JSON.parse(match[0]) : {};
  }

  return {
    transcript:   parsed.transcript   || '',
    minutes_json: JSON.stringify(parsed.minutes_json || {}),
    mermaid_code: parsed.mermaid_code || '',
    gantt_json:   JSON.stringify(parsed.gantt_json   || []),
  };
}

/**
 * 前回会議の未完了タスクをテキストで取得
 */
function getPrevMeetingContext(prevMeetingId) {
  try {
    const props = PropertiesService.getScriptProperties();
    const ss = SpreadsheetApp.openById(props.getProperty('SPREADSHEET_ID'));
    const sheet = ss.getSheetByName('会議履歴');
    if (!sheet) return '';

    const values = sheet.getDataRange().getValues();
    for (let i = 1; i < values.length; i++) {
      if (values[i][0] === prevMeetingId) {
        const minutesJson = values[i][6];
        if (!minutesJson) return '';
        const minutes = JSON.parse(minutesJson);
        const tasks = [
          ...(minutes.priority_tasks || []).map(t => `- [${t.label}] ${t.task}`),
          ...(minutes.carryover_tasks || []).map(t => `- ${t}`),
        ];
        return tasks.join('\n');
      }
    }
  } catch (e) {
    logSheet('WARN', 'getPrevMeetingContext', `前回会議取得エラー: ${e}`);
  }
  return '';
}
