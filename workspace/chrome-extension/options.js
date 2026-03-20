// =============================================
// Workspace Quick Add - 設定画面
// =============================================

document.addEventListener('DOMContentLoaded', async () => {
  const cfg = await chrome.storage.sync.get(['gasUrl', 'apiToken']);
  document.getElementById('gas-url').value = cfg.gasUrl || '';
  document.getElementById('api-token').value = cfg.apiToken || '';
});

async function save() {
  const gasUrl = document.getElementById('gas-url').value.trim();
  const apiToken = document.getElementById('api-token').value.trim();

  if (!gasUrl || !apiToken) {
    showStatus('両方の項目を入力してください', 'error');
    return;
  }

  await chrome.storage.sync.set({ gasUrl, apiToken });
  showStatus('保存しました', 'success');
}

async function testConnection() {
  const gasUrl = document.getElementById('gas-url').value.trim();
  const apiToken = document.getElementById('api-token').value.trim();

  if (!gasUrl || !apiToken) {
    showStatus('両方の項目を入力してください', 'error');
    return;
  }

  showStatus('テスト中…', '');

  try {
    const res = await fetch(gasUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: JSON.stringify({ action: 'getTaskLists', token: apiToken }),
    });
    const json = await res.json();
    if (json.ok) {
      const count = (json.data || []).length;
      showStatus('接続成功! タスクリスト ' + count + '件 取得', 'success');
    } else {
      showStatus('エラー: ' + (json.error || '不明なエラー'), 'error');
    }
  } catch (e) {
    showStatus('接続エラー: ' + e.message, 'error');
  }
}

function showStatus(msg, type) {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = 'status ' + (type || '');
}
