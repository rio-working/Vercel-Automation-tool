/**
 * AI.gs — Gemini API を使った音声処理・議事録生成
 *
 * 処理フロー:
 *   1. DriveApp で音声ファイル取得
 *   2. Gemini Files API にアップロード（Base64エンコード）
 *   3. gemini-2.0-flash-exp で一括生成
 *   4. 結果をシートに保存 → 通知
 */

const GEMINI_MODEL = 'gemini-2.0-flash-exp';
const GEMINI_FILES_URL = 'https://generativelanguage.googleapis.com/upload/v1beta/files';
const GEMINI_GENERATE_URL = 'https://generativelanguage.googleapis.com/v1beta/models/' + GEMINI_MODEL + ':generateContent';

/**
 * メイン処理エントリポイント（Code.gsから呼び出し）
 */
function processMeeting(meetingId, driveFileId, prevMeetingId) {
  const props = PropertiesService.getScriptProperties();
  const apiKey = props.getProperty('GEMINI_API_KEY');
  if (!apiKey) throw new Error('GEMINI_API_KEY が未設定です');

  logSheet('INFO', 'processMeeting', `処理開始: ${meetingId}`);

  // 前回会議の未完了タスクを取得
  const prevContext = prevMeetingId ? getPrevMeetingContext(prevMeetingId) : '';

  let transcript = '';
  let minutesJson = '{}';
  let mermaidCode = '';
  let ganttJson = '[]';

  try {
    // 1. Drive からファイル取得
    const file = DriveApp.getFileById(driveFileId);
    const blob = file.getBlob();
    const mimeType = blob.getContentType();
    const fileBytes = blob.getBytes();

    // 2. Gemini Files API にアップロード
    const fileUri = uploadToGeminiFiles(apiKey, fileBytes, mimeType, file.getName());
    logSheet('INFO', 'processMeeting', `Geminiファイルアップロード完了: ${fileUri}`);

    // 3. Gemini で文字起こし + 議事録生成
    const result = generateMinutes(apiKey, fileUri, mimeType, prevContext);
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
 * Gemini Files API にファイルをアップロードして URI を返す
 */
function uploadToGeminiFiles(apiKey, fileBytes, mimeType, displayName) {
  // multipart/form-data でアップロード
  const boundary = 'gemini_boundary_' + Date.now();

  const metaJson = JSON.stringify({
    file: { display_name: displayName, mime_type: mimeType }
  });

  // バイト列をBase64に変換してBlobで送信
  const base64Data = Utilities.base64Encode(fileBytes);
  const fileBlob = Utilities.newBlob(Utilities.base64Decode(base64Data), mimeType, displayName);

  // resumable upload を使う（大きなファイル対応）
  const initRes = UrlFetchApp.fetch(`${GEMINI_FILES_URL}?key=${apiKey}`, {
    method: 'POST',
    headers: {
      'X-Goog-Upload-Protocol': 'resumable',
      'X-Goog-Upload-Command': 'start',
      'X-Goog-Upload-Header-Content-Length': fileBytes.length,
      'X-Goog-Upload-Header-Content-Type': mimeType,
      'Content-Type': 'application/json',
    },
    payload: metaJson,
    muteHttpExceptions: true,
  });

  const uploadUrl = initRes.getHeaders()['x-goog-upload-url'];
  if (!uploadUrl) {
    throw new Error('Gemini Files API: アップロードURL取得失敗 ' + initRes.getContentText());
  }

  // データ送信
  const uploadRes = UrlFetchApp.fetch(uploadUrl, {
    method: 'POST',
    headers: {
      'Content-Length': fileBytes.length,
      'X-Goog-Upload-Offset': 0,
      'X-Goog-Upload-Command': 'upload, finalize',
    },
    payload: fileBlob.getBytes(),
    muteHttpExceptions: true,
  });

  const uploadData = JSON.parse(uploadRes.getContentText());
  const fileUri = uploadData.file && uploadData.file.uri;
  if (!fileUri) {
    throw new Error('Gemini Files API: ファイルURI取得失敗 ' + uploadRes.getContentText());
  }
  return fileUri;
}

/**
 * Gemini で議事録を一括生成する
 */
function generateMinutes(apiKey, fileUri, mimeType, prevContext) {
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
        { file_data: { mime_type: mimeType, file_uri: fileUri } },
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
