"""
Logging utilities for iONspID.

This module provides a comprehensive logging system with hierarchical loggers,
configurable outputs, and log rotation.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union
import yaml
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install as rich_traceback_install

# Default log format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# More detailed format for file logging
DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"

# Define log levels with user-friendly names
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}


class LogManager:
    """
    Centralized logging manager for iONspID.
    
    This class provides a singleton interface for configuring and managing
    application-wide logging settings.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.root_logger = logging.getLogger("ionspid")
        self.root_logger.setLevel(logging.INFO)
        self.handlers = {}
        
        # Set up default console handler
        self._setup_console_handler()
        
    def _setup_console_handler(self):
        """Set up the default console handler with rich integration."""
        console = Console()
        rich_traceback_install(console=console, show_locals=True)
        console_handler = RichHandler(console=console, show_time=True, show_level=True, show_path=True, rich_tracebacks=True)
        console_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
        self.root_logger.addHandler(console_handler)
        self.handlers["console"] = console_handler
    
    def setup_file_logging(self, log_dir: Union[str, Path], 
                          log_file: str = "ionspid.log",
                          max_size: int = 10 * 1024 * 1024,  # 10 MB
                          backup_count: int = 5) -> None:
        """
        Set up file-based logging with rotation.
        
        Args:
            log_dir: Directory to store log files
            log_file: Name of the log file
            max_size: Maximum size of each log file in bytes
            backup_count: Number of backup files to keep
        """
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_path = log_dir / log_file
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=max_size, backupCount=backup_count
        )
        file_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))
        self.root_logger.addHandler(file_handler)
        self.handlers["file"] = file_handler
        
    def setup_syslog(self, address='/dev/log', facility=logging.handlers.SysLogHandler.LOG_USER):
        """Set up syslog handler."""
        syslog_handler = logging.handlers.SysLogHandler(address=address, facility=facility)
        syslog_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
        self.root_logger.addHandler(syslog_handler)
        self.handlers["syslog"] = syslog_handler

    def configure_from_yaml(self, config_path: Union[str, Path]):
        """Configure logging from a YAML file."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        # Example config: {console_level: 'info', file_level: 'debug', log_dir: 'logs', ...}
        self.set_global_level(config.get('console_level', 'info'))
        if config.get('log_dir'):
            self.setup_file_logging(config['log_dir'])
        if config.get('syslog'):
            self.setup_syslog(**config['syslog'])
        if 'module_levels' in config:
            self.configure_log_levels(config['module_levels'])


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    This is the primary function for getting loggers throughout the application.
    It ensures that all loggers are properly configured through the LogManager.
    
    Args:
        name: Logger name, typically __name__ from the calling module
        
    Returns:
        Configured logger instance
    """
    # Ensure the log manager is initialized
    LogManager()
    
    # If the name doesn't start with 'ionspid', prefix it
    if not name.startswith("ionspid"):
        if name == "__main__":
            name = "ionspid.main"
        else:
            name = f"ionspid.{name}"
    
    return logging.getLogger(name)


def configure_logging(log_dir: Optional[Union[str, Path]] = None,
                     console_level: str = "info",
                     file_level: str = "debug",
                     module_levels: Optional[Dict[str, str]] = None,
                     config_file: Optional[Union[str, Path]] = None) -> None:
    """
    Configure the logging system with common settings or from a config file.
    
    This is a convenience function for setting up logging with common parameters.
    
    Args:
        log_dir: Directory for log files, if None, file logging is disabled
        console_level: Log level for console output
        file_level: Log level for file output
        module_levels: Dictionary of module-specific log levels
        config_file: Path to a YAML configuration file
    """
    log_manager = LogManager()
    if config_file:
        log_manager.configure_from_yaml(config_file)
        return
    
    # Set console level
    if console_level.lower() in LOG_LEVELS:
        console_handler = log_manager.handlers.get("console")
        if console_handler:
            console_handler.setLevel(LOG_LEVELS[console_level.lower()])
    
    # Set up file logging if directory is provided
    if log_dir is not None:
        log_manager.setup_file_logging(log_dir)
        if file_level.lower() in LOG_LEVELS:
            file_handler = log_manager.handlers.get("file")
            if file_handler:
                file_handler.setLevel(LOG_LEVELS[file_level.lower()])
    
    # Configure module-specific levels
    if module_levels:
        log_manager.configure_log_levels(module_levels)
