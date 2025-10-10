import logging
import sys
import os
from datetime import datetime

def setup_logging(log_level=logging.INFO, log_file=None):
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (default: INFO)
        log_file: If provided, logs will be written to this file
    """
    # Create logs directory if it doesn't exist and log_file is not specified
    if log_file is None:
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(logs_dir, f'meow_attack_{timestamp}.log')
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler (if log_file is provided)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name):
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)