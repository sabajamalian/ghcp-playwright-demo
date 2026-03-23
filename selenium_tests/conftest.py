import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from selenium_tests.helpers import API_URL, navigate


@pytest.fixture(scope="session")
def chrome_options():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    return opts


@pytest.fixture()
def driver(chrome_options):
    d = webdriver.Chrome(options=chrome_options)
    d.implicitly_wait(0)
    yield d
    d.quit()


@pytest.fixture()
def wait(driver):
    return WebDriverWait(driver, 10)


@pytest.fixture(autouse=True)
def clean_data(driver):
    """Delete all lists via API before each test, then navigate to the app."""
    resp = requests.get(API_URL)
    for lst in resp.json():
        requests.delete(f"{API_URL}/{lst['id']}")
    navigate(driver)
    yield
