"""Selenium tests for task management features."""

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from selenium_tests.helpers import (
    create_list_via_api,
    create_task_via_api,
    navigate,
    sl_input_fill,
    get_sl_input_value,
    wait_for_list_count,
)


def sl_input_fill(driver, css_selector, value):
    """Clear and fill a Shoelace sl-input via JS (shadow DOM)."""
    driver.execute_script(
        """
        const el = document.querySelector(arguments[0]);
        el.value = arguments[1];
        el.dispatchEvent(new Event('sl-input', {bubbles: true}));
        """,
        css_selector,
        value,
    )


def sl_input_type(driver, wait, css_selector, value):
    """Type into a Shoelace sl-input by focusing its shadow DOM inner input."""
    inner = driver.execute_script(
        "return document.querySelector(arguments[0]).shadowRoot.querySelector('input[type=text],input:not([type])')",
        css_selector,
    )
    wait.until(lambda d: inner.is_displayed())
    inner.clear()
    inner.send_keys(value)


def get_sl_input_value(driver, css_selector):
    return driver.execute_script(
        f'return document.querySelector("{css_selector}").value'
    )


def select_list(driver, wait, name):
    """Click a list button in the sidebar by name and wait for task view."""
    driver.execute_script(
        """
        const btns = document.querySelectorAll('#list-nav button');
        for (const b of btns) { if (b.textContent.includes(arguments[0])) { b.click(); break; } }
        """,
        name,
    )
    wait.until(EC.visibility_of_element_located((By.ID, "task-view")))
    wait.until(lambda d: d.find_element(By.ID, "task-list-name").text == name)


def setup_list_and_select(driver, wait, list_name="Test List"):
    """Create a list via API, reload, and select it."""
    lst = create_list_via_api(list_name)
    driver.get(BASE_URL)
    WebDriverWait(driver, 10).until(
        lambda d: d.execute_script(
            "return document.querySelector('sl-button') !== null "
            "&& document.querySelector('sl-button').shadowRoot !== null"
        )
    )
    WebDriverWait(driver, 10).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) >= 1
    )
    select_list(driver, wait, list_name)
    return lst


def get_task_items(driver):
    return driver.find_elements(By.CSS_SELECTOR, ".task-item")


def get_badge_text(driver):
    return driver.find_element(By.ID, "task-count-badge").text


class TestTaskCreation:
    def test_adds_task_via_button_click(self, driver, wait):
        setup_list_and_select(driver, wait)

        sl_input_fill(driver, "#new-task-input", "Buy groceries")
        driver.find_element(By.CSS_SELECTOR, "#add-task-btn").click()

        wait.until(lambda d: len(get_task_items(d)) == 1)

        task = get_task_items(driver)[0]
        assert "Buy groceries" in task.text

        # Checkbox unchecked
        checked = driver.execute_script(
            'return document.querySelector(".task-item sl-checkbox").checked'
        )
        assert checked is False

        assert get_badge_text(driver) == "1 / 1"
        assert get_sl_input_value(driver, "#new-task-input") == ""

    def test_adds_task_via_enter_key(self, driver, wait):
        setup_list_and_select(driver, wait)

        sl_input_type(driver, wait, "#new-task-input", "Keyboard task")
        inner = driver.execute_script(
            "return document.querySelector('#new-task-input').shadowRoot.querySelector('input')"
        )
        inner.send_keys(Keys.ENTER)

        wait.until(lambda d: len(get_task_items(d)) == 1)
        assert "Keyboard task" in get_task_items(driver)[0].text

    def test_does_not_add_empty_task(self, driver, wait):
        setup_list_and_select(driver, wait)

        sl_input_fill(driver, "#new-task-input", "   ")
        driver.find_element(By.CSS_SELECTOR, "#add-task-btn").click()

        items = get_task_items(driver)
        assert len(items) == 0
        assert driver.find_element(By.ID, "tasks-empty").is_displayed()

    def test_adds_multiple_tasks(self, driver, wait):
        setup_list_and_select(driver, wait)

        for i, title in enumerate(["Task A", "Task B", "Task C"], 1):
            sl_input_fill(driver, "#new-task-input", title)
            driver.find_element(By.CSS_SELECTOR, "#add-task-btn").click()
            wait.until(lambda d, count=i: len(get_task_items(d)) == count)

        assert len(get_task_items(driver)) == 3
        assert get_badge_text(driver) == "3 / 3"

    def test_task_input_focus_after_adding(self, driver, wait):
        setup_list_and_select(driver, wait)

        sl_input_fill(driver, "#new-task-input", "Focus test")
        driver.find_element(By.CSS_SELECTOR, "#add-task-btn").click()
        wait.until(lambda d: len(get_task_items(d)) == 1)

        # The inner input of #new-task-input should be focused
        wait.until(
            lambda d: d.execute_script(
                'return document.activeElement === document.querySelector("#new-task-input") '
                '|| document.querySelector("#new-task-input").shadowRoot.activeElement !== null '
                '|| document.activeElement.closest("#new-task-input") !== null'
            )
        )

    def test_special_characters_in_task_title(self, driver, wait):
        setup_list_and_select(driver, wait)

        special = '<script>alert("xss")</script> & "quotes"'
        sl_input_fill(driver, "#new-task-input", special)
        driver.find_element(By.CSS_SELECTOR, "#add-task-btn").click()
        wait.until(lambda d: len(get_task_items(d)) == 1)

        title_el = driver.find_element(By.CSS_SELECTOR, ".task-item .task-title")
        # Rendered as text, not HTML
        assert "<script>" in title_el.text
        assert '& "quotes"' in title_el.text


class TestTaskToggle:
    def _setup_with_task(self, driver, wait, task_title, list_name="Test List"):
        """Create list + task via API, navigate, and select the list."""
        lst = create_list_via_api(list_name)
        create_task_via_api(lst["id"], task_title)
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script(
                "return document.querySelector('sl-button') !== null "
                "&& document.querySelector('sl-button').shadowRoot !== null"
            )
        )
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) >= 1
        )
        select_list(driver, wait, list_name)
        wait.until(lambda d: len(get_task_items(d)) == 1)
        return lst

    def test_toggles_task_to_completed(self, driver, wait):
        self._setup_with_task(driver, wait, "Toggle me")
        assert get_badge_text(driver) == "1 / 1"

        driver.execute_script(
            'document.querySelector(".task-item sl-checkbox").click()'
        )
        wait.until(lambda d: get_badge_text(d) == "0 / 1")

        title_el = driver.find_element(By.CSS_SELECTOR, ".task-item .task-title")
        assert "completed" in title_el.get_attribute("class")

    def test_toggles_task_back_to_uncompleted(self, driver, wait):
        self._setup_with_task(driver, wait, "Toggle back")

        driver.execute_script(
            'document.querySelector(".task-item sl-checkbox").click()'
        )
        wait.until(lambda d: get_badge_text(d) == "0 / 1")

        driver.execute_script(
            'document.querySelector(".task-item sl-checkbox").click()'
        )
        wait.until(lambda d: get_badge_text(d) == "1 / 1")

        checked = driver.execute_script(
            'return document.querySelector(".task-item sl-checkbox").checked'
        )
        assert checked is False
        title_el = driver.find_element(By.CSS_SELECTOR, ".task-item .task-title")
        assert "completed" not in title_el.get_attribute("class")

    def test_completion_shows_strikethrough(self, driver, wait):
        self._setup_with_task(driver, wait, "Strike me")

        driver.execute_script(
            'document.querySelector(".task-item sl-checkbox").click()'
        )
        wait.until(lambda d: get_badge_text(d) == "0 / 1")

        title_el = driver.find_element(By.CSS_SELECTOR, ".task-item .task-title")
        text_decoration = title_el.value_of_css_property("text-decoration")
        assert "line-through" in text_decoration


class TestTaskDeletion:
    def _navigate_with_tasks(self, driver, wait, list_name, task_titles):
        """Create list + tasks via API, navigate, select list, wait for tasks."""
        lst = create_list_via_api(list_name)
        for t in task_titles:
            create_task_via_api(lst["id"], t)
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script(
                "return document.querySelector('sl-button') !== null "
                "&& document.querySelector('sl-button').shadowRoot !== null"
            )
        )
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) >= 1
        )
        select_list(driver, wait, list_name)
        wait.until(lambda d: len(get_task_items(d)) == len(task_titles))
        return lst

    def test_deletes_a_task(self, driver, wait):
        self._navigate_with_tasks(driver, wait, "Test List", ["Delete me"])

        driver.execute_script(
            'document.querySelector(".task-item sl-icon-button").click()'
        )

        wait.until(lambda d: len(get_task_items(d)) == 0)
        assert get_badge_text(driver) == "0 / 0"
        assert driver.find_element(By.ID, "tasks-empty").is_displayed()

    def test_deletes_one_task_while_others_remain(self, driver, wait):
        self._navigate_with_tasks(driver, wait, "Test List", ["Keep me", "Remove me"])

        # Delete "Remove me" via JS
        driver.execute_script(
            """
            const items = document.querySelectorAll('.task-item');
            for (const item of items) {
                if (item.textContent.includes('Remove me')) {
                    item.querySelector('sl-icon-button').click();
                    break;
                }
            }
            """
        )

        wait.until(lambda d: len(get_task_items(d)) == 1)
        assert "Keep me" in get_task_items(driver)[0].text
        assert get_badge_text(driver) == "1 / 1"

    def test_task_delete_adds_removing_class(self, driver, wait):
        self._navigate_with_tasks(driver, wait, "Test List", ["Animate me"])

        driver.execute_script(
            'document.querySelector(".task-item sl-icon-button").click()'
        )

        wait.until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, ".task-item.removing")) > 0
            or len(d.find_elements(By.CSS_SELECTOR, ".task-item")) == 0
        )


class TestTaskBadge:
    def test_badge_tracks_mixed_states(self, driver, wait):
        lst = create_list_via_api("Test List")
        for t in ["Task 1", "Task 2", "Task 3"]:
            create_task_via_api(lst["id"], t)
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script(
                "return document.querySelector('sl-button') !== null "
                "&& document.querySelector('sl-button').shadowRoot !== null"
            )
        )
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) >= 1
        )
        select_list(driver, wait, "Test List")
        wait.until(lambda d: len(get_task_items(d)) == 3)

        assert get_badge_text(driver) == "3 / 3"

        # Complete Task 1
        driver.execute_script(
            'document.querySelectorAll(".task-item sl-checkbox")[0].click()'
        )
        wait.until(lambda d: get_badge_text(d) == "2 / 3")

        # Complete Task 2
        driver.execute_script(
            'document.querySelectorAll(".task-item sl-checkbox")[1].click()'
        )
        wait.until(lambda d: get_badge_text(d) == "1 / 3")

    def test_sidebar_pending_count_accuracy(self, driver, wait):
        lst = create_list_via_api("Counted")
        create_task_via_api(lst["id"], "Pending 1")
        create_task_via_api(lst["id"], "Pending 2")
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script(
                "return document.querySelector('sl-button') !== null "
                "&& document.querySelector('sl-button').shadowRoot !== null"
            )
        )
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) >= 1
        )

        # Before selecting, sidebar should show pending count = 2
        btn = driver.find_element(By.CSS_SELECTOR, "#list-nav button")
        count_el = btn.find_element(By.CSS_SELECTOR, ".task-count")
        assert count_el.text == "2"

        # Select and complete one
        select_list(driver, wait, "Counted")
        driver.execute_script(
            'document.querySelectorAll(".task-item sl-checkbox")[0].click()'
        )
        wait.until(lambda d: get_badge_text(d) == "1 / 2")

        # Sidebar count should update to 1
        wait.until(
            lambda d: d.find_element(
                By.CSS_SELECTOR, "#list-nav button.active .task-count"
            ).text == "1"
        )


class TestTaskPersistence:
    def test_persists_tasks_across_reload(self, driver, wait):
        lst = setup_list_and_select(driver, wait, "Persist Tasks")

        sl_input_fill(driver, "#new-task-input", "Surviving task")
        driver.find_element(By.CSS_SELECTOR, "#add-task-btn").click()
        wait.until(lambda d: len(get_task_items(d)) == 1)

        # Complete it
        driver.execute_script(
            'document.querySelector(".task-item sl-checkbox").click()'
        )
        wait.until(lambda d: get_badge_text(d) == "0 / 1")

        # Reload and re-select
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script(
                "return document.querySelector('sl-button') !== null "
                "&& document.querySelector('sl-button').shadowRoot !== null"
            )
        )
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) >= 1
        )
        select_list(driver, wait, "Persist Tasks")
        wait.until(lambda d: len(get_task_items(d)) == 1)

        checked = driver.execute_script(
            'return document.querySelector(".task-item sl-checkbox").checked'
        )
        assert checked is True
        title_el = driver.find_element(By.CSS_SELECTOR, ".task-item .task-title")
        assert "completed" in title_el.get_attribute("class")

    def test_deleting_list_removes_all_tasks(self, driver, wait):
        lst = setup_list_and_select(driver, wait, "Full Delete")

        for title in ["T1", "T2"]:
            sl_input_fill(driver, "#new-task-input", title)
            driver.find_element(By.CSS_SELECTOR, "#add-task-btn").click()

        wait.until(lambda d: len(get_task_items(d)) == 2)

        driver.find_element(By.ID, "delete-list-btn").click()
        wait.until(
            lambda d: d.execute_script(
                'return document.querySelector("#delete-dialog").open'
            )
        )
        driver.find_element(By.ID, "delete-confirm-btn").click()

        wait.until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) == 0
        )
        assert driver.find_element(By.ID, "sidebar-empty").is_displayed()


class TestEmptyStateTransitions:
    def test_sidebar_empty_state_lifecycle(self, driver, wait):
        # Initially empty
        assert driver.find_element(By.ID, "sidebar-empty").is_displayed()

        # Create a list — empty state hides
        sl_input_fill(driver, "#new-list-input", "First List")
        driver.find_element(By.CSS_SELECTOR, "#add-list-btn").click()
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) == 1)
        assert not driver.find_element(By.ID, "sidebar-empty").is_displayed()

        # Delete the list — empty state reappears
        driver.find_element(By.ID, "delete-list-btn").click()
        wait.until(
            lambda d: d.execute_script(
                'return document.querySelector("#delete-dialog").open'
            )
        )
        driver.find_element(By.ID, "delete-confirm-btn").click()
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) == 0)
        wait.until(lambda d: d.find_element(By.ID, "sidebar-empty").is_displayed())

    def test_tasks_empty_state_lifecycle(self, driver, wait):
        setup_list_and_select(driver, wait)

        # Initially no tasks — empty state visible
        assert driver.find_element(By.ID, "tasks-empty").is_displayed()

        # Add a task — empty state hides
        sl_input_fill(driver, "#new-task-input", "Something")
        driver.find_element(By.CSS_SELECTOR, "#add-task-btn").click()
        wait.until(lambda d: len(get_task_items(d)) == 1)
        assert not driver.find_element(By.ID, "tasks-empty").is_displayed()

        # Delete the task — empty state reappears
        driver.execute_script(
            'document.querySelector(".task-item sl-icon-button").click()'
        )
        wait.until(lambda d: len(get_task_items(d)) == 0)
        wait.until(lambda d: d.find_element(By.ID, "tasks-empty").is_displayed())


class TestAccessibility:
    def test_aria_labels_on_icon_buttons(self, driver, wait):
        create_list_via_api("A11y Test")
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) >= 1
        )
        select_list(driver, wait, "A11y Test")

        rename_btn = driver.find_element(By.ID, "rename-list-btn")
        assert rename_btn.get_attribute("label") == "Rename list"

        delete_btn = driver.find_element(By.ID, "delete-list-btn")
        assert delete_btn.get_attribute("label") == "Delete list"

    def test_dialog_labels(self, driver, wait):
        create_list_via_api("Dialog A11y")
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) >= 1
        )
        select_list(driver, wait, "Dialog A11y")

        rename_dialog = driver.find_element(By.ID, "rename-dialog")
        assert rename_dialog.get_attribute("label") == "Rename List"

        delete_dialog = driver.find_element(By.ID, "delete-dialog")
        assert delete_dialog.get_attribute("label") == "Delete List"

    def test_landmark_elements_present(self, driver, wait):
        nav = driver.find_elements(By.CSS_SELECTOR, "nav#list-nav")
        assert len(nav) == 1

        aside = driver.find_elements(By.CSS_SELECTOR, "aside#sidebar")
        assert len(aside) == 1

        main = driver.find_elements(By.CSS_SELECTOR, "main#main-panel")
        assert len(main) == 1

    def test_task_delete_buttons_have_labels(self, driver, wait):
        lst = create_list_via_api("Label Test")
        create_task_via_api(lst["id"], "Check label")
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) >= 1
        )
        select_list(driver, wait, "Label Test")
        wait.until(lambda d: len(get_task_items(d)) == 1)

        del_btn = driver.find_element(
            By.CSS_SELECTOR, ".task-item sl-icon-button"
        )
        assert del_btn.get_attribute("label") == "Delete task"

    def test_escape_closes_rename_dialog(self, driver, wait):
        create_list_via_api("Esc Test")
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) >= 1
        )
        select_list(driver, wait, "Esc Test")

        driver.find_element(By.ID, "rename-list-btn").click()
        wait.until(
            lambda d: d.execute_script(
                'return document.querySelector("#rename-dialog").open'
            )
        )

        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()

        wait.until(
            lambda d: not d.execute_script(
                'return document.querySelector("#rename-dialog").open'
            )
        )

    def test_escape_closes_delete_dialog(self, driver, wait):
        create_list_via_api("Esc Del Test")
        driver.get(BASE_URL)
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) >= 1
        )
        select_list(driver, wait, "Esc Del Test")

        driver.find_element(By.ID, "delete-list-btn").click()
        wait.until(
            lambda d: d.execute_script(
                'return document.querySelector("#delete-dialog").open'
            )
        )

        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()

        wait.until(
            lambda d: not d.execute_script(
                'return document.querySelector("#delete-dialog").open'
            )
        )
