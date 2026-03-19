import { test, expect, Page, Locator } from "@playwright/test";

// Shoelace sl-input wraps a native <input> in shadow DOM.
// Playwright CSS selectors pierce shadow DOM, so we target the inner input.
function slInput(page: Page, selector: string): Locator {
  return page.locator(`${selector} input`);
}

// Assert sl-input value via the custom element's .value property
async function expectSlInputValue(page: Page, selector: string, expected: string) {
  await expect(page.locator(selector)).toHaveJSProperty("value", expected);
}

// Reset data before each test to ensure a clean state
async function resetData(page: Page) {
  const lists = await page.evaluate(async () => {
    const res = await fetch("/api/lists");
    return res.json();
  });
  for (const list of lists) {
    await page.evaluate(async (id) => {
      await fetch(`/api/lists/${id}`, { method: "DELETE" });
    }, list.id);
  }
}

test.describe("List Management", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await resetData(page);
    await page.reload();
    await page.waitForLoadState("networkidle");
  });

  test("shows empty state when no lists exist", async ({ page }) => {
    const emptyMessage = page.locator("#sidebar-empty");
    await expect(emptyMessage).toBeVisible();
    await expect(emptyMessage).toContainText("No lists yet");

    await expect(page.getByRole("heading", { name: "Select a list" })).toBeVisible();
    await expect(page.getByText("Pick a list from the sidebar")).toBeVisible();
  });

  test("creates a new list via button click", async ({ page }) => {
    await slInput(page, "#new-list-input").fill("My Shopping List");
    await page.getByRole("button", { name: "Add List" }).click();

    await page.waitForResponse((res) => res.url().includes("/api/lists") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    // List appears in sidebar
    await expect(page.locator("#list-nav button").filter({ hasText: "My Shopping List" })).toBeVisible();

    // List is auto-selected — task view is visible
    await expect(page.getByRole("heading", { name: "My Shopping List" })).toBeVisible();

    // Badge shows 0 / 0
    await expect(page.locator("#task-count-badge")).toHaveText("0 / 0");

    // Input is cleared
    await expectSlInputValue(page, "#new-list-input", "");

    // Empty task state visible
    await expect(page.locator("#tasks-empty")).toBeVisible();
    await expect(page.locator("#tasks-empty")).toContainText("No tasks yet");
  });

  test("creates a new list via Enter key", async ({ page }) => {
    await slInput(page, "#new-list-input").fill("Keyboard List");
    await slInput(page, "#new-list-input").press("Enter");

    await page.waitForResponse((res) => res.url().includes("/api/lists") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    await expect(page.locator("#list-nav button").filter({ hasText: "Keyboard List" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Keyboard List" })).toBeVisible();
  });

  test("does not create a list with empty name", async ({ page }) => {
    await slInput(page, "#new-list-input").fill("   ");
    await page.getByRole("button", { name: "Add List" }).click();

    await expect(page.locator("#list-nav button")).toHaveCount(0);
    await expect(page.locator("#sidebar-empty")).toBeVisible();
  });

  test("creates multiple lists", async ({ page }) => {
    for (const name of ["Work", "Personal", "Groceries"]) {
      await slInput(page, "#new-list-input").fill(name);
      await page.getByRole("button", { name: "Add List" }).click();
      await page.waitForResponse((res) => res.url().includes("/api/lists") && res.status() === 201);
      await page.waitForLoadState("networkidle");
    }

    await expect(page.locator("#list-nav button")).toHaveCount(3);
    await expect(page.locator("#list-nav")).toContainText("Work");
    await expect(page.locator("#list-nav")).toContainText("Personal");
    await expect(page.locator("#list-nav")).toContainText("Groceries");
  });

  test("selects a list and shows its task view", async ({ page }) => {
    for (const name of ["Alpha", "Beta"]) {
      await slInput(page, "#new-list-input").fill(name);
      await page.getByRole("button", { name: "Add List" }).click();
      await page.waitForResponse((res) => res.url().includes("/api/lists") && res.status() === 201);
      await page.waitForLoadState("networkidle");
    }

    // Click on Alpha
    await page.locator("#list-nav button").filter({ hasText: "Alpha" }).click();
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "Alpha" }).first()).toBeVisible();
    await expect(page.locator("#task-view")).toBeVisible();
    await expect(page.locator("#no-selection")).toBeHidden();

    // Switch to Beta
    await page.locator("#list-nav button").filter({ hasText: "Beta" }).click();
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "Beta" }).first()).toBeVisible();
  });

  test("renames a list", async ({ page }) => {
    await slInput(page, "#new-list-input").fill("Old Name");
    await page.getByRole("button", { name: "Add List" }).click();
    await page.waitForResponse((res) => res.url().includes("/api/lists") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    // Open rename dialog
    await page.getByRole("button", { name: "Rename list" }).click();

    const dialog = page.locator("#rename-dialog");
    await expect(dialog).toBeVisible();
    await expect(page.getByRole("heading", { name: "Rename List" })).toBeVisible();

    // Input is pre-filled
    await expectSlInputValue(page, "#rename-input", "Old Name");

    // Clear and type new name
    await slInput(page, "#rename-input").fill("New Name");
    await page.getByRole("button", { name: "Rename", exact: true }).click();

    await page.waitForResponse((res) => res.url().includes("/api/lists/") && res.request().method() === "PUT");
    await page.waitForLoadState("networkidle");

    await expect(dialog).toBeHidden();
    await expect(page.locator("#list-nav")).toContainText("New Name");
    await expect(page.getByRole("heading", { name: "New Name" }).first()).toBeVisible();
  });

  test("cancels rename dialog without changes", async ({ page }) => {
    await slInput(page, "#new-list-input").fill("Keep This Name");
    await page.getByRole("button", { name: "Add List" }).click();
    await page.waitForResponse((res) => res.url().includes("/api/lists") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    await page.getByRole("button", { name: "Rename list" }).click();
    await expect(page.locator("#rename-dialog")).toBeVisible();

    await page.locator("#rename-dialog").getByRole("button", { name: "Cancel" }).click();

    await expect(page.locator("#rename-dialog")).toBeHidden();
    await expect(page.locator("#list-nav")).toContainText("Keep This Name");
  });

  test("renames a list via Enter key in dialog", async ({ page }) => {
    await slInput(page, "#new-list-input").fill("Enter Test");
    await page.getByRole("button", { name: "Add List" }).click();
    await page.waitForResponse((res) => res.url().includes("/api/lists") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    await page.getByRole("button", { name: "Rename list" }).click();
    await slInput(page, "#rename-input").fill("Renamed Via Enter");
    await slInput(page, "#rename-input").press("Enter");

    await page.waitForResponse((res) => res.url().includes("/api/lists/") && res.request().method() === "PUT");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("#rename-dialog")).toBeHidden();
    await expect(page.locator("#list-nav")).toContainText("Renamed Via Enter");
  });

  test("deletes a list with confirmation", async ({ page }) => {
    await slInput(page, "#new-list-input").fill("To Delete");
    await page.getByRole("button", { name: "Add List" }).click();
    await page.waitForResponse((res) => res.url().includes("/api/lists") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    await page.getByRole("button", { name: "Delete list" }).click();

    const dialog = page.locator("#delete-dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("To Delete");
    await expect(dialog).toContainText("Are you sure");

    await dialog.getByRole("button", { name: "Delete" }).click();

    await page.waitForResponse((res) => res.url().includes("/api/lists/") && res.request().method() === "DELETE");
    await page.waitForLoadState("networkidle");

    await expect(dialog).toBeHidden();
    await expect(page.locator("#list-nav button")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Select a list" })).toBeVisible();
    await expect(page.locator("#sidebar-empty")).toBeVisible();
  });

  test("cancels delete dialog without removing list", async ({ page }) => {
    await slInput(page, "#new-list-input").fill("Don't Delete Me");
    await page.getByRole("button", { name: "Add List" }).click();
    await page.waitForResponse((res) => res.url().includes("/api/lists") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    await page.getByRole("button", { name: "Delete list" }).click();
    await expect(page.locator("#delete-dialog")).toBeVisible();

    await page.locator("#delete-dialog").getByRole("button", { name: "Cancel" }).click();

    await expect(page.locator("#delete-dialog")).toBeHidden();
    await expect(page.locator("#list-nav")).toContainText("Don't Delete Me");
  });

  test("persists lists across page reload", async ({ page }) => {
    await slInput(page, "#new-list-input").fill("Persistent List");
    await page.getByRole("button", { name: "Add List" }).click();
    await page.waitForResponse((res) => res.url().includes("/api/lists") && res.status() === 201);
    await page.waitForLoadState("networkidle");

    await page.reload();
    await page.waitForLoadState("networkidle");

    await expect(page.locator("#list-nav")).toContainText("Persistent List");
    await expect(page.getByRole("heading", { name: "Select a list" })).toBeVisible();
  });
});
