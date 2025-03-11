import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    LOG_FILE = 'logs/automation.log'
    SCRIPT_OUTPUT_DIR = 'generated_scripts'
    DEFAULT_TIMEOUT = 10
    DEFAULT_FRAMEWORK = 'selenium'
    DEFAULT_LANGUAGE = 'python' 