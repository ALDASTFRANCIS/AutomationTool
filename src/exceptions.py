class AutomationError(Exception):
    """Base exception for automation errors"""
    pass

class BrowserInitializationError(AutomationError):
    """Raised when browser initialization fails"""
    pass

class ElementNotFoundError(AutomationError):
    """Raised when element cannot be found"""
    pass

class ScriptGenerationError(AutomationError):
    """Raised when script generation fails"""
    pass 