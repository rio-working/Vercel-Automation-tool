// =============================================
// Workspace Quick Add - ポップアップ
// =============================================

let gasUrl = '';
let apiToken = '';
let taskListsCache = null;
let calendarListsCache = null;

// 設定読み込み & 初期化
document.addEventListener('DOMContentLoaded', async () => {
  const cfg = await chrome.storage.sync.get(['gasUrl', 'apiToken']);
  gasUrl = cfg.gasUrl || '';
  apiToken = cfg.apiToken || '';

  if (!gasUrl || !apiToken) {
    showStatus('設定画面でGAS URLとトークンを入力してください', 'error');
    return;
  }

  // デフォルト日時を設定
  setDefaultDateTime();

  // リスト・カレンダー一覧を取得
  loadLists();
});

function setDefaultDateTime() {
  const now = new Date();
  now.setMinutes(0, 0, 0);
  now.setHours(now.getHours() + 1);
  const end = new Date(now.getTime() + 60 * 60 * 1000);
  document.getElementById('event-start').value = toLocalIso(now);
  document.getElementById('event-end').value = toLocalIso(end);
}

function toLocalIso(d) {
  const pad = n => String(n).padStart(2, '0');
  return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + 'T' + pad(d.getHours()) + ':' + pad(d.getMinutes());
}

// タブ切り替え
function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.toggle('active', c.id === 'tab-' + tab));
}

// GAS API 呼び出し（Chrome拡張から直接POST）
async function callGas(action, params) {
  const body = Object.assign({ action, token: apiToken }, params || {});
  const res = await fetch(gasUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: JSON.stringify(body),
  });
  const json = await res.json();
  if (!json.ok) throw new Error(json.error || 'GASエラー');
  return json.data;
}

// リスト・カレンダー一覧をロード
async function loadLists() {
  try {
    const [taskLists, calLists] = await Promise.all([
      callGas('getTaskLists'),
      callGas('getCalendarLists'),
    ]);
    taskListsCache = taskLists;
    calendarListsCache = calLists;

    const taskSel = document.getElementById('task-list');
    taskSel.innerHTML = taskLists.map(l => `<option value="${esc(l.id)}">${esc(l.title)}</option>`).join('');

    const calSel = document.getElementById('event-calendar');
    calSel.innerHTML = calLists.map(c => `<option value="${esc(c.id)}">${esc(c.summary)}</option>`).join('');
  } catch (e) {
    showStatus('一覧取得エラー: ' + e.message, 'error');
  }
}

// タスク追加
async function submitTask() {
  const title = document.getElementById('task-title').value.trim();
  if (!title) { showStatus('タイトルを入力してください', 'error'); return; }

  const btn = document.getElementById('task-submit');
  btn.disabled = true;
  btn.textContent = '送信中…';

  try {
    await callGas('createTask', {
      list_id: document.getElementById('task-list').value,
      title,
      due: document.getElementById('task-due').value || null,
      notes: document.getElementById('task-notes').value || '',
    });
    showStatus('タスクを追加しました', 'success');
    document.getElementById('task-title').value = '';
    document.getElementById('task-due').value = '';
    document.getElementById('task-notes').value = '';
  } catch (e) {
    showStatus('エラー: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'タスクを追加';
  }
}

// イベント追加
async function submitEvent() {
  const title = document.getElementById('event-title').value.trim();
  const start = document.getElementById('event-start').value;
  const end = document.getElementById('event-end').value;
  if (!title) { showStatus('タイトルを入力してください', 'error'); return; }
  if (!start || !end) { showStatus('日時を入力してください', 'error'); return; }

  const btn = document.getElementById('event-submit');
  btn.disabled = true;
  btn.textContent = '送信中…';

  try {
    await callGas('createEvent', {
      calendar_id: document.getElementById('event-calendar').value,
      title,
      start_time: start,
      end_time: end,
      location: document.getElementById('event-location').value || '',
      description: document.getElementById('event-description').value || '',
    });
    showStatus('予定を追加しました', 'success');
    document.getElementById('event-title').value = '';
    document.getElementById('event-location').value = '';
    document.getElementById('event-description').value = '';
    setDefaultDateTime();
  } catch (e) {
    showStatus('エラー: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '予定を追加';
  }
}

function showStatus(msg, type) {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = 'status ' + (type || '');
  if (type === 'success') setTimeout(() => { el.textContent = ''; el.className = 'status'; }, 3000);
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
