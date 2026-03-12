/**
 * Todos.gs — ToDo CRUD
 * シート列: id, content, priority, effort, completed, delete_flag, created_at
 */

const TODO_SHEET = 'Todos';
const TODO_HEADERS = ['id', 'content', 'priority', 'effort', 'completed', 'delete_flag', 'created_at'];

function getTodos() {
  ensureHeaders(TODO_SHEET, TODO_HEADERS);
  const rows = getAllValues(TODO_SHEET);
  const result = [];
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i];
    if (!r || !r[0]) continue;
    if (r[5] === true || r[5] === 'TRUE') continue;
    result.push({
      row: i + 1,
      id: r[0],
      content: r[1],
      priority: r[2],
      effort: r[3],
      completed: r[4] === true || r[4] === 'TRUE',
      created_at: r[6] || '',
    });
  }
  return result;
}

function createTodo(data) {
  ensureHeaders(TODO_SHEET, TODO_HEADERS);
  const id = shortUuid();
  getSheet(TODO_SHEET).appendRow([id, data.content, data.priority || '中', data.effort || '中', false, false, nowStr()]);
  gasLogInfo('Todos', 'ToDo追加: ' + data.content);
  return { id };
}

function updateTodo(row, data) {
  const sheet = getSheet(TODO_SHEET);
  const r = sheet.getRange(row, 1, 1, 7).getValues()[0];
  if (data.content   !== undefined) r[1] = data.content;
  if (data.priority  !== undefined) r[2] = data.priority;
  if (data.effort    !== undefined) r[3] = data.effort;
  if (data.completed !== undefined) r[4] = data.completed;
  sheet.getRange(row, 1, 1, 7).setValues([r]);
  return { success: true };
}

function deleteTodo(row) {
  getSheet(TODO_SHEET).getRange(row, 6).setValue(true);
  return { success: true };
}
