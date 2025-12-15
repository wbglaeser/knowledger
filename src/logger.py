"""
Centralized logging configuration for Knowledger.
"""
import logging

# Configure logging once for the entire application
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given module name.
    
    Args:
        name: The name of the module (typically __name__)
    
    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)
