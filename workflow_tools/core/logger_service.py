"""Logging service without global state.

WARNING: This entire file appears to be DEAD CODE as of the latest refactoring.
- LoggerService is not used anywhere (only imported by unused error_handler.py)
- WorkflowPrinter here is a duplicate of the one in common.py (everyone uses common.py version)  
- FlushingFileHandler here is also duplicated in common.py
- The WorkflowPrinter in common.py uses print_debug() while this one uses debug_print()

This file is kept only because it's exported by core/__init__.py and removing it might
break imports. Consider removing this file and error_handler.py in a future cleanup.
"""

import os
import sys
import logging
import signal
import atexit
import getpass
from datetime import datetime
from pathlib import Path
from typing import Optional


class LoggerService:
    """Manages logging without global state."""
    
    _instance: Optional['LoggerService'] = None
    
    def __init__(self, log_dir: str = "logging", log_level: str = "INFO"):
        """Initialize the logger service.
        
        Args:
            log_dir: Directory for log files
            log_level: Logging level
        """
        self.log_dir = Path(log_dir)
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger = self._setup_logger()
        self.printer = WorkflowPrinter(self.logger)
        self._setup_signal_handlers()
    
    @classmethod
    def get_instance(cls, log_dir: str = "logging", log_level: str = "INFO") -> 'LoggerService':
        """Get singleton instance of logger service.
        
        Args:
            log_dir: Directory for log files
            log_level: Logging level
            
        Returns:
            LoggerService instance
        """
        if cls._instance is None:
            cls._instance = cls(log_dir, log_level)
        return cls._instance
    
    def _setup_logger(self) -> logging.Logger:
        """Set up logging to both console and timestamped file.
        
        Returns:
            Configured logger instance
        """
        # Create logging directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped log filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = self.log_dir / f"workflow_{timestamp}.log"
        
        # Create logger
        logger = logging.getLogger(f"workflow_{timestamp}")
        logger.setLevel(self.log_level)
        
        # Remove any existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter('%(message)s')
        
        # File handler with immediate flushing
        file_handler = FlushingFileHandler(str(log_filename), encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        # Console handler - for error messages only
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def flush_logs():
            """Flush all log handlers to ensure logs are written to disk."""
            for handler in self.logger.handlers:
                handler.flush()
        
        def signal_handler(signum, frame):
            """Handle signals (like Ctrl+C) to flush logs before exit."""
            flush_logs()
            sys.exit(0)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Register cleanup function to run on normal exit
        atexit.register(flush_logs)
    
    def get_logger(self) -> logging.Logger:
        """Get the logger instance.
        
        Returns:
            Logger instance
        """
        return self.logger
    
    def get_printer(self) -> 'WorkflowPrinter':
        """Get the printer instance.
        
        Returns:
            WorkflowPrinter instance
        """
        return self.printer


class FlushingFileHandler(logging.FileHandler):
    """File handler that flushes after each log entry."""
    
    def emit(self, record):
        """Emit a log record and flush immediately."""
        super().emit(record)
        self.flush()


class WorkflowPrinter:
    """Custom printer that logs to file and prints to console without duplication."""
    
    def __init__(self, logger: logging.Logger):
        """Initialize the workflow printer.
        
        Args:
            logger: Logger instance to use
        """
        self.logger = logger
        # Find the file handler to log to file only
        self.file_handler = None
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                self.file_handler = handler
                break
        # Check if verbose mode is enabled
        self.verbose_mode = os.environ.get('VERBOSE_MODE', 'false').lower() == 'true'
    
    def print(self, message: str = "", end: str = "\n"):
        """Print message to console and log to file.
        
        Args:
            message: Message to print
            end: Line ending character
        """
        # Print to console directly
        print(message, end=end)
        
        # Log to file only if we have a file handler
        if self.file_handler:
            safe_message = self._sanitize_for_logging(message)
            record = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=safe_message,
                args=(),
                exc_info=None
            )
            self.file_handler.emit(record)
    
    def input(self, prompt: str) -> str:
        """Get user input and log both prompt and response.
        
        Args:
            prompt: Input prompt to display
            
        Returns:
            User input string
        """
        # Log the prompt to file only
        if self.file_handler:
            safe_prompt = self._sanitize_for_logging(prompt)
            prompt_record = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"PROMPT: {safe_prompt}",
                args=(),
                exc_info=None
            )
            self.file_handler.emit(prompt_record)
        
        try:
            response = input(prompt)
            # Sanitize the actual response to prevent encoding issues downstream
            clean_response = response.encode('utf-8', errors='replace').decode('utf-8')
            
            # Log the response to file only
            if self.file_handler:
                safe_response = self._sanitize_for_logging(clean_response)
                response_record = logging.LogRecord(
                    name=self.logger.name,
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=f"USER INPUT: {safe_response}",
                    args=(),
                    exc_info=None
                )
                self.file_handler.emit(response_record)
            return clean_response
        except (EOFError, KeyboardInterrupt):
            # Log the interruption to file only
            if self.file_handler:
                interrupt_record = logging.LogRecord(
                    name=self.logger.name,
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg="USER INPUT: [Interrupted]",
                    args=(),
                    exc_info=None
                )
                self.file_handler.emit(interrupt_record)
            raise
    
    def debug_print(self, message: str = "", end: str = "\n"):
        """Print debug message only in verbose mode. Always logs to file.
        
        Args:
            message: Debug message to print
            end: Line ending character
        """
        # Always log to file
        if self.file_handler:
            safe_message = self._sanitize_for_logging(message)
            record = logging.LogRecord(
                name=self.logger.name,
                level=logging.DEBUG,
                pathname="",
                lineno=0,
                msg=f"[DEBUG] {safe_message}",
                args=(),
                exc_info=None
            )
            self.file_handler.emit(record)
        
        # Only print to console in verbose mode
        if self.verbose_mode:
            print(message, end=end)
    
    def _sanitize_for_logging(self, text: str) -> str:
        """Sanitize text to prevent Unicode encoding errors in logging.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        try:
            # Try to encode/decode to catch any encoding issues
            sanitized = text.encode('utf-8', errors='replace').decode('utf-8')
            return sanitized
        except Exception:
            # If all else fails, return a safe representation
            return repr(text)