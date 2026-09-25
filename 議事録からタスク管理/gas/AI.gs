/**
 * AI.gs — Gemini API を使った音声処理・議事録生成
 *
 * 処理フロー:
 *   1. Drive API で音声ファイルをダウンロード
 *   2. Base64エンコードして inline_data で Gemini に送信（Files API不使用）
 *   3. gemini-2.5-flash で一括生成
 *   4. 結果をシートに保存 → 通知
 *
 * ※ GAS は Content-Length を含むヘッダー名を全てブロックするため
 *    Files API の resumable upload は使用不可。inline_data で回避。
 */

const GEMINI_MODEL = 'gemini-2.5-flash';
const GEMINI_GENERATE_URL = 'https://generativelanguage.googleapis.com/v1beta/models/' + GEMINI_MODEL + ':generateContent';

/** Gemini APIが対応する音声MIMEタイプ */
const SUPPORTED_AUDIO_MIMES = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/aiff', 'audio/aac', 'audio/ogg', 'audio/flac'];

/** DriveのMIMEタイプをGemini対応形式に変換 */
function _normalizeMimeType(driveMime) {
  if (SUPPORTED_AUDIO_MIMES.includes(driveMime)) return driveMime;
  // audio/mp4, audio/x-m4a, video/mp4 等 → audio/aac として送信
  if (driveMime && (driveMime.includes('mp4') || driveMime.includes('m4a'))) return 'audio/aac';
  // audio/x-wav → audio/wav
  if (driveMime && driveMime.includes('wav')) return 'audio/wav';
  // 不明な場合はmp3として試行
  return 'audio/mp3';
}

/**
 * メイン処理エントリポイント（Code.gsから呼び出し）
 */
function processMeeting(meetingId, driveFileId, prevMeetingId) {
  const props = PropertiesService.getScriptProperties();
  const apiKey = props.getProperty('GEMINI_API_KEY');
  if (!apiKey) throw new Error('GEMINI_API_KEY が未設定です');

  logSheet('INFO', 'processMeeting', `処理開始: ${meetingId}`);

  // 1. ファイルサイズチェック（Base64後約1.33倍になるため37MB上限でUrlFetchApp 50MB超を防ぐ）
  const file = DriveApp.getFileById(driveFileId);
  const fileSize = file.getSize();
  const MAX_BYTES = 19 * 1024 * 1024; // inline_data上限20MB（余裕を持って19MB）
  if (fileSize > MAX_BYTES) {
    const msg = `ファイルサイズ超過: ${Math.round(fileSize / 1024 / 1024)}MB（上限37MB）。音声を圧縮・分割してください。`;
    logSheet('ERROR', 'processMeeting', msg);
    updateMeetingStatus(meetingId, 'エラー', '', '{}', '', '[]');
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
    const mimeType = _normalizeMimeType(file.getMimeType());
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
  const candidate = resData.candidates?.[0];
  const finishReason = candidate?.finishReason;
  if (finishReason && finishReason !== 'STOP') {
    throw new Error(`Gemini が処理を拒否しました (finishReason: ${finishReason})`);
  }
  const text = candidate?.content?.parts?.[0]?.text || '{}';

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

// ── ステップ分割関数 ─────────────────────────────────────────────────────────

/**
 * ① 文字起こしのみ実行（音声ファイル → テキスト）
 */
function transcribeAudio(meetingId, driveFileId) {
  const props = PropertiesService.getScriptProperties();
  const apiKey = props.getProperty('GEMINI_API_KEY');
  if (!apiKey) throw new Error('GEMINI_API_KEY が未設定です');

  logSheet('INFO', 'transcribeAudio', `文字起こし開始: ${meetingId}`);

  const file = DriveApp.getFileById(driveFileId);
  const fileSize = file.getSize();
  const MAX_BYTES = 19 * 1024 * 1024; // inline_data上限20MB（余裕を持って19MB）
  if (fileSize > MAX_BYTES) {
    const msg = `ファイルサイズ超過: ${Math.round(fileSize / 1024 / 1024)}MB（上限37MB）`;
    logSheet('ERROR', 'transcribeAudio', msg);
    updateMeetingStatus(meetingId, 'エラー');
    return { meeting_id: meetingId, status: 'エラー' };
  }

  try {
    const token = ScriptApp.getOAuthToken();
    const dlRes = UrlFetchApp.fetch(
      `https://www.googleapis.com/drive/v3/files/${driveFileId}?alt=media`,
      { headers: { Authorization: 'Bearer ' + token }, muteHttpExceptions: true }
    );
    if (dlRes.getResponseCode() !== 200) {
      throw new Error('Driveダウンロード失敗: ' + dlRes.getContentText().substring(0, 200));
    }
    const mimeType = _normalizeMimeType(file.getMimeType());
    const base64Audio = Utilities.base64Encode(dlRes.getContent());

    const transcript = _transcribeWithGemini(apiKey, base64Audio, mimeType);
    updateTranscript(meetingId, transcript);
    logSheet('INFO', 'transcribeAudio', `文字起こし完了: ${meetingId}`);
    return { meeting_id: meetingId, status: '文字起こし完了' };
  } catch (err) {
    logSheet('ERROR', 'transcribeAudio', `エラー: ${err}`);
    updateMeetingStatus(meetingId, 'エラー');
    throw err;
  }
}

/**
 * ② 議事録・タスク生成（シートのtranscriptテキストのみ使用）
 */
function generateMinutesFromTranscript(meetingId, prevMeetingId) {
  const props = PropertiesService.getScriptProperties();
  const apiKey = props.getProperty('GEMINI_API_KEY');
  if (!apiKey) throw new Error('GEMINI_API_KEY が未設定です');

  logSheet('INFO', 'generateMinutesFromTranscript', `議事録生成開始: ${meetingId}`);

  const transcript = _getTranscriptFromSheet(meetingId);
  if (!transcript) throw new Error('文字起こしデータが見つかりません。先に①文字起こしを実行してください。');

  const prevContext = prevMeetingId ? getPrevMeetingContext(prevMeetingId) : '';

  try {
    const minutesJson = _generateMinutesTextOnly(apiKey, transcript, prevContext);
    updateMinutesJson(meetingId, minutesJson);
    logSheet('INFO', 'generateMinutesFromTranscript', `議事録生成完了: ${meetingId}`);
    return { meeting_id: meetingId, status: '文字起こし完了' };
  } catch (err) {
    logSheet('ERROR', 'generateMinutesFromTranscript', `エラー: ${err}`);
    updateMeetingStatus(meetingId, 'エラー');
    throw err;
  }
}

/**
 * ③ フローチャート生成（シートのtranscriptテキストのみ使用）
 */
function generateFlowchartFromTranscript(meetingId) {
  const props = PropertiesService.getScriptProperties();
  const apiKey = props.getProperty('GEMINI_API_KEY');
  if (!apiKey) throw new Error('GEMINI_API_KEY が未設定です');

  logSheet('INFO', 'generateFlowchartFromTranscript', `フロー生成開始: ${meetingId}`);

  const transcript = _getTranscriptFromSheet(meetingId);
  if (!transcript) throw new Error('文字起こしデータが見つかりません。先に①文字起こしを実行してください。');

  try {
    const mermaidCode = _generateFlowchartTextOnly(apiKey, transcript);
    updateMermaidCode(meetingId, mermaidCode);
    logSheet('INFO', 'generateFlowchartFromTranscript', `フロー生成完了: ${meetingId}`);
    return { meeting_id: meetingId, status: '文字起こし完了' };
  } catch (err) {
    logSheet('ERROR', 'generateFlowchartFromTranscript', `エラー: ${err}`);
    updateMeetingStatus(meetingId, 'エラー');
    throw err;
  }
}

/**
 * ④ ガントチャート生成（シートのtranscriptテキストのみ使用）
 */
function generateGanttFromTranscript(meetingId) {
  const props = PropertiesService.getScriptProperties();
  const apiKey = props.getProperty('GEMINI_API_KEY');
  if (!apiKey) throw new Error('GEMINI_API_KEY が未設定です');

  logSheet('INFO', 'generateGanttFromTranscript', `ガント生成開始: ${meetingId}`);

  const transcript = _getTranscriptFromSheet(meetingId);
  if (!transcript) throw new Error('文字起こしデータが見つかりません。先に①文字起こしを実行してください。');

  try {
    const ganttJson = _generateGanttTextOnly(apiKey, transcript);
    updateGanttJson(meetingId, ganttJson);
    logSheet('INFO', 'generateGanttFromTranscript', `ガント生成完了: ${meetingId}`);
    return { meeting_id: meetingId, status: '文字起こし完了' };
  } catch (err) {
    logSheet('ERROR', 'generateGanttFromTranscript', `エラー: ${err}`);
    updateMeetingStatus(meetingId, 'エラー');
    throw err;
  }
}

// ── 内部ヘルパー ─────────────────────────────────────────────────────────────

/**
 * シートから transcript テキストを取得（col6 = index 5）
 */
function _getTranscriptFromSheet(meetingId) {
  const props = PropertiesService.getScriptProperties();
  const ss = SpreadsheetApp.openById(props.getProperty('SPREADSHEET_ID'));
  const sheet = ss.getSheetByName('会議履歴');
  if (!sheet) return '';
  const values = sheet.getDataRange().getValues();
  for (let i = 1; i < values.length; i++) {
    if (values[i][0] === meetingId) return values[i][5] || '';
  }
  return '';
}

/**
 * Gemini で音声 → 文字起こしのみ
 */
function _transcribeWithGemini(apiKey, base64Audio, mimeType) {
  const prompt = `添付の音声ファイルを文字起こししてください。話者が複数いる場合は「話者A:」「話者B:」のように区別してください。JSONではなくテキストのみで出力してください。`;

  const requestBody = {
    contents: [{
      parts: [
        { inline_data: { mime_type: mimeType, data: base64Audio } },
        { text: prompt },
      ]
    }],
    generation_config: { temperature: 0.1 },
  };

  const res = UrlFetchApp.fetch(`${GEMINI_GENERATE_URL}?key=${apiKey}`, {
    method: 'POST',
    contentType: 'application/json',
    payload: JSON.stringify(requestBody),
    muteHttpExceptions: true,
  });

  if (res.getResponseCode() !== 200) {
    throw new Error('Gemini 文字起こしエラー: ' + res.getContentText().substring(0, 500));
  }

  const resData = JSON.parse(res.getContentText());
  return resData.candidates?.[0]?.content?.parts?.[0]?.text || '';
}

/**
 * テキストのみで議事録JSON生成
 */
function _generateMinutesTextOnly(apiKey, transcript, prevContext) {
  const prevSection = prevContext
    ? `\n\n【前回会議の未完了タスク】\n${prevContext}\n上記を今回の議事録に引き継いでください。\n`
    : '';

  const prompt = `あなたは経営者向けの議事録アシスタントです。
以下の文字起こしテキストを分析し、JSONのみを出力してください（前後に余分なテキスト不可）。
${prevSection}
【文字起こし】
${transcript}

【出力形式】
{
  "summary": "会議の要約（3〜5行）",
  "agenda": ["議題1", "議題2"],
  "decisions": ["決定事項1"],
  "priority_tasks": [{"label": "A", "task": "タスク名", "deadline": "期限", "reason": "理由"}],
  "delegate_tasks": [{"task": "タスク名", "detail": "具体的作業内容", "estimated_time": "所要時間目安"}],
  "risks": [{"description": "放置リスクの説明", "consequence": "頓挫する内容"}],
  "carryover_tasks": ["前回からの引き継ぎタスク"]
}`;

  const requestBody = {
    contents: [{ parts: [{ text: prompt }] }],
    generation_config: { response_mime_type: 'application/json', temperature: 0.2 },
  };

  const res = UrlFetchApp.fetch(`${GEMINI_GENERATE_URL}?key=${apiKey}`, {
    method: 'POST',
    contentType: 'application/json',
    payload: JSON.stringify(requestBody),
    muteHttpExceptions: true,
  });

  if (res.getResponseCode() !== 200) {
    throw new Error('Gemini 議事録生成エラー: ' + res.getContentText().substring(0, 500));
  }

  const resData = JSON.parse(res.getContentText());
  const text = resData.candidates?.[0]?.content?.parts?.[0]?.text || '{}';
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (e) {
    const match = text.match(/\{[\s\S]*\}/);
    parsed = match ? JSON.parse(match[0]) : {};
  }
  return JSON.stringify(parsed);
}

/**
 * テキストのみでMermaidフローチャート生成
 */
function _generateFlowchartTextOnly(apiKey, transcript) {
  const prompt = `以下の会議の文字起こしを分析し、意思決定フローをMermaidのflowchart TD形式で出力してください。
Mermaidコードのみを出力し、前後に余分なテキストやコードブロック記法（\`\`\`等）を含めないでください。

【文字起こし】
${transcript}

出力例:
graph TD
  A[開始] --> B[議題1]
  B --> C{判断}
  C -->|Yes| D[決定事項1]
  C -->|No| E[継続検討]`;

  const requestBody = {
    contents: [{ parts: [{ text: prompt }] }],
    generation_config: { temperature: 0.2 },
  };

  const res = UrlFetchApp.fetch(`${GEMINI_GENERATE_URL}?key=${apiKey}`, {
    method: 'POST',
    contentType: 'application/json',
    payload: JSON.stringify(requestBody),
    muteHttpExceptions: true,
  });

  if (res.getResponseCode() !== 200) {
    throw new Error('Gemini フロー生成エラー: ' + res.getContentText().substring(0, 500));
  }

  const resData = JSON.parse(res.getContentText());
  let code = resData.candidates?.[0]?.content?.parts?.[0]?.text || '';
  // コードブロック記法を除去
  code = code.replace(/^```[^\n]*\n?/m, '').replace(/```\s*$/m, '').trim();
  return code;
}

/**
 * テキストのみでガントJSON生成
 */
function _generateGanttTextOnly(apiKey, transcript) {
  const prompt = `以下の会議の文字起こしを分析し、タスク一覧をJSONのみで出力してください（前後に余分なテキスト不可）。

【文字起こし】
${transcript}

【出力形式】
[
  {"task": "タスク名", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "assignee": "担当者", "status": "未着手"}
]`;

  const requestBody = {
    contents: [{ parts: [{ text: prompt }] }],
    generation_config: { response_mime_type: 'application/json', temperature: 0.2 },
  };

  const res = UrlFetchApp.fetch(`${GEMINI_GENERATE_URL}?key=${apiKey}`, {
    method: 'POST',
    contentType: 'application/json',
    payload: JSON.stringify(requestBody),
    muteHttpExceptions: true,
  });

  if (res.getResponseCode() !== 200) {
    throw new Error('Gemini ガント生成エラー: ' + res.getContentText().substring(0, 500));
  }

  const resData = JSON.parse(res.getContentText());
  const text = resData.candidates?.[0]?.content?.parts?.[0]?.text || '[]';
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (e) {
    const match = text.match(/\[[\s\S]*\]/);
    parsed = match ? JSON.parse(match[0]) : [];
  }
  return JSON.stringify(Array.isArray(parsed) ? parsed : []);
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
