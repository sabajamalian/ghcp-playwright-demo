"""Shared helpers for Selenium tests."""

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = "http://localhost:3003"
API_URL = f"{BASE_URL}/api/lists"


def create_list_via_api(name):
    """Create a list via the API. Returns the list dict."""
    resp = requests.post(API_URL, json={"name": name})
    resp.raise_for_status()
    return resp.json()


def create_task_via_api(list_id, title):
    """Create a task via the API. Returns the task dict."""
    resp = requests.post(f"{API_URL}/{list_id}/tasks", json={"title": title})
    resp.raise_for_status()
    return resp.json()


def navigate(driver):
    """Navigate to the app and wait for Shoelace components to load."""
    driver.get(BASE_URL)
    WebDriverWait(driver, 10).until(
        lambda d: d.execute_script(
            "return document.querySelector('sl-button') !== null "
            "&& document.querySelector('sl-button').shadowRoot !== null"
        )
    )
    WebDriverWait(driver, 10).until(
        lambda d: d.execute_script(
            "return document.querySelector('#list-nav') !== null"
        )
    )


def wait_for_list_count(driver, count):
    """Wait until the sidebar has exactly `count` list buttons."""
    WebDriverWait(driver, 10).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "#list-nav button")) == count
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


def get_sl_input_value(driver, css_selector):
    """Read the .value property of a Shoelace sl-input."""
    return driver.execute_script(
        f'return document.querySelector("{css_selector}").value'
    )
