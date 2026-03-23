"""Selenium tests for list management features."""

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from selenium_tests.helpers import (
    create_list_via_api,
    navigate,
    sl_input_fill,
    get_sl_input_value,
    wait_for_list_count,
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


class TestListCreation:
    def test_shows_empty_state_when_no_lists(self, driver, wait):
        empty = driver.find_element(By.ID, "sidebar-empty")
        assert empty.is_displayed()
        assert "No lists yet" in empty.text

        heading = driver.find_element(By.CSS_SELECTOR, "#no-selection h2")
        assert heading.text == "Select a list"
        assert driver.find_element(By.CSS_SELECTOR, "#no-selection p").is_displayed()

    def test_creates_list_via_button_click(self, driver, wait):
        sl_input_fill(driver, "#new-list-input", "Shopping")
        driver.find_element(By.CSS_SELECTOR, "#add-list-btn").click()

        wait_for_list_count(driver, 1)

        nav_btn = driver.find_element(By.CSS_SELECTOR, "#list-nav button")
        assert "Shopping" in nav_btn.text

        wait.until(EC.visibility_of_element_located((By.ID, "task-view")))
        heading = driver.find_element(By.ID, "task-list-name")
        assert heading.text == "Shopping"

        badge = driver.find_element(By.ID, "task-count-badge")
        assert badge.text == "0 / 0"

        assert get_sl_input_value(driver, "#new-list-input") == ""

    def test_creates_list_via_enter_key(self, driver, wait):
        sl_input_type(driver, wait, "#new-list-input", "Keyboard List")
        inner = driver.execute_script(
            "return document.querySelector('#new-list-input').shadowRoot.querySelector('input')"
        )
        inner.send_keys(Keys.ENTER)

        wait_for_list_count(driver, 1)
        assert "Keyboard List" in driver.find_element(
            By.CSS_SELECTOR, "#list-nav button"
        ).text

    def test_does_not_create_list_with_empty_name(self, driver, wait):
        sl_input_fill(driver, "#new-list-input", "   ")
        driver.find_element(By.CSS_SELECTOR, "#add-list-btn").click()

        buttons = driver.find_elements(By.CSS_SELECTOR, "#list-nav button")
        assert len(buttons) == 0
        assert driver.find_element(By.ID, "sidebar-empty").is_displayed()

    def test_creates_multiple_lists(self, driver, wait):
        for i, name in enumerate(["Work", "Personal", "Groceries"], 1):
            sl_input_fill(driver, "#new-list-input", name)
            driver.find_element(By.CSS_SELECTOR, "#add-list-btn").click()
            wait_for_list_count(driver, i)

        buttons = driver.find_elements(By.CSS_SELECTOR, "#list-nav button")
        assert len(buttons) == 3
        nav_text = driver.find_element(By.ID, "list-nav").text
        for name in ["Work", "Personal", "Groceries"]:
            assert name in nav_text


class TestListSelection:
    def test_selects_list_and_shows_task_view(self, driver, wait):
        create_list_via_api("Alpha")
        create_list_via_api("Beta")
        navigate(driver)
        wait_for_list_count(driver, 2)

        # Click Alpha
        buttons = driver.find_elements(By.CSS_SELECTOR, "#list-nav button")
        for btn in buttons:
            if "Alpha" in btn.text:
                btn.click()
                break

        wait.until(EC.visibility_of_element_located((By.ID, "task-view")))
        assert driver.find_element(By.ID, "task-list-name").text == "Alpha"

        # Switch to Beta — re-query buttons after re-render
        wait.until(
            lambda d: any(
                "Beta" in b.text
                for b in d.find_elements(By.CSS_SELECTOR, "#list-nav button")
            )
        )
        buttons = driver.find_elements(By.CSS_SELECTOR, "#list-nav button")
        for btn in buttons:
            if "Beta" in btn.text:
                btn.click()
                break

        wait.until(lambda d: d.find_element(By.ID, "task-list-name").text == "Beta")

    def test_sidebar_active_class_toggles(self, driver, wait):
        create_list_via_api("First")
        create_list_via_api("Second")
        navigate(driver)
        wait_for_list_count(driver, 2)

        # Click First
        driver.execute_script(
            """
            const btns = document.querySelectorAll('#list-nav button');
            for (const b of btns) { if (b.textContent.includes('First')) { b.click(); break; } }
            """
        )

        wait.until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button.active")) == 1
            and "First" in d.find_element(By.CSS_SELECTOR, "#list-nav button.active").text
        )

        # Switch to Second
        driver.execute_script(
            """
            const btns = document.querySelectorAll('#list-nav button');
            for (const b of btns) { if (b.textContent.includes('Second')) { b.click(); break; } }
            """
        )

        wait.until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button.active")) == 1
            and "Second" in d.find_element(By.CSS_SELECTOR, "#list-nav button.active").text
        )

    def test_new_list_auto_selected(self, driver, wait):
        create_list_via_api("Existing")
        navigate(driver)
        wait_for_list_count(driver, 1)

        driver.find_element(By.CSS_SELECTOR, "#list-nav button").click()
        wait.until(EC.visibility_of_element_located((By.ID, "task-view")))

        sl_input_fill(driver, "#new-list-input", "Brand New")
        driver.find_element(By.CSS_SELECTOR, "#add-list-btn").click()
        wait_for_list_count(driver, 2)

        wait.until(lambda d: d.find_element(By.ID, "task-list-name").text == "Brand New")
        active = driver.find_elements(By.CSS_SELECTOR, "#list-nav button.active")
        assert len(active) == 1
        assert "Brand New" in active[0].text


class TestListRename:
    def _open_rename_dialog(self, driver, wait, list_name):
        create_list_via_api(list_name)
        navigate(driver)
        wait_for_list_count(driver, 1)
        driver.find_element(By.CSS_SELECTOR, "#list-nav button").click()
        wait.until(EC.visibility_of_element_located((By.ID, "task-view")))
        driver.find_element(By.ID, "rename-list-btn").click()
        wait.until(
            lambda d: d.execute_script(
                'return document.querySelector("#rename-dialog").open'
            )
        )

    def test_renames_a_list(self, driver, wait):
        self._open_rename_dialog(driver, wait, "Old Name")
        assert get_sl_input_value(driver, "#rename-input") == "Old Name"

        sl_input_fill(driver, "#rename-input", "New Name")
        driver.find_element(By.ID, "rename-confirm-btn").click()

        wait.until(
            lambda d: not d.execute_script(
                'return document.querySelector("#rename-dialog").open'
            )
        )
        wait.until(lambda d: d.find_element(By.ID, "task-list-name").text == "New Name")
        assert "New Name" in driver.find_element(By.ID, "list-nav").text

    def test_renames_via_enter_key(self, driver, wait):
        self._open_rename_dialog(driver, wait, "Enter Test")

        sl_input_fill(driver, "#rename-input", "Renamed Via Enter")
        # Send Enter to the inner shadow DOM input
        driver.execute_script(
            """
            const inner = document.querySelector('#rename-input').shadowRoot.querySelector('input');
            inner.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true, composed: true}));
            """
        )

        wait.until(
            lambda d: not d.execute_script(
                'return document.querySelector("#rename-dialog").open'
            )
        )
        wait.until(
            lambda d: d.find_element(By.ID, "task-list-name").text == "Renamed Via Enter"
        )

    def test_cancel_rename_preserves_name(self, driver, wait):
        self._open_rename_dialog(driver, wait, "Keep This")

        driver.find_element(By.ID, "rename-cancel-btn").click()
        wait.until(
            lambda d: not d.execute_script(
                'return document.querySelector("#rename-dialog").open'
            )
        )
        assert "Keep This" in driver.find_element(By.ID, "list-nav").text

    def test_rename_with_empty_name_does_not_change(self, driver, wait):
        self._open_rename_dialog(driver, wait, "Original")

        # Clear via JS
        driver.execute_script(
            'document.querySelector("#rename-input").value = "";'
        )
        driver.find_element(By.ID, "rename-confirm-btn").click()

        # Dialog should remain open (empty name is rejected by JS)
        assert driver.execute_script(
            'return document.querySelector("#rename-dialog").open'
        )
        driver.find_element(By.ID, "rename-cancel-btn").click()
        wait.until(
            lambda d: not d.execute_script(
                'return document.querySelector("#rename-dialog").open'
            )
        )
        assert driver.find_element(By.ID, "task-list-name").text == "Original"

    def test_rename_dialog_close_via_x_button(self, driver, wait):
        self._open_rename_dialog(driver, wait, "CloseX Test")

        driver.execute_script(
            'document.querySelector("#rename-dialog")'
            '.shadowRoot.querySelector("[part=close-button]").click()'
        )
        wait.until(
            lambda d: not d.execute_script(
                'return document.querySelector("#rename-dialog").open'
            )
        )
        assert "CloseX Test" in driver.find_element(By.ID, "list-nav").text


class TestListDeletion:
    def _open_delete_dialog(self, driver, wait, list_name):
        create_list_via_api(list_name)
        navigate(driver)
        wait_for_list_count(driver, 1)
        driver.find_element(By.CSS_SELECTOR, "#list-nav button").click()
        wait.until(EC.visibility_of_element_located((By.ID, "task-view")))
        driver.find_element(By.ID, "delete-list-btn").click()
        wait.until(
            lambda d: d.execute_script(
                'return document.querySelector("#delete-dialog").open'
            )
        )

    def test_deletes_list_with_confirmation(self, driver, wait):
        self._open_delete_dialog(driver, wait, "To Delete")

        dialog_text = driver.find_element(By.CSS_SELECTOR, "#delete-dialog p").text
        assert "To Delete" in dialog_text
        assert "Are you sure" in dialog_text

        driver.find_element(By.ID, "delete-confirm-btn").click()

        wait.until(
            lambda d: not d.execute_script(
                'return document.querySelector("#delete-dialog").open'
            )
        )
        wait_for_list_count(driver, 0)
        assert driver.find_element(By.ID, "sidebar-empty").is_displayed()
        heading = driver.find_element(By.CSS_SELECTOR, "#no-selection h2")
        assert heading.text == "Select a list"

    def test_cancel_delete_preserves_list(self, driver, wait):
        self._open_delete_dialog(driver, wait, "Don't Delete")

        driver.find_element(By.ID, "delete-cancel-btn").click()
        wait.until(
            lambda d: not d.execute_script(
                'return document.querySelector("#delete-dialog").open'
            )
        )
        assert "Don't Delete" in driver.find_element(By.ID, "list-nav").text

    def test_delete_dialog_close_via_x_button(self, driver, wait):
        self._open_delete_dialog(driver, wait, "XClose Delete")

        driver.execute_script(
            'document.querySelector("#delete-dialog")'
            '.shadowRoot.querySelector("[part=close-button]").click()'
        )
        wait.until(
            lambda d: not d.execute_script(
                'return document.querySelector("#delete-dialog").open'
            )
        )
        assert len(driver.find_elements(By.CSS_SELECTOR, "#list-nav button")) == 1


class TestListPersistence:
    def test_persists_lists_across_reload(self, driver, wait):
        sl_input_fill(driver, "#new-list-input", "Persistent")
        driver.find_element(By.CSS_SELECTOR, "#add-list-btn").click()
        wait_for_list_count(driver, 1)

        navigate(driver)
        wait_for_list_count(driver, 1)
        assert "Persistent" in driver.find_element(By.ID, "list-nav").text

        heading = driver.find_element(By.CSS_SELECTOR, "#no-selection h2")
        assert heading.text == "Select a list"

    def test_special_characters_in_list_name(self, driver, wait):
        special = '<b>Bold</b> & "quotes"'
        create_list_via_api(special)
        navigate(driver)
        wait_for_list_count(driver, 1)

        btn = driver.find_element(By.CSS_SELECTOR, "#list-nav button")
        btn_text = btn.text
        assert "<b>" in btn_text or "Bold" in btn_text
        b_tags = btn.find_elements(By.TAG_NAME, "b")
        assert len(b_tags) == 0

        btn.click()
        wait.until(EC.visibility_of_element_located((By.ID, "task-view")))
        header_text = driver.find_element(By.ID, "task-list-name").text
        assert "<b>" in header_text or "Bold" in header_text
