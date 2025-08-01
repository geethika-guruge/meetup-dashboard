"""
Centralized logging configuration for the Meetup RSVP Fetcher application.

This module provides standardized logging setup with proper formatting,
log levels, and output handling across all application modules.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import os
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        """Format log record with colors for console output."""
        if hasattr(record, 'levelname') and record.levelname in self.COLORS:
            # Add color to level name
            colored_levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
            )
            # Temporarily replace levelname for formatting
            original_levelname = record.levelname
            record.levelname = colored_levelname
            formatted = super().format(record)
            record.levelname = original_levelname
            return formatted
        return super().format(record)


class LoggingConfig:
    """Centralized logging configuration manager."""
    
    DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DETAILED_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s'
    
    @classmethod
    def setup_logging(
        cls,
        level: str = "INFO",
        log_file: Optional[str] = None,
        console_output: bool = True,
        detailed_format: bool = False,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ) -> None:
        """
        Set up comprehensive logging configuration.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional path to log file
            console_output: Whether to output logs to console
            detailed_format: Whether to use detailed log format
            max_file_size: Maximum size of log file before rotation
            backup_count: Number of backup log files to keep
        """
        # Convert string level to logging constant
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        
        # Get root logger
        root_logger = logging.getLogger()
        
        # Clear existing handlers to avoid duplicates
        root_logger.handlers.clear()
        
        # Set root logger level
        root_logger.setLevel(numeric_level)
        
        # Choose format
        log_format = cls.DETAILED_FORMAT if detailed_format else cls.DEFAULT_FORMAT
        
        # Set up console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(numeric_level)
            
            # Use colored formatter for console
            console_formatter = ColoredFormatter(log_format)
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # Set up file handler with rotation
        if log_file:
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(numeric_level)
            
            # Use standard formatter for file (no colors)
            file_formatter = logging.Formatter(log_format)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        
        # Log the configuration
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured - Level: {level}, Console: {console_output}, File: {log_file}")
    
    @classmethod
    def setup_from_config(cls, config: Dict[str, Any]) -> None:
        """
        Set up logging from configuration dictionary.
        
        Args:
            config: Configuration dictionary with logging settings
        """
        cls.setup_logging(
            level=config.get('level', 'INFO'),
            log_file=config.get('log_file'),
            console_output=config.get('console_output', True),
            detailed_format=config.get('detailed_format', False),
            max_file_size=config.get('max_file_size', 10 * 1024 * 1024),
            backup_count=config.get('backup_count', 5)
        )
    
    @classmethod
    def setup_from_environment(cls) -> None:
        """Set up logging from environment variables."""
        config = {
            'level': os.getenv('MEETUP_LOG_LEVEL', 'INFO'),
            'log_file': os.getenv('MEETUP_LOG_FILE'),
            'console_output': os.getenv('MEETUP_LOG_CONSOLE', 'true').lower() == 'true',
            'detailed_format': os.getenv('MEETUP_LOG_DETAILED', 'false').lower() == 'true',
        }
        
        # Handle numeric environment variables
        try:
            config['max_file_size'] = int(os.getenv('MEETUP_LOG_MAX_SIZE', str(10 * 1024 * 1024)))
        except ValueError:
            config['max_file_size'] = 10 * 1024 * 1024
        
        try:
            config['backup_count'] = int(os.getenv('MEETUP_LOG_BACKUP_COUNT', '5'))
        except ValueError:
            config['backup_count'] = 5
        
        cls.setup_from_config(config)
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger with the specified name.
        
        Args:
            name: Logger name (typically __name__)
            
        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)


def setup_application_logging() -> None:
    """Set up default logging configuration for the application."""
    # Default log file path
    log_dir = Path.home() / '.meetup_rsvp_fetcher' / 'logs'
    log_file = log_dir / f'meetup_rsvp_fetcher_{datetime.now().strftime("%Y%m%d")}.log'
    
    # Set up logging with environment variables or defaults
    LoggingConfig.setup_from_environment()
    
    # If no log file was specified in environment, use default
    if not os.getenv('MEETUP_LOG_FILE'):
        LoggingConfig.setup_logging(
            level=os.getenv('MEETUP_LOG_LEVEL', 'INFO'),
            log_file=str(log_file),
            console_output=True,
            detailed_format=os.getenv('MEETUP_LOG_DETAILED', 'false').lower() == 'true'
        )


# Convenience function for getting loggers
def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return LoggingConfig.get_logger(name)