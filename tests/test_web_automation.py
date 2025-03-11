import unittest
from unittest.mock import MagicMock, patch
from src.web_automation_tool import WebAutomationTool
from src.exceptions import BrowserInitializationError

class TestWebAutomationTool(unittest.TestCase):
    def setUp(self):
        self.api_key = "test_api_key"
        self.tool = WebAutomationTool(self.api_key)

    def test_initialization(self):
        self.assertEqual(self.tool.api_key, self.api_key)
        self.assertIsNone(self.tool.driver)
        self.assertEqual(self.tool.actions, [])

    @patch('undetected_chromedriver.Chrome')
    def test_browser_initialization(self, mock_chrome):
        self.tool.initialize_browser()
        mock_chrome.assert_called_once()
        self.assertIsNotNone(self.tool.driver)

    @patch('undetected_chromedriver.Chrome')
    def test_browser_initialization_failure(self, mock_chrome):
        mock_chrome.side_effect = Exception("Browser failed to start")
        with self.assertRaises(BrowserInitializationError):
            self.tool.initialize_browser()

if __name__ == '__main__':
    unittest.main() 