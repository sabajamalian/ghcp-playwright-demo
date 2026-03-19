import { test, expect, Page, Locator } from "@playwright/test";

function slInput(page: Page, selector: string): Locator {
  return page.locator(`${selector} input`);
}

async function expectSlInputValue(page: Page, selector: string, expected: string) {
  await expect(page.locator(selector)).toHaveJSProperty("value", expected);
}

// Reset data and create a single list, then select it
async function setupSingleList(page: Page, listName = "Test List") {
  const lists = await page.evaluate(async () => {
    const res = await fetch("/api/lists");
    return res.json();
  });
  for (const list of lists) {
    await page.evaluate(async (id) => {
      await fetch(`/api/lists/${id}`, { method: "DELETE" });
    }, list.id);
  }

  await page.evaluate(async (name) => {
    await fetch("/api/lists", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
  }, listName);

  await page.reload();
  await page.waitForLoadState("networkidle");

  // Select the list
  await page.locator("#list-nav button").filter({ hasText: listName }).click();
  await page.waitForLoadState("networkidle");
}

test.describe("Task Management", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("adds a task via button click", async ({ page }) => {
    await setupSingleList(page);

    await slInput(page, "#new-task-input").fill("Buy groceries");
    await page.getByRole("button", { name: "Add", exact: true }).click();

    await page.waitForResponse((res) => res.url().includes("/tasks") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    // Task appears in list
    const taskItem = page.locator(".task-item").filter({ hasText: "Buy groceries" });
    await expect(taskItem).toBeVisible();

    // Checkbox is unchecked
    await expect(taskItem.locator("sl-checkbox")).toHaveJSProperty("checked", false);

    // Badge updates
    await expect(page.locator("#task-count-badge")).toHaveText("1 / 1");

    // Input is cleared
    await expectSlInputValue(page, "#new-task-input", "");

    // Sidebar count updates
    await expect(page.locator("#list-nav button.active")).toContainText("1");
  });

  test("adds a task via Enter key", async ({ page }) => {
    await setupSingleList(page);

    await slInput(page, "#new-task-input").fill("Keyboard task");
    await slInput(page, "#new-task-input").press("Enter");

    await page.waitForResponse((res) => res.url().includes("/tasks") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    await expect(page.locator(".task-item").filter({ hasText: "Keyboard task" })).toBeVisible();
  });

  test("does not add a task with empty title", async ({ page }) => {
    await setupSingleList(page);

    await slInput(page, "#new-task-input").fill("   ");
    await page.getByRole("button", { name: "Add", exact: true }).click();

    await expect(page.locator(".task-item")).toHaveCount(0);
    await expect(page.locator("#tasks-empty")).toBeVisible();
  });

  test("adds multiple tasks", async ({ page }) => {
    await setupSingleList(page);

    const tasks = ["Task A", "Task B", "Task C"];
    for (const title of tasks) {
      await slInput(page, "#new-task-input").fill(title);
      await page.getByRole("button", { name: "Add", exact: true }).click();
      await page.waitForResponse((res) => res.url().includes("/tasks") && res.status() === 201);
      await page.waitForLoadState("networkidle");
    }

    await expect(page.locator(".task-item")).toHaveCount(3);
    await expect(page.locator("#task-count-badge")).toHaveText("3 / 3");

    for (const title of tasks) {
      await expect(page.locator(".task-item").filter({ hasText: title })).toBeVisible();
    }
  });

  test("toggles task to completed", async ({ page }) => {
    await setupSingleList(page);

    await slInput(page, "#new-task-input").fill("Toggle me");
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await page.waitForResponse((res) => res.url().includes("/tasks") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    await expect(page.locator("#task-count-badge")).toHaveText("1 / 1");

    // Click checkbox to complete
    const taskItem = page.locator(".task-item").filter({ hasText: "Toggle me" });
    await taskItem.locator("sl-checkbox").click();

    await page.waitForResponse((res) => res.url().includes("/tasks/") && res.request().method() === "PUT");
    await page.waitForLoadState("networkidle");

    await expect(taskItem.locator("sl-checkbox")).toHaveJSProperty("checked", true);
    await expect(taskItem.locator(".task-title")).toHaveClass(/completed/);
    await expect(page.locator("#task-count-badge")).toHaveText("0 / 1");
    await expect(page.locator("#list-nav button.active")).toContainText("0");
  });

  test("toggles task back to uncompleted", async ({ page }) => {
    await setupSingleList(page);

    await slInput(page, "#new-task-input").fill("Toggle back");
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await page.waitForResponse((res) => res.url().includes("/tasks") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    const taskItem = page.locator(".task-item").filter({ hasText: "Toggle back" });

    // Complete it
    await taskItem.locator("sl-checkbox").click();
    await page.waitForResponse((res) => res.url().includes("/tasks/") && res.request().method() === "PUT");
    await page.waitForLoadState("networkidle");
    await expect(taskItem.locator("sl-checkbox")).toHaveJSProperty("checked", true);

    // Uncomplete it
    await taskItem.locator("sl-checkbox").click();
    await page.waitForResponse((res) => res.url().includes("/tasks/") && res.request().method() === "PUT");
    await page.waitForLoadState("networkidle");

    await expect(taskItem.locator("sl-checkbox")).toHaveJSProperty("checked", false);
    await expect(taskItem.locator(".task-title")).not.toHaveClass(/completed/);
    await expect(page.locator("#task-count-badge")).toHaveText("1 / 1");
  });

  test("deletes a task", async ({ page }) => {
    await setupSingleList(page);

    await slInput(page, "#new-task-input").fill("Delete me");
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await page.waitForResponse((res) => res.url().includes("/tasks") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    await expect(page.locator(".task-item")).toHaveCount(1);

    const taskItem = page.locator(".task-item").filter({ hasText: "Delete me" });
    await taskItem.getByRole("button", { name: "Delete task" }).click();

    await page.waitForResponse((res) => res.url().includes("/tasks/") && res.request().method() === "DELETE");
    await page.waitForLoadState("networkidle");

    await expect(page.locator(".task-item")).toHaveCount(0);
    await expect(page.locator("#task-count-badge")).toHaveText("0 / 0");
    await expect(page.locator("#tasks-empty")).toBeVisible();
  });

  test("deletes one task while others remain", async ({ page }) => {
    await setupSingleList(page);

    for (const name of ["Keep me", "Remove me"]) {
      await slInput(page, "#new-task-input").fill(name);
      await page.getByRole("button", { name: "Add", exact: true }).click();
      await page.waitForResponse((res) => res.url().includes("/tasks") && res.status() === 201);
      await page.waitForLoadState("networkidle");
    }

    await expect(page.locator(".task-item")).toHaveCount(2);

    const taskToDelete = page.locator(".task-item").filter({ hasText: "Remove me" });
    await taskToDelete.getByRole("button", { name: "Delete task" }).click();

    await page.waitForResponse((res) => res.url().includes("/tasks/") && res.request().method() === "DELETE");
    await page.waitForLoadState("networkidle");

    await expect(page.locator(".task-item")).toHaveCount(1);
    await expect(page.locator(".task-item").filter({ hasText: "Keep me" })).toBeVisible();
    await expect(page.locator("#task-count-badge")).toHaveText("1 / 1");
  });

  test("task count badge tracks mixed completed/pending states", async ({ page }) => {
    await setupSingleList(page);

    for (const name of ["Task 1", "Task 2", "Task 3"]) {
      await slInput(page, "#new-task-input").fill(name);
      await page.getByRole("button", { name: "Add", exact: true }).click();
      await page.waitForResponse((res) => res.url().includes("/tasks") && res.status() === 201);
      await page.waitForLoadState("networkidle");
    }

    await expect(page.locator("#task-count-badge")).toHaveText("3 / 3");

    // Complete Task 1
    await page.locator(".task-item").filter({ hasText: "Task 1" }).locator("sl-checkbox").click();
    await page.waitForResponse((res) => res.url().includes("/tasks/") && res.request().method() === "PUT");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#task-count-badge")).toHaveText("2 / 3");

    // Complete Task 2
    await page.locator(".task-item").filter({ hasText: "Task 2" }).locator("sl-checkbox").click();
    await page.waitForResponse((res) => res.url().includes("/tasks/") && res.request().method() === "PUT");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#task-count-badge")).toHaveText("1 / 3");

    await expect(page.locator("#list-nav button.active")).toContainText("1");

    // Delete Task 3 (the only pending one)
    await page.locator(".task-item").filter({ hasText: "Task 3" }).getByRole("button", { name: "Delete task" }).click();
    await page.waitForResponse((res) => res.url().includes("/tasks/") && res.request().method() === "DELETE");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#task-count-badge")).toHaveText("0 / 2");
  });

  test("tasks with special characters render safely", async ({ page }) => {
    await setupSingleList(page);

    const specialTitle = '<script>alert("xss")</script> & "quotes"';
    await slInput(page, "#new-task-input").fill(specialTitle);
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await page.waitForResponse((res) => res.url().includes("/tasks") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    // Task renders as text, not as HTML
    const taskTitle = page.locator(".task-item .task-title");
    await expect(taskTitle).toContainText('<script>alert("xss")</script>');
    await expect(taskTitle).toContainText('& "quotes"');
  });

  test("persists tasks across page reload", async ({ page }) => {
    await setupSingleList(page, "Persist Tasks");

    await slInput(page, "#new-task-input").fill("Surviving task");
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await page.waitForResponse((res) => res.url().includes("/tasks") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    // Complete it
    await page.locator(".task-item").locator("sl-checkbox").click();
    await page.waitForResponse((res) => res.url().includes("/tasks/") && res.request().method() === "PUT");
    await page.waitForLoadState("networkidle");

    // Reload
    await page.reload();
    await page.waitForLoadState("networkidle");

    // Re-select the list
    await page.locator("#list-nav button").filter({ hasText: "Persist Tasks" }).click();
    await page.waitForLoadState("networkidle");

    const taskItem = page.locator(".task-item").filter({ hasText: "Surviving task" });
    await expect(taskItem).toBeVisible();
    await expect(taskItem.locator("sl-checkbox")).toHaveJSProperty("checked", true);
    await expect(taskItem.locator(".task-title")).toHaveClass(/completed/);
  });

  test("deleting a list with tasks removes everything", async ({ page }) => {
    await setupSingleList(page, "Full Delete");

    for (const name of ["T1", "T2"]) {
      await slInput(page, "#new-task-input").fill(name);
      await page.getByRole("button", { name: "Add", exact: true }).click();
      await page.waitForResponse((res) => res.url().includes("/tasks") && res.status() === 201);
      await page.waitForLoadState("networkidle");
    }

    await expect(page.locator(".task-item")).toHaveCount(2);

    await page.getByRole("button", { name: "Delete list" }).click();
    const dialog = page.locator("#delete-dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "Delete" }).click();

    await page.waitForResponse((res) => res.url().includes("/api/lists/") && res.request().method() === "DELETE");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("#list-nav button")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Select a list" })).toBeVisible();
    await expect(page.locator("#sidebar-empty")).toBeVisible();
  });
});
