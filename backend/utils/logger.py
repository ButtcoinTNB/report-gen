"""
Logger utility for the application.
Provides a consistent way to get a logger instance across the application.
"""

import logging
import os
from typing import Optional

# Set up the base logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_logger(name: str, log_level: Optional[int] = None) -> logging.Logger:
    """
    Get a logger instance with the specified name and log level.
    
    Args:
        name: Name of the logger, typically __name__ from the calling module
        log_level: Optional logging level to override the default
        
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set custom log level if provided, otherwise use the application default
    if log_level is not None:
        logger.setLevel(log_level)
    elif os.getenv('DEBUG', 'false').lower() == 'true':
        logger.setLevel(logging.DEBUG)
    
    return logger 