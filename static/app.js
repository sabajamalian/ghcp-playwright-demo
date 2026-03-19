// ── State ────────────────────────────────────────────────────────
let lists = [];
let activeListId = null;

// ── DOM refs ────────────────────────────────────────────────────
const listNav = document.getElementById("list-nav");
const sidebarEmpty = document.getElementById("sidebar-empty");
const noSelection = document.getElementById("no-selection");
const taskView = document.getElementById("task-view");
const taskListEl = document.getElementById("task-list");
const taskListName = document.getElementById("task-list-name");
const taskCountBadge = document.getElementById("task-count-badge");
const tasksEmpty = document.getElementById("tasks-empty");

const newListInput = document.getElementById("new-list-input");
const addListBtn = document.getElementById("add-list-btn");
const newTaskInput = document.getElementById("new-task-input");
const addTaskBtn = document.getElementById("add-task-btn");

const renameDialog = document.getElementById("rename-dialog");
const renameInput = document.getElementById("rename-input");
const renameConfirmBtn = document.getElementById("rename-confirm-btn");
const renameCancelBtn = document.getElementById("rename-cancel-btn");
const renameListBtn = document.getElementById("rename-list-btn");

const deleteDialog = document.getElementById("delete-dialog");
const deleteListNameEl = document.getElementById("delete-list-name");
const deleteConfirmBtn = document.getElementById("delete-confirm-btn");
const deleteCancelBtn = document.getElementById("delete-cancel-btn");
const deleteListBtn = document.getElementById("delete-list-btn");

// ── API helpers ─────────────────────────────────────────────────
async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 204) return null;
  return res.json();
}

// ── Fetch & Render ──────────────────────────────────────────────
async function loadLists() {
  lists = await api("/api/lists");
  renderSidebar();

  if (activeListId) {
    const stillExists = lists.find((l) => l.id === activeListId);
    if (stillExists) {
      renderTasks(stillExists);
    } else {
      activeListId = null;
      showNoSelection();
    }
  }
}

function renderSidebar() {
  listNav.innerHTML = "";
  sidebarEmpty.classList.toggle("hidden", lists.length > 0);

  lists.forEach((list) => {
    const btn = document.createElement("button");
    btn.className = "list-item" + (list.id === activeListId ? " active" : "");
    btn.dataset.id = list.id;

    const pending = list.tasks.filter((t) => !t.completed).length;

    btn.innerHTML =
      '<sl-icon name="list-ul"></sl-icon>' +
      '<span class="list-name">' + escapeHtml(list.name) + "</span>" +
      '<span class="task-count">' + pending + "</span>";

    btn.addEventListener("click", () => selectList(list.id));
    listNav.appendChild(btn);
  });
}

function selectList(id) {
  activeListId = id;
  const list = lists.find((l) => l.id === id);
  if (!list) return;
  renderSidebar();
  renderTasks(list);
}

function renderTasks(list) {
  noSelection.classList.add("hidden");
  taskView.classList.remove("hidden");

  taskListName.textContent = list.name;
  const pending = list.tasks.filter((t) => !t.completed).length;
  const total = list.tasks.length;
  taskCountBadge.textContent = pending + " / " + total;

  taskListEl.innerHTML = "";
  tasksEmpty.classList.toggle("hidden", list.tasks.length > 0);

  list.tasks.forEach((task) => {
    const li = document.createElement("li");
    li.className = "task-item";
    li.dataset.id = task.id;

    const checkbox = document.createElement("sl-checkbox");
    checkbox.checked = task.completed;
    checkbox.addEventListener("sl-change", () => toggleTask(list.id, task.id, !task.completed));

    const title = document.createElement("span");
    title.className = "task-title" + (task.completed ? " completed" : "");
    title.textContent = task.title;

    const deleteBtn = document.createElement("sl-icon-button");
    deleteBtn.setAttribute("name", "x-lg");
    deleteBtn.setAttribute("label", "Delete task");
    deleteBtn.addEventListener("click", () => removeTask(list.id, task.id, li));

    li.appendChild(checkbox);
    li.appendChild(title);
    li.appendChild(deleteBtn);
    taskListEl.appendChild(li);
  });
}

function showNoSelection() {
  taskView.classList.add("hidden");
  noSelection.classList.remove("hidden");
}

// ── List actions ────────────────────────────────────────────────
async function addList() {
  const name = newListInput.value.trim();
  if (!name) {
    newListInput.focus();
    return;
  }
  await api("/api/lists", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  newListInput.value = "";
  await loadLists();
  // auto-select the newest list
  if (lists.length > 0) {
    selectList(lists[lists.length - 1].id);
  }
}

addListBtn.addEventListener("click", addList);
newListInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") addList();
});

// Rename
renameListBtn.addEventListener("click", () => {
  const list = lists.find((l) => l.id === activeListId);
  if (!list) return;
  renameInput.value = list.name;
  renameDialog.show();
  setTimeout(() => {
    renameInput.focus();
    renameInput.select();
  }, 100);
});

renameCancelBtn.addEventListener("click", () => renameDialog.hide());

renameConfirmBtn.addEventListener("click", async () => {
  const name = renameInput.value.trim();
  if (!name) return;
  await api("/api/lists/" + activeListId, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
  renameDialog.hide();
  await loadLists();
});

renameInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") renameConfirmBtn.click();
});

// Delete
deleteListBtn.addEventListener("click", () => {
  const list = lists.find((l) => l.id === activeListId);
  if (!list) return;
  deleteListNameEl.textContent = list.name;
  deleteDialog.show();
});

deleteCancelBtn.addEventListener("click", () => deleteDialog.hide());

deleteConfirmBtn.addEventListener("click", async () => {
  await api("/api/lists/" + activeListId, { method: "DELETE" });
  deleteDialog.hide();
  activeListId = null;
  showNoSelection();
  await loadLists();
});

// ── Task actions ────────────────────────────────────────────────
async function addTask() {
  const title = newTaskInput.value.trim();
  if (!title || !activeListId) {
    newTaskInput.focus();
    return;
  }
  await api("/api/lists/" + activeListId + "/tasks", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
  newTaskInput.value = "";
  await loadLists();
  newTaskInput.focus();
}

addTaskBtn.addEventListener("click", addTask);
newTaskInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") addTask();
});

async function toggleTask(listId, taskId, completed) {
  await api("/api/lists/" + listId + "/tasks/" + taskId, {
    method: "PUT",
    body: JSON.stringify({ completed }),
  });
  await loadLists();
}

async function removeTask(listId, taskId, liElement) {
  liElement.classList.add("removing");
  await new Promise((r) => setTimeout(r, 250));
  await api("/api/lists/" + listId + "/tasks/" + taskId, { method: "DELETE" });
  await loadLists();
}

// ── Utilities ───────────────────────────────────────────────────
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ── Init ────────────────────────────────────────────────────────
loadLists();
