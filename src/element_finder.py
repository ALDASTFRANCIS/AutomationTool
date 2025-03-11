from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Optional, Dict
import logging

class ElementFinder:
    def __init__(self, driver):
        """
        Initialize ElementFinder with a WebDriver instance
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
        self.logger = logging.getLogger(__name__)
        self.wait = WebDriverWait(self.driver, 10)  # Default timeout of 10 seconds

    def find_element_by_locators(self, locators: Dict[str, str], timeout: int = 10) -> Optional[object]:
        """
        Find element using multiple locator strategies
        
        Args:
            locators (Dict[str, str]): Dictionary of locator strategies and values
            timeout (int): Wait timeout in seconds
            
        Returns:
            Optional[object]: WebElement if found, None otherwise
        """
        for locator_type, locator_value in locators.items():
            try:
                if not locator_value:
                    continue

                if locator_type == "id":
                    return self.wait.until(
                        EC.presence_of_element_located((By.ID, locator_value))
                    )
                elif locator_type == "xpath":
                    return self.wait.until(
                        EC.presence_of_element_located((By.XPATH, locator_value))
                    )
                elif locator_type == "css":
                    return self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, locator_value))
                    )
                elif locator_type == "name":
                    return self.wait.until(
                        EC.presence_of_element_located((By.NAME, locator_value))
                    )
                elif locator_type == "class":
                    return self.wait.until(
                        EC.presence_of_element_located((By.CLASS_NAME, locator_value))
                    )
                elif locator_type == "link_text":
                    return self.wait.until(
                        EC.presence_of_element_located((By.LINK_TEXT, locator_value))
                    )
                elif locator_type == "partial_link_text":
                    return self.wait.until(
                        EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, locator_value))
                    )
            except Exception as e:
                self.logger.debug(f"Failed to find element with {locator_type}: {locator_value}. Error: {str(e)}")
                continue
        
        return None

    def find_clickable_element(self, locators: Dict[str, str], timeout: int = 10) -> Optional[object]:
        """
        Find clickable element using multiple locator strategies
        
        Args:
            locators (Dict[str, str]): Dictionary of locator strategies and values
            timeout (int): Wait timeout in seconds
            
        Returns:
            Optional[object]: WebElement if found and clickable, None otherwise
        """
        for locator_type, locator_value in locators.items():
            try:
                if not locator_value:
                    continue

                if locator_type == "id":
                    return self.wait.until(
                        EC.element_to_be_clickable((By.ID, locator_value))
                    )
                elif locator_type == "xpath":
                    return self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, locator_value))
                    )
                elif locator_type == "css":
                    return self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, locator_value))
                    )
            except Exception as e:
                self.logger.debug(f"Failed to find clickable element with {locator_type}: {locator_value}. Error: {str(e)}")
                continue
        
        return None

    def find_visible_element(self, locators: Dict[str, str], timeout: int = 10) -> Optional[object]:
        """
        Find visible element using multiple locator strategies
        
        Args:
            locators (Dict[str, str]): Dictionary of locator strategies and values
            timeout (int): Wait timeout in seconds
            
        Returns:
            Optional[object]: WebElement if found and visible, None otherwise
        """
        for locator_type, locator_value in locators.items():
            try:
                if not locator_value:
                    continue

                if locator_type == "id":
                    return self.wait.until(
                        EC.visibility_of_element_located((By.ID, locator_value))
                    )
                elif locator_type == "xpath":
                    return self.wait.until(
                        EC.visibility_of_element_located((By.XPATH, locator_value))
                    )
                elif locator_type == "css":
                    return self.wait.until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, locator_value))
                    )
            except Exception as e:
                self.logger.debug(f"Failed to find visible element with {locator_type}: {locator_value}. Error: {str(e)}")
                continue
        
        return None

    def wait_for_element_presence(self, locators: Dict[str, str], timeout: int = 10) -> bool:
        """
        Wait for element presence using multiple locator strategies
        
        Args:
            locators (Dict[str, str]): Dictionary of locator strategies and values
            timeout (int): Wait timeout in seconds
            
        Returns:
            bool: True if element is found, False otherwise
        """
        return self.find_element_by_locators(locators, timeout) is not None

    def wait_for_element_clickable(self, locators: Dict[str, str], timeout: int = 10) -> bool:
        """
        Wait for element to be clickable using multiple locator strategies
        
        Args:
            locators (Dict[str, str]): Dictionary of locator strategies and values
            timeout (int): Wait timeout in seconds
            
        Returns:
            bool: True if element is found and clickable, False otherwise
        """
        return self.find_clickable_element(locators, timeout) is not None

    def wait_for_element_visible(self, locators: Dict[str, str], timeout: int = 10) -> bool:
        """
        Wait for element to be visible using multiple locator strategies
        
        Args:
            locators (Dict[str, str]): Dictionary of locator strategies and values
            timeout (int): Wait timeout in seconds
            
        Returns:
            bool: True if element is found and visible, False otherwise
        """
        return self.find_visible_element(locators, timeout) is not None
