from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from typing import List, Dict

class ScriptGenerator:
    def __init__(self):
        self.selenium_template = """
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def run_test():
    # Initialize the driver
    driver = webdriver.Chrome()
    driver.maximize_window()
    wait = WebDriverWait(driver, 10)
    
    try:
        {test_steps}
        
    except Exception as e:
        print(f"Test failed: {{str(e)}}")
    finally:
        time.sleep(2)  # Small delay before closing
        driver.quit()

        
if __name__ == "__main__":
    run_test()
"""

        self.playwright_template = """
from playwright.sync_api import sync_playwright
import time

def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            {test_steps}
            
        except Exception as e:
            print(f"Test failed: {{str(e)}}")
        finally:
            time.sleep(2)  # Small delay before closing
            browser.close()

if __name__ == "__main__":
    run_test()
"""

    def generate_selenium_steps(self, actions: List[Dict]) -> str:
        steps = []
        for action in actions:
            if action["type"] == "navigate":
                url = action["element_info"].get("url", "")
                steps.append(f"""
        # Navigate to URL
        driver.get("{url}")
        time.sleep(2)  # Wait for page load""")
                
            elif action["type"] == "input":
                locator = action["locators"].get("xpath", "")
                input_value = action["element_info"].get("value", "")
                steps.append(f"""
        # Wait for input element and enter text
        element = wait.until(EC.presence_of_element_located((By.XPATH, "{locator}")))
        element.clear()
        element.send_keys("{input_value}")
        element.send_keys(Keys.RETURN)
        time.sleep(2)  # Wait for search results""")
                
            elif action["type"] == "click":
                locator = action["locators"].get("xpath", "")
                steps.append(f"""
        # Wait for element to be clickable and click
        element = wait.until(EC.element_to_be_clickable((By.XPATH, "{locator}")))
        element.click()
        time.sleep(2)  # Wait for action to complete""")
        
        return "\n".join(steps)

    def generate_playwright_steps(self, actions: List[Dict]) -> str:
        steps = []
        for action in actions:
            if action["type"] == "navigate":
                url = action["element_info"].get("url", "")
                steps.append(f"""
            # Navigate to URL
            page.goto("{url}")
            page.wait_for_load_state("networkidle")""")
                
            elif action["type"] == "input":
                locator = action["locators"].get("css", "")
                input_value = action["element_info"].get("value", "")
                steps.append(f"""
            # Fill input field and submit
            page.fill("{locator}", "{input_value}")
            page.keyboard.press("Enter")
            page.wait_for_load_state("networkidle")""")
                
            elif action["type"] == "click":
                locator = action["locators"].get("css", "")
                steps.append(f"""
            # Click element
            page.click("{locator}")
            page.wait_for_load_state("networkidle")""")
        
        return "\n".join(steps)

    def generate_script(self, actions: List[Dict], framework: str) -> str:
        """
        Generate automation script based on recorded actions
        
        Args:
            actions (List[Dict]): List of recorded actions
            framework (str): Target automation framework
            
        Returns:
            str: Generated automation script
        """
        if framework.lower() == "selenium":
            steps = self.generate_selenium_steps(actions)
            return self.selenium_template.format(test_steps=steps)
        elif framework.lower() == "playwright":
            steps = self.generate_playwright_steps(actions)
            return self.playwright_template.format(test_steps=steps)
        else:
            raise ValueError(f"Unsupported framework: {framework}")
