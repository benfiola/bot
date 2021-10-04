import contextlib
import logging
import platform
from typing import ContextManager

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver import Firefox, FirefoxOptions


logger = logging.getLogger(__name__)


@contextlib.contextmanager
def create() -> ContextManager[WebDriver]:
    """
    Creates a webdriver context manager so that browsers are correctly cleaned up after use.
    :return:
    """
    logger.debug(f"creating browser")

    options = FirefoxOptions()
    options.headless = True

    service_log_path = "/dev/null"
    if platform.system().lower() == "win32":
        service_log_path = "nul"

    driver = Firefox(options=options, service_log_path=service_log_path)
    try:
        yield driver
    finally:
        driver.close()
