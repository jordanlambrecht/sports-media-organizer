# src/custom_logger.py
import logging
import os
from rich.logging import RichHandler
from rich import print as console_print
from rich.traceback import install as rich_traceback_install
from logging.handlers import RotatingFileHandler
from datetime import datetime
import yaml

# Enable Rich's pretty tracebacks globally
rich_traceback_install(show_locals=True)


class Logger:
    """
    Custom logger class that provides a centralized logging system with Rich-enhanced
    console output, file logging, log rotation, and optional emoji usage per message.
    """

    EMOJIS = {
        "DEBUG": "🐛",
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "🔥",
    }

    COLOR_MAP = {
        "DEBUG": "green",
        "INFO": "blue",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold red",
    }

    DEFAULT_CONFIG = {
        "log_file": "sports_organizer.log",
        "log_rotation": True,
        "max_log_size_kb": 1024,
        "backup_count": 5,
        "console_log_level": "INFO",
        "file_log_level": "DEBUG",
        "use_emojis": True,
        "prepend_log_level_labels": True,
        "noConsole": False,  # Global default to allow console logging
    }

    def __init__(self, config_path="configs/config.yaml"):
        """
        Initializes the Logger instance by loading configuration from a YAML file.
        Falls back to default settings if the config file is missing or invalid.
        """
        # Load configuration from config.yaml or use defaults
        self.config = self.load_config(config_path)

        # Set log directory and file name
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Log file named with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = os.path.join(log_dir, f"{timestamp}.log")

        # Create logger instance
        self.logger = logging.getLogger("sports_media_organizer")
        self.logger.setLevel(
            logging.DEBUG
        )  # Overall logging level (handlers filter their own levels)

        # Set up file handler with log rotation
        self.file_log_level = getattr(
            logging, self.config.get("file_log_level", "DEBUG").upper(), logging.DEBUG
        )
        max_log_size_bytes = self.config.get("max_log_size_kb", 1024) * 1024
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_log_size_bytes,
            backupCount=self.config.get("backup_count", 5),
        )
        file_handler.setLevel(self.file_log_level)

        # Define log formats for both console and file
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Conditionally add console handler if noConsole is False
        if not self.config.get("noConsole", False):
            self.console_log_level = getattr(
                logging,
                self.config.get("console_log_level", "INFO").upper(),
                logging.INFO,
            )
            console_handler = RichHandler(show_path=False, markup=True)
            console_handler.setLevel(self.console_log_level)

            # Define console format
            console_formatter = logging.Formatter("%(message)s")
            console_handler.setFormatter(console_formatter)

            # Add console handler to the logger
            self.logger.addHandler(console_handler)

    def load_config(self, config_path):
        """
        Loads the logging configuration from the provided YAML file.
        Falls back to default settings if the file is missing or invalid.

        Args:
        config_path (str): Path to the configuration file.

        Returns:
        dict: The loaded configuration settings or defaults.
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or self.DEFAULT_CONFIG
        except Exception as e:
            console_print(
                f"[bold red]Failed to load configuration from {config_path}: {e}. Using default settings.[/bold red]"
            )
            return self.DEFAULT_CONFIG

    def format_console_message(
        self, level, message, use_emojis=True, prepend_label=True
    ):
        """
        Formats log messages for console output with optional emojis and colors based on log level.
        """
        label = ""
        if prepend_label and self.config.get("prepend_log_level_labels", True):
            if level in ["ERROR", "WARNING", "CRITICAL"]:
                label = f"{level}: "

        if use_emojis and self.config.get("use_emojis", True):
            emoji = self.EMOJIS.get(level, "")
            color = self.COLOR_MAP.get(level, "white")
            return f"[{color}]{emoji} {label}{message}[/{color}]"

        return f"{label}{message}"

    def log_message(
        self,
        level,
        message,
        use_emojis=True,
        prepend_label=True,
        noConsole=False,
        **kwargs,
    ):
        """
        Unified log message handler to be called by log methods like debug, info, etc.
        Logs to both file and console unless `noConsole=True`.
        """
        formatted_message = self.format_console_message(
            level, message, use_emojis, prepend_label
        )

        # Print to console only if noConsole is False
        if not noConsole:
            console_print(formatted_message, **kwargs)

        # Log the message to the file
        log_method = getattr(self.logger, level.lower())
        log_method(message)

    def debug(
        self, message, use_emojis=True, prepend_label=True, noConsole=False, **kwargs
    ):
        self.log_message(
            "DEBUG", message, use_emojis, prepend_label, noConsole, **kwargs
        )

    def info(
        self, message, use_emojis=True, prepend_label=False, noConsole=False, **kwargs
    ):
        self.log_message(
            "INFO", message, use_emojis, prepend_label, noConsole, **kwargs
        )

    def warning(
        self, message, use_emojis=True, prepend_label=True, noConsole=False, **kwargs
    ):
        self.log_message(
            "WARNING", message, use_emojis, prepend_label, noConsole, **kwargs
        )

    def error(
        self, message, use_emojis=True, prepend_label=True, noConsole=False, **kwargs
    ):
        self.log_message(
            "ERROR", message, use_emojis, prepend_label, noConsole, **kwargs
        )

    def critical(
        self, message, use_emojis=True, prepend_label=True, noConsole=False, **kwargs
    ):
        self.log_message(
            "CRITICAL", message, use_emojis, prepend_label, noConsole, **kwargs
        )


# Singleton pattern to ensure one logger instance
logger_instance = None


def get_logger():
    """
    Retrieves a singleton instance of the logger to ensure only one logger is used
    throughout the application.

    Returns:
    Logger: The singleton logger instance.
    """
    global logger_instance
    if not logger_instance:
        logger_instance = Logger().logger  # Access the .logger attribute directly
    return logger_instance


# Create an instance of Logger for direct use
log = Logger()
