const $ = (selector) => document.querySelector(selector);
const statuses = {todo: 'To do', doing: 'In progress', done: 'Done'};
let tasks = [], filter = 'all', editingId = null, deletingId = null, toastTimer;

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options, headers: {'Content-Type': 'application/json', ...options.headers}
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message = Array.isArray(body.detail)
      ? body.detail.map(item => `${item.loc.at(-1)}: ${item.msg}`).join('. ')
      : body.detail;
    throw new Error(message || `Request failed (${response.status}). Please try again.`);
  }
  return response.status === 204 ? null : response.json();
}
function showError(target, error) { target.textContent = error.message; target.hidden = false; }
function toast(message) {
  clearTimeout(toastTimer); $('#toast').textContent = message; $('#toast').hidden = false;
  toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 3500);
}
function element(tag, className, text) {
  const node = document.createElement(tag); node.className = className;
  if (text !== undefined) node.textContent = text; // All user content is text, never HTML.
  return node;
}
function action(label, symbol, handler) {
  const button = element('button', 'icon-button', symbol);
  button.type = 'button'; button.title = label; button.setAttribute('aria-label', label);
  button.addEventListener('click', handler); return button;
}
function render() {
  $('#total').textContent = tasks.length;
  $('#doing').textContent = tasks.filter(t => t.status === 'doing').length;
  $('#done').textContent = tasks.filter(t => t.status === 'done').length;
  $('#nav-count').textContent = $('#filter-count').textContent = tasks.length;
  const query = $('#search').value.trim().toLowerCase();
  const visible = tasks.filter(t => (filter === 'all' || t.status === filter) && `${t.title} ${t.notes}`.toLowerCase().includes(query));
  $('#task-grid').replaceChildren();
  $('#empty').hidden = visible.length > 0;
  $('#empty h3').textContent = tasks.length ? 'A little breathing room.' : 'A fresh start looks good on you.';
  $('#empty p').textContent = tasks.length ? 'No tasks match this view. Try another filter or search.' : 'Add your first task. Give that idea somewhere to go.';
  $('#empty-add').hidden = tasks.length > 0;
  for (const task of visible) {
    const card = element('article', 'task-card');
    const top = element('div', 'card-top');
    top.append(element('span', `status-badge ${task.status}`, statuses[task.status]));
    const actions = element('div', 'card-actions');
    actions.append(action(`Edit ${task.title}`, '✎', () => openEditor(task)), action(`Delete ${task.title}`, '×', () => openDelete(task)));
    top.append(actions);
    card.append(top, element('h3', '', task.title), element('p', '', task.notes || 'A small step in the right direction.'));
    const footer = element('div', 'card-footer');
    footer.append(element('span', `priority ${task.priority}`, `${task.priority[0].toUpperCase()}${task.priority.slice(1)} priority`));
    const complete = element('button', 'complete-button', task.status === 'done' ? '↶ Reopen' : '✓ Mark done');
    complete.setAttribute('aria-label', `${task.status === 'done' ? 'Reopen' : 'Complete'} ${task.title}`);
    complete.addEventListener('click', async () => {
      complete.disabled = true;
      try {
        const {title, notes, priority} = task;
        const updated = await api(`/tasks/${task.id}`, {method: 'PUT', body: JSON.stringify({title, notes, priority, status: task.status === 'done' ? 'todo' : 'done'})});
        tasks = tasks.map(t => t.id === updated.id ? updated : t); render();
        toast(updated.status === 'done' ? 'One more little win. Task completed!' : 'Task reopened. Ready when you are.');
      } catch (error) { showError($('#error'), error); complete.disabled = false; }
    });
    footer.append(complete); card.append(footer); $('#task-grid').append(card);
  }
}
async function load() {
  $('#refresh').disabled = true; $('#error').hidden = true;
  try {
    const [health, records] = await Promise.all([api('/health'), api('/tasks')]);
    tasks = records; render();
    $('#connection').className = 'connection connected';
    $('#connection').replaceChildren(element('i', ''), document.createTextNode('MongoDB connected'));
    $('#db-label').textContent = `${health.database} / ${health.collection} · Saved in MongoDB`;
  } catch (error) {
    showError($('#error'), error); $('#connection').className = 'connection offline';
    $('#connection').textContent = 'Connection unavailable';
  } finally { $('#refresh').disabled = false; }
}
function openEditor(task = null) {
  editingId = task?.id || null; $('#task-form').reset(); $('#form-error').hidden = true;
  $('#dialog-title').textContent = task ? 'A little fine-tuning.' : 'What’s your next step?';
  $('#save').textContent = task ? 'Save changes' : 'Create task';
  if (task) for (const key of ['title', 'notes', 'status', 'priority']) $(`#${key}`).value = task[key];
  $('#task-dialog').showModal(); $('#title').focus();
}
function openDelete(task) {
  deletingId = task.id; $('#delete-description').textContent = `“${task.title}” will be removed from your board.`;
  $('#delete-error').hidden = true; $('#delete-dialog').showModal(); $('#cancel-delete').focus();
}
$('#task-form').addEventListener('submit', async event => {
  event.preventDefault(); $('#form-error').hidden = true;
  const data = Object.fromEntries(new FormData(event.target)); data.title = data.title.trim();
  if (!data.title) { showError($('#form-error'), new Error('Give your task a name.')); $('#title').focus(); return; }
  $('#save').disabled = true;
  try {
    const updated = await api(editingId ? `/tasks/${editingId}` : '/tasks', {method: editingId ? 'PUT' : 'POST', body: JSON.stringify(data)});
    tasks = editingId ? tasks.map(t => t.id === updated.id ? updated : t) : [updated, ...tasks];
    render(); $('#task-dialog').close(); toast(editingId ? 'Changes saved to MongoDB.' : 'Task added. You’re already moving forward.');
  } catch (error) { showError($('#form-error'), error); }
  finally { $('#save').disabled = false; }
});
$('#confirm-delete').addEventListener('click', async () => {
  $('#confirm-delete').disabled = true; $('#delete-error').hidden = true;
  try {
    await api(`/tasks/${deletingId}`, {method: 'DELETE'});
    tasks = tasks.filter(t => t.id !== deletingId); render(); $('#delete-dialog').close(); toast('Task deleted. A little more breathing room.');
  } catch (error) { showError($('#delete-error'), error); }
  finally { $('#confirm-delete').disabled = false; }
});
$('#new-task').addEventListener('click', () => openEditor());
$('#empty-add').addEventListener('click', () => openEditor());
for (const id of ['cancel', 'close-dialog']) $(`#${id}`).addEventListener('click', () => $('#task-dialog').close());
$('#cancel-delete').addEventListener('click', () => $('#delete-dialog').close());
$('#refresh').addEventListener('click', load);
$('#search').addEventListener('input', render);
for (const button of document.querySelectorAll('[data-filter]')) {
  button.addEventListener('click', () => {
    filter = button.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-pressed', String(b === button)); });
    render();
  });
}
$('#board-nav').addEventListener('click', () => {
  filter = 'all'; $('#search').value = ''; $('[data-filter="all"]').click(); window.scrollTo({top: 0, behavior: 'smooth'});
});
load();
