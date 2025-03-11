import os
import time
from src.web_automation_tool import WebAutomationTool
from src.config import Config

def main():
    # Initialize the tool
    tool = WebAutomationTool()
    
    # Define test steps
    test_steps = [
        "navigate to 'https://testautomation3.salesparrow.com/'",
        "Click on email address field",
        "Enter 'automation.test+333@surveysparrowqa.com' in the email address field",
        "Click on proceed button",
        "Click on password field",
        "Enter '231as564' in the password field",
        "Click on login button"
    ]
    
    try:
        # Initialize browser
        tool.initialize_browser()
        
        # Execute test steps
        tool.run_test_steps(test_steps)
        
        # Generate scripts for different frameworks
        selenium_script = tool.generate_script("selenium", "python")
        playwright_script = tool.generate_script("playwright", "python")
        
        # Save the generated scripts
        tool.save_script(selenium_script, "amazon_search_selenium.py")
        tool.save_script(playwright_script, "amazon_search_playwright.py")
        
        print("\nGenerated Scripts:")
        print("1. Selenium Script: generated_scripts/amazon_search_selenium.py")
        print("2. Playwright Script: generated_scripts/amazon_search_playwright.py")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        # Add a small delay before cleanup to see the final state
        time.sleep(3)
        tool.cleanup()

if __name__ == "__main__":
    main() 