import logging
from datetime import datetime

def setup_logger(name: str, log_file: str) -> logging.Logger:
    """Set up logger with file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(levelname)s: %(message)s')
    )
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def generate_timestamp() -> str:
    """Generate a formatted timestamp"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters"""
    return "".join(c for c in filename if c.isalnum() or c in ('-', '_')).rstrip() 