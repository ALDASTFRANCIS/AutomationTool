import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import openai
from typing import Dict, List, Optional
import logging

class WebAutomationTool:
    def __init__(self, api_key: str):
        """
        Initialize the Web Automation Tool
        
        Args:
            api_key (str): OpenAI API key for LLM integration
        """
        self.driver = None
        self.actions = []
        self.openai = openai
        self.openai.api_key = api_key
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging for the automation tool"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('automation.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def initialize_browser(self):
        """Initialize the browser with undetected-chromedriver"""
        try:
            self.driver = uc.Chrome()
            self.driver.maximize_window()
            self.logger.info("Browser initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {str(e)}")
            raise

    def navigate_to_url(self, url: str):
        """
        Navigate to the specified URL
        
        Args:
            url (str): The URL to navigate to
        """
        try:
            self.driver.get(url)
            self.logger.info(f"Navigated to URL: {url}")
        except Exception as e:
            self.logger.error(f"Failed to navigate to URL: {str(e)}")
            raise

    def get_element_info(self, element) -> Dict:
        """
        Extract element information for locator generation
        
        Args:
            element: WebElement object
            
        Returns:
            Dict: Dictionary containing element attributes
        """
        try:
            return {
                "tag": element.tag_name,
                "id": element.get_attribute("id"),
                "class": element.get_attribute("class"),
                "text": element.text,
                "aria-label": element.get_attribute("aria-label"),
                "name": element.get_attribute("name"),
                "type": element.get_attribute("type"),
                "href": element.get_attribute("href"),
                "value": element.get_attribute("value"),
                "placeholder": element.get_attribute("placeholder"),
                "dom": element.get_attribute("outerHTML")
            }
        except Exception as e:
            self.logger.error(f"Failed to get element info: {str(e)}")
            return {}

    def generate_locators(self, element_info: Dict) -> Dict[str, str]:
        """
        Generate unique locators using LLM
        
        Args:
            element_info (Dict): Dictionary containing element information
            
        Returns:
            Dict[str, str]: Dictionary containing generated locators
        """
        try:
            prompt = f"""
            Generate unique locators (ID, XPath, and CSS selector) for the following element:
            Element information: {json.dumps(element_info, indent=2)}
            
            Rules:
            1. Prefer ID if available
            2. Use text content if present
            3. Combine multiple attributes for uniqueness
            4. Ensure the locator is specific enough
            
            Return only the JSON response in this format:
            {{
                "xpath": "generated xpath",
                "css": "generated css selector",
                "id": "id if available"
            }}
            """

            response = self.openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )

            locators = json.loads(response.choices[0].message.content)
            self.logger.info("Successfully generated locators")
            return locators

        except Exception as e:
            self.logger.error(f"Failed to generate locators: {str(e)}")
            return {}

    def record_action(self, action_type: str, element_info: Dict, locators: Dict[str, str]):
        """
        Record an automation action
        
        Args:
            action_type (str): Type of action (click, input, etc.)
            element_info (Dict): Element information
            locators (Dict[str, str]): Generated locators
        """
        action = {
            "type": action_type,
            "element_info": element_info,
            "locators": locators,
            "timestamp": import datetime; datetime.datetime.now().isoformat()
        }
        self.actions.append(action)
        self.logger.info(f"Recorded action: {action_type}")

    def generate_script(self, framework: str, language: str) -> str:
        """
        Generate automation script based on recorded actions
        
        Args:
            framework (str): Automation framework (selenium/playwright)
            language (str): Programming language (python/javascript)
            
        Returns:
            str: Generated automation script
        """
        try:
            prompt = f"""
            Generate a {framework} script in {language} for the following actions:
            {json.dumps(self.actions, indent=2)}
            
            Include proper imports, error handling, and comments.
            """

            response = self.openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )

            generated_script = response.choices[0].message.content
            self.logger.info(f"Successfully generated {framework} script in {language}")
            return generated_script

        except Exception as e:
            self.logger.error(f"Failed to generate script: {str(e)}")
            return ""

    def save_script(self, script: str, filename: str):
        """
        Save the generated script to a file
        
        Args:
            script (str): Generated automation script
            filename (str): Output filename
        """
        try:
            with open(filename, 'w') as f:
                f.write(script)
            self.logger.info(f"Script saved to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save script: {str(e)}")
            raise

    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
        self.logger.info("Cleanup completed")
