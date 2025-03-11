import datetime
import json
import os
import time
from typing import Dict, List, Optional

import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from .config import Config
from .element_finder import ElementFinder
from .exceptions import BrowserInitializationError, ScriptGenerationError, ElementNotFoundError
from .script_generator import ScriptGenerator
from .utils import setup_logger, generate_timestamp, sanitize_filename
from openai import OpenAI

class WebAutomationTool:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Web Automation Tool
        
        Args:
            api_key (str, optional): OpenAI API key. If not provided, uses from config
        """
        self.api_key = api_key or Config.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
            
        self.driver = None
        self.actions = []
        self.client = OpenAI(api_key=self.api_key)
        
        self.element_finder = None
        self.script_generator = ScriptGenerator()
        
        self.logger = setup_logger(__name__, Config.LOG_FILE)
        
    def initialize_browser(self, headless: bool = False):
        """Initialize browser with undetected-chromedriver"""
        try:
            options = uc.ChromeOptions()
            if headless:
                options.add_argument('--headless')
            
            self.driver = uc.Chrome(options=options)
            self.driver.maximize_window()
            
            # Initialize element finder after driver is created
            self.element_finder = ElementFinder(self.driver)
            
            self.logger.info("Browser initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {str(e)}")
            raise BrowserInitializationError(f"Browser initialization failed: {str(e)}")

    def get_page_elements(self) -> Dict:
        """Get all interactive elements from the current page"""
        try:
            elements_script = """
                return {
                    'inputs': Array.from(document.querySelectorAll('input, textarea')).map(el => ({
                        tag: el.tagName,
                        type: el.type,
                        id: el.id,
                        name: el.name,
                        placeholder: el.placeholder,
                        'aria-label': el.getAttribute('aria-label'),
                        class: el.className,
                        value: el.value,
                        label: el.labels ? el.labels[0]?.textContent.trim() : '',
                        xpath: generateXPath(el),
                        preceding_text: getPrecedingText(el)
                    })),
                    'buttons': Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"], [role="button"]')).map(el => ({
                        tag: el.tagName,
                        type: el.type,
                        id: el.id,
                        text: el.innerText || el.value,
                        'aria-label': el.getAttribute('aria-label'),
                        class: el.className,
                        role: el.getAttribute('role'),
                        xpath: generateXPath(el),
                        preceding_text: getPrecedingText(el)
                    })),
                    'links': Array.from(document.querySelectorAll('a, [role="link"]')).map(el => ({
                        tag: el.tagName,
                        href: el.href,
                        text: el.innerText,
                        'aria-label': el.getAttribute('aria-label'),
                        class: el.className,
                        role: el.getAttribute('role'),
                        xpath: generateXPath(el),
                        preceding_text: getPrecedingText(el)
                    }))
                };

                function getPrecedingText(element) {
                    let previousNode = element.previousSibling;
                    while (previousNode && previousNode.nodeType === 3 && previousNode.textContent.trim() === '') {
                        previousNode = previousNode.previousSibling;
                    }
                    return previousNode && previousNode.nodeType === 3 ? previousNode.textContent.trim() : '';
                }

                function generateXPath(element) {

                    if (element.id)
                        return `//*[@id="${element.id}"]`;
                        
                    if (element.getAttribute('aria-label'))
                        return `//*[@aria-label="${element.getAttribute('aria-label')}"]`;
                        
                    if (element.placeholder)
                        return `//*[@placeholder="${element.placeholder}"]`;
                        
                    if (element.innerText && element.innerText.trim())
                        return `//*[text()="${element.innerText.trim()}"]`;
                        
                    let path = [];
                    if (element.type) path.push(`@type="${element.type}"`);
                    if (element.name) path.push(`@name="${element.name}"`);
                    if (element.className) path.push(`contains(@class, "${element.className}")`);
                    
                    if (path.length > 0)
                        return `//*[${path.join(' and ')}]`;
                        
                    return getFullXPath(element);
                }

                function getFullXPath(element) {
                    if (element.tagName === 'HTML')
                        return '/HTML[1]';
                    if (element === document.body)
                        return '/HTML[1]/BODY[1]';

                    let ix = 0;
                    let siblings = element.parentNode.childNodes;

                    for (let i = 0; i < siblings.length; i++) {
                        let sibling = siblings[i];
                        if (sibling === element)
                            return getFullXPath(element.parentNode) + '/' + element.tagName + '[' + (ix + 1) + ']';
                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName)
                            ix++;
                    }
                }
            """
            
            page_elements = self.driver.execute_script(elements_script)
            return page_elements
            
        except Exception as e:
            self.logger.error(f"Failed to get page elements: {str(e)}")
            return {}

    def filter_relevant_elements(self, page_elements: Dict, step_description: str) -> Dict:
        """Filter and limit elements based on the step description"""
        step = step_description.lower()
        filtered = {"inputs": [], "buttons": [], "links": []}
        
        # Extract key terms from step
        terms = step.replace("click on", "").replace("enter", "").replace("type", "").replace("in the", "").replace("field", "").strip().split()
        
        for element_type, elements in page_elements.items():
            for element in elements:
                element_text = json.dumps(element).lower()
                if any(term.lower() in element_text for term in terms):
                    filtered[element_type].append(element)
                    
                # Check preceding text and labels
                if element.get('preceding_text') and any(term.lower() in element['preceding_text'].lower() for term in terms):
                    filtered[element_type].append(element)
                if element.get('label') and any(term.lower() in element['label'].lower() for term in terms):
                    filtered[element_type].append(element)
        
        return filtered

    def analyze_elements_for_action(self, step_description: str, page_elements: Dict) -> Dict:
        """
        Use AI to analyze page elements and determine the best element for the action
        """
        try:
            # Filter relevant elements first
            filtered_elements = self.filter_relevant_elements(page_elements, step_description)
            
            prompt = f"""
            Analyze these relevant page elements for the step: "{step_description}"

            Available elements:
            {json.dumps(filtered_elements, indent=2)}

            Return a JSON response in this format:
            {{
                "action_type": "navigate|input|click",
                "selected_element": {{
                    "xpath": "xpath of the selected element",
                    "css": "css selector of the selected element",
                    "reason": "why this element was selected"
                }},
                "input_value": "value to input if applicable",
                "wait_time": recommended wait time in seconds
            }}

            For search inputs, prefer elements with id 'twotabsearchtextbox' or search-related attributes.
            For clicks, prefer elements with matching text or relevant attributes.
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )

            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            self.logger.error(f"Failed to analyze elements: {str(e)}")
            if "context_length_exceeded" in str(e):
                # Fallback to basic element finding for common scenarios
                if "search" in step_description.lower():
                    return {
                        "action_type": "input",
                        "selected_element": {
                            "xpath": "//input[@id='twotabsearchtextbox']",
                            "css": "#twotabsearchtextbox",
                            "reason": "Amazon search box"
                        },
                        "input_value": step_description.lower().replace("search for", "").replace("in the search bar", "").strip().strip("'"),
                        "wait_time": 2
                    }
                elif "first link" in step_description.lower():
                    return {
                        "action_type": "click",
                        "selected_element": {
                            "xpath": "(//div[@data-component-type='s-search-result']//h2//a)[1]",
                            "css": "div[data-component-type='s-search-result'] h2 a",
                            "reason": "First search result"
                        },
                        "wait_time": 2
                    }
            raise

    def analyze_step(self, step_description: str) -> Dict:
        """
        Use AI to analyze the step and determine required action
        """
        try:
            prompt = f"""
            Analyze this test step and provide a detailed action plan:
            "{step_description}"

            Return a JSON object with exactly this structure (no additional text):
            {{
                "action_type": "navigate|input|click|select|hover|wait|verify",
                "element_type": "input|button|link|select|div|etc",
                "element_identification": {{
                    "primary_attributes": ["id", "name", "type"],
                    "text_content": "expected text if any",
                    "contextual_hints": ["search", "submit", "next"]
                }},
                "input_value": "value to input if needed",
                "wait_conditions": ["presence", "clickable", "visible"],
                "expected_result": "what should happen after action",
                "fallback_strategies": ["try alternative locators", "check similar elements"]
            }}
            
            Important: Return ONLY the JSON object, no additional text or explanations.
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a JSON generator that only returns valid JSON objects without any additional text or explanations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            # Clean the response to ensure it's valid JSON
            response_text = response.choices[0].message.content.strip()
            # Remove any potential markdown code block markers
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response: {response_text}")
                # Fallback analysis for common actions
                return self.fallback_step_analysis(step_description)

        except Exception as e:
            self.logger.error(f"Failed to analyze step: {str(e)}")
            return self.fallback_step_analysis(step_description)

    def fallback_step_analysis(self, step_description: str) -> Dict:
        """
        Fallback method for step analysis when AI fails
        """
        step = step_description.lower()
        
        # Navigation action
        if step.startswith("navigate to"):
            return {
                "action_type": "navigate",
                "element_type": "browser",
                "element_identification": {
                    "primary_attributes": [],
                    "text_content": "",
                    "contextual_hints": ["navigation"]
                },
                "input_value": "",
                "wait_conditions": ["complete"],
                "expected_result": "page loads successfully",
                "fallback_strategies": []
            }
        
        # Click action
        if step.startswith("click"):
            target = step.replace("click", "").replace("on", "").replace("the", "").strip()
            return {
                "action_type": "click",
                "element_type": "any",
                "element_identification": {
                    "primary_attributes": ["id", "name", "type"],
                    "text_content": target,
                    "contextual_hints": [target, "clickable"]
                },
                "input_value": "",
                "wait_conditions": ["clickable"],
                "expected_result": "element is clicked",
                "fallback_strategies": ["try by text", "try by aria-label"]
            }
        
        # Input action
        if "enter" in step or "type" in step or "input" in step:
            # Extract the value to input (text between quotes if present)
            import re
            value_match = re.search(r"'([^']*)'", step)
            input_value = value_match.group(1) if value_match else ""
            
            return {
                "action_type": "input",
                "element_type": "input",
                "element_identification": {
                    "primary_attributes": ["id", "name", "type"],
                    "text_content": "",
                    "contextual_hints": ["input", "textbox", "field"]
                },
                "input_value": input_value,
                "wait_conditions": ["visible", "enabled"],
                "expected_result": "text is entered successfully",
                "fallback_strategies": ["try by placeholder", "try by label text"]
            }
        
        # Default fallback
        return {
            "action_type": "click",
            "element_type": "any",
            "element_identification": {
                "primary_attributes": ["id", "name", "type"],
                "text_content": step,
                "contextual_hints": ["interactive"],
                "fallback_strategies": ["try all available locators"]
            },
            "wait_conditions": ["visible", "enabled"],
            "expected_result": "action completed",
            "fallback_strategies": ["try alternative elements"]
        }

    def generate_element_locators(self, action_plan: Dict, page_elements: Dict) -> Dict:
        """
        Use AI to generate optimal locators based on action plan and available elements
        """
        try:
            prompt = f"""
            Generate optimal element locators based on this action plan and available page elements.

            Action Plan:
            {json.dumps(action_plan, indent=2)}

            Available Page Elements:
            {json.dumps(page_elements, indent=2)}

            Return a JSON with locator strategies in priority order:
            {{
                "locators": {{
                    "id": "id value if available",
                    "xpath": ["primary xpath", "fallback xpath"],
                    "css": ["primary css", "fallback css"],
                    "custom": "any other unique locator strategy"
                }},
                "confidence_score": 0.0 to 1.0,
                "verification_attributes": ["attributes to verify correct element"]
            }}
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            self.logger.error(f"Failed to generate locators: {str(e)}")
            raise

    def verify_element_match(self, element, action_plan: Dict, locator_info: Dict) -> bool:
        """
        Use AI to verify if found element matches the intended target
        """
        try:
            element_attributes = self.get_element_info(element)
            
            prompt = f"""
            Verify if this element matches the intended target.

            Action Plan:
            {json.dumps(action_plan, indent=2)}

            Found Element:
            {json.dumps(element_attributes, indent=2)}

            Verification Attributes:
            {json.dumps(locator_info.get('verification_attributes', []), indent=2)}

            Return a JSON response:
            {{
                "is_match": true/false,
                "confidence": 0.0 to 1.0,
                "reason": "explanation of decision"
            }}
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)
            return result["is_match"] and result["confidence"] > 0.7

        except Exception as e:
            self.logger.error(f"Failed to verify element match: {str(e)}")
            return False

    def execute_step(self, step_description: str):
        """
        Execute a test step using AI for analysis and execution
        """
        try:
            # Analyze the step
            action_plan = self.analyze_step(step_description)
            
            # Handle navigation separately
            if action_plan["action_type"] == "navigate":
                url = step_description.replace("navigate to", "").strip().strip("'")
                self.driver.get(url)
                self.record_action("navigate", {"url": url}, {"url": url})
                time.sleep(2)
                return

            # Add wait for page stability
            self.wait_for_page_stability()

            # Get page elements
            page_elements = self.get_page_elements()
            
            # Generate locators
            locator_info = self.generate_element_locators(action_plan, page_elements)
            
            # Try to find element with retries
            max_retries = 3
            retry_count = 0
            element = None
            
            while retry_count < max_retries and not element:
                try:
                    # Try to find element using generated locators
                    for locator_type, locator_value in locator_info["locators"].items():
                        if isinstance(locator_value, list):
                            for loc in locator_value:
                                element = self.element_finder.find_element_by_locators({locator_type: loc})
                                if element and self.verify_element_match(element, action_plan, locator_info):
                                    break
                        else:
                            element = self.element_finder.find_element_by_locators({locator_type: locator_value})
                            if element and self.verify_element_match(element, action_plan, locator_info):
                                break
                    
                    if not element:
                        # Try alternative strategies if element not found
                        element = self.try_alternative_strategies(step_description, action_plan)
                    
                    if not element:
                        retry_count += 1
                        time.sleep(1)  # Wait before retry
                        # Refresh page elements for next attempt
                        page_elements = self.get_page_elements()
                        locator_info = self.generate_element_locators(action_plan, page_elements)
                except Exception as e:
                    self.logger.debug(f"Retry {retry_count + 1} failed: {str(e)}")
                    retry_count += 1
                    time.sleep(1)

            if not element:
                raise ElementNotFoundError(f"Could not find matching element for: {step_description}")

            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)  # Small delay after scroll

            # Execute action based on type
            if action_plan["action_type"] == "input":
                element.clear()
                input_value = action_plan.get("input_value", "").strip("'")
                element.send_keys(input_value)
                if any(hint in step_description.lower() for hint in ["search", "submit", "enter"]):
                    element.send_keys(Keys.RETURN)
                
            elif action_plan["action_type"] == "click":
                # Ensure element is clickable
                self.wait_for_element_clickable(element)
                try:
                    element.click()
                except:
                    # Fallback to JavaScript click if regular click fails
                    self.driver.execute_script("arguments[0].click();", element)
                
            # Record the action
            self.record_action(
                action_plan["action_type"],
                self.get_element_info(element),
                locator_info["locators"]
            )

            # Wait for any page updates after action
            self.wait_for_page_stability()

            self.logger.info(f"Successfully executed step: {step_description}")
            
        except Exception as e:
            self.logger.error(f"Failed to execute step '{step_description}': {str(e)}")
            raise

    def wait_for_page_stability(self, timeout: int = 10):
        """Wait for page to become stable"""
        try:
            # Wait for document ready state
            self.driver.execute_script("""
                return new Promise(resolve => {
                    if (document.readyState === 'complete') {
                        resolve();
                    } else {
                        window.addEventListener('load', resolve);
                    }
                });
            """)
            
            # Wait for any AJAX requests to complete
            self.driver.execute_script("""
                return new Promise(resolve => {
                    const observer = new MutationObserver(mutations => {
                        if (!document.querySelector('.loading, .spinner, .wait')) {
                            observer.disconnect();
                            resolve();
                        }
                    });
                    observer.observe(document.body, {
                        childList: true,
                        subtree: true,
                        attributes: true
                    });
                    // Resolve anyway after 2 seconds
                    setTimeout(resolve, 2000);
                });
            """)
        except Exception as e:
            self.logger.debug(f"Wait for stability failed: {str(e)}")

    def wait_for_element_clickable(self, element, timeout: int = 10):
        """Wait for element to become clickable"""
        try:
            end_time = time.time() + timeout
            while time.time() < end_time:
                if element.is_displayed() and element.is_enabled():
                    return True
                time.sleep(0.5)
            return False
        except Exception as e:
            self.logger.debug(f"Wait for clickable failed: {str(e)}")
            return False

    def try_alternative_strategies(self, step_description: str, action_plan: Dict) -> Optional[object]:
        """Try alternative strategies to find element"""
        try:
            step = step_description.lower()
            
            # For login-related elements
            if "login" in step:
                login_xpaths = [
                    "//button[contains(translate(., 'LOGIN', 'login'), 'login')]",
                    "//input[@type='submit'][contains(translate(., 'LOGIN', 'login'), 'login')]",
                    "//a[contains(translate(., 'LOGIN', 'login'), 'login')]",
                    "//button[@type='submit'][last()]",  # Often the last submit button is login
                    "//form[contains(@action, 'login')]//button[@type='submit']"
                ]
                
                for xpath in login_xpaths:
                    try:
                        element = self.element_finder.find_element_by_locators({"xpath": xpath})
                        if element:
                            return element
                    except:
                        continue
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Alternative strategies failed: {str(e)}")
            return None

    def get_element_info(self, element) -> Dict:
        """Get element information"""
        try:
            # Simplified element data collection to reduce tokens
            element_data = {
                "tag": element.tag_name,
                "id": element.get_attribute("id"),
                "class": element.get_attribute("class"),
                "type": element.get_attribute("type"),
                "name": element.get_attribute("name"),
                "text": element.text,
                "aria-label": element.get_attribute("aria-label")
            }
            
            # Filter out None values
            element_data = {k: v for k, v in element_data.items() if v}
            
            return element_data
            
        except Exception as e:
            self.logger.error(f"Failed to get element info: {str(e)}")
            return {}

    def generate_locators(self, element_info: Dict) -> Dict[str, str]:
        """
        Generate locators using AI based on element information
        
        Args:
            element_info (Dict): Element information
            
        Returns:
            Dict[str, str]: Generated locators
        """
        try:
            prompt = f"""
            Generate robust and unique locators for this element:
            {json.dumps(element_info, indent=2)}
            
            Return a JSON with these locator strategies:
            1. XPath - prefer unique attributes and text
            2. CSS Selector - compact and efficient
            3. ID - if available and unique
            
            Consider:
            - Reliability across page updates
            - Performance of the locator
            - Uniqueness in the page context
            - Readability for maintenance
            
            Return only the JSON response.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            
            locators = json.loads(response.choices[0].message.content)
            self.logger.info("Successfully generated locators")
            return locators
            
        except Exception as e:
            self.logger.error(f"Failed to generate locators: {str(e)}")
            return {}

    def run_test_steps(self, steps: List[str]):
        """
        Run a list of test steps
        
        Args:
            steps (List[str]): List of step descriptions to execute
        """
        try:
            for step in steps:
                self.logger.info(f"Executing step: {step}")
                self.execute_step(step)
                # Add small delay between steps
                time.sleep(2)
        except Exception as e:
            self.logger.error(f"Test execution failed: {str(e)}")
            raise

    def save_script(self, script: str, filename: str = None):
        """Save generated script to file"""
        if filename is None:
            timestamp = generate_timestamp()
            filename = f"test_script_{timestamp}.py"
        
        filename = sanitize_filename(filename)
        filepath = os.path.join(Config.SCRIPT_OUTPUT_DIR, filename)
        
        try:
            os.makedirs(Config.SCRIPT_OUTPUT_DIR, exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(script)
            self.logger.info(f"Script saved to {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Failed to save script: {str(e)}")
            raise 

    def navigate_to_url(self, url: str):
        """
        Navigate to the specified URL
        
        Args:
            url (str): The URL to navigate to
        """
        try:
            self.driver.get(url)
            # Record the navigation action
            self.record_action("navigate", {"url": url}, {"url": url})
            self.logger.info(f"Navigated to URL: {url}")
        except Exception as e:
            self.logger.error(f"Failed to navigate to URL: {str(e)}")
            raise

    def record_action(self, action_type: str, element_info: Dict, locators: Dict[str, str]):
        """
        Record an automation action
        
        Args:
            action_type (str): Type of action (click, input, navigate, etc.)
            element_info (Dict): Element information
            locators (Dict[str, str]): Generated locators
        """
        try:
            action = {
                "type": action_type,
                "element_info": element_info,
                "locators": locators,
                "timestamp": datetime.datetime.now().isoformat()
            }
            self.actions.append(action)
            self.logger.info(f"Recorded action: {action_type}")
        except Exception as e:
            self.logger.error(f"Failed to record action: {str(e)}")
            raise 

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
            if not self.actions:
                raise ScriptGenerationError("No actions recorded to generate script")

            # Use the script generator to create the script
            script = self.script_generator.generate_script(self.actions, framework)
            self.logger.info(f"Successfully generated {framework} script in {language}")
            return script

        except Exception as e:
            self.logger.error(f"Failed to generate script: {str(e)}")
            raise ScriptGenerationError(f"Script generation failed: {str(e)}") 

    def cleanup(self):
        """
        Clean up resources and close the browser
        """
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
            self.logger.info("Cleanup completed successfully")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            raise 