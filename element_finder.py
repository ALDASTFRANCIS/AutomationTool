from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Optional
import logging

class ElementFinder:
    def __init__(self, driver):
        self.driver = driver
        self.logger = logging.getLogger(__name__)

    def find_element_by_locators(self, locators: dict, timeout: int = 10) -> Optional[object]:
        """
        Find element using generated locators
        
        Args:
            locators (dict): Dictionary of locators
            timeout (int): Wait timeout in seconds
            
        Returns:
            Optional[object]: WebElement if found, None otherwise
        """
        for locator_type, locator_value in locators.items():
            try:
                if locator_type == "id":
                    return WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.ID, locator_value))
                    )
                elif locator_type == "xpath":
                    return WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.XPATH, locator_value))
                    )
                elif locator_type == "css":
                    return WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, locator_value))
                    )
            except Exception as e:
                self.logger.debug(f"Failed to find element with {locator_type}: {str(e)}")
                continue
        
        return None 