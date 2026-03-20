/**
 * Tasks.gs — Google Tasks 取得・完了
 * Tasks 上級サービスを使用（appsscript.json で有効化済み）
 */

function getTasks() {
  const today = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd');

  // 設定から選択済みリストIDを取得
  let listIds = null;
  try {
    const settings = getSettingsMap();
    const raw = settings['task_selected_lists'];
    if (raw) listIds = JSON.parse(raw);
  } catch (e) {}

  const allLists = (Tasks.Tasklists.list().items) || [];
  const targetLists = listIds
    ? allLists.filter(l => listIds.includes(l.id))
    : allLists;

  const result = [];
  targetLists.forEach(list => {
    const resp = Tasks.Tasks.list(list.id, { showCompleted: false, showHidden: false, maxResults: 20 });
    const items = resp.items || [];
    items.forEach(task => {
      const due = task.due ? task.due.substring(0, 10) : '';
      result.push({
        id:       task.id,
        title:    task.title || '',
        due:      due,
        is_today: due === today,
        notes:    task.notes || '',
        list_id:  list.id,
      });
    });
  });

  return result;
}

function completeTask(taskId, listId) {
  if (listId) {
    Tasks.Tasks.patch({ status: 'completed' }, listId, taskId);
  } else {
    const allLists = (Tasks.Tasklists.list().items) || [];
    for (const list of allLists) {
      try {
        Tasks.Tasks.patch({ status: 'completed' }, list.id, taskId);
        break;
      } catch (e) {}
    }
  }
  return { success: true };
}

function getTaskLists() {
  const lists = (Tasks.Tasklists.list().items) || [];
  return lists.map(l => ({ id: l.id, title: l.title }));
}

function createTask(listId, title, due, notes) {
  const task = { title: title };
  if (due) task.due = new Date(due).toISOString();
  if (notes) task.notes = notes;
  const created = Tasks.Tasks.insert(task, listId);
  return { id: created.id, title: created.title };
}

function updateTask(listId, taskId, title, due, notes) {
  const resource = {};
  if (title !== undefined) resource.title = title;
  if (due !== undefined) resource.due = due ? new Date(due).toISOString() : null;
  if (notes !== undefined) resource.notes = notes;
  Tasks.Tasks.patch(resource, listId, taskId);
  return { success: true };
}
