# File: src/custom_logger.py

import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from collections.abc import Mapping
import atexit

from rich.logging import RichHandler
from rich import print as console_print
from rich.traceback import install as rich_traceback_install
from rich.console import Console

# Enable Rich's pretty tracebacks globally
rich_traceback_install(show_locals=True)
console = Console(color_system="256")


def deep_merge(dict1: Dict[str, Any], dict2: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two dictionaries.

    Args:
        dict1 (Dict[str, Any]): Base dictionary
        dict2 (Mapping[str, Any]): Dictionary to merge into base

    Returns:
        Dict[str, Any]: Merged dictionary
    """
    for k, v in dict2.items():
        if isinstance(v, Mapping):
            dict1[k] = deep_merge(dict1.get(k, {}), v)
        else:
            dict1[k] = v
    return dict1


class Logger:
    """
    Custom logger class with Rich console output and file logging capabilities.
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
        "noConsole": False,
    }

    def __init__(self, config_path: str = "configs/config.yaml") -> None:
        """
        Initialize the Logger with configuration from a YAML file.

        Args:
            config_path (str): Path to the configuration YAML file
        """
        self.config = self.load_config(config_path)
        self.logger: logging.Logger = logging.getLogger("sports_media_organizer")
        self._setup_logger()
        atexit.register(self.close)

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from a YAML file.

        Args:
            config_path (str): Path to the configuration file

        Returns:
            Dict[str, Any]: Merged configuration dictionary
        """
        try:
            with Path(config_path).open("r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            return deep_merge(self.DEFAULT_CONFIG.copy(), config or {})
        except Exception as e:
            console.print(
                f"[bold red]Failed to load configuration from {config_path}: {e}. Using default settings.[/bold red]"
            )
            return self.DEFAULT_CONFIG.copy()

    def _setup_logger(self) -> None:
        """Set up the logger with file and console handlers."""
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = log_dir / f"{timestamp}.log"

        self.logger.setLevel(logging.DEBUG)

        self._setup_file_handler(log_file)
        self._setup_console_handler()

    def _setup_file_handler(self, log_file: Path) -> None:
        """Set up the file handler for logging."""
        self.file_log_level = getattr(
            logging, self.config.get("file_log_level", "DEBUG").upper(), logging.DEBUG
        )
        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=self.config.get("max_log_size_kb", 1024) * 1024,
            backupCount=self.config.get("backup_count", 5),
        )
        file_handler.setLevel(self.file_log_level)
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def _setup_console_handler(self) -> None:
        """Set up the console handler for logging."""
        if not self.config.get("noConsole", False):
            self.console_log_level = getattr(
                logging,
                self.config.get("console_log_level", "INFO").upper(),
                logging.INFO,
            )
            console_handler = RichHandler(show_path=False, markup=True)
            console_handler.setLevel(self.console_log_level)
            console_formatter = logging.Formatter("%(message)s")
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

    def format_console_message(
        self, level: str, message: str, use_emojis: bool, prepend_label: bool
    ) -> str:
        """
        Format the log message for console output.

        Args:
            level (str): Log level
            message (str): Log message
            use_emojis (bool): Whether to use emojis in the output
            prepend_label (bool): Whether to prepend the log level label

        Returns:
            str: Formatted log message
        """
        label = (
            f"{level}: "
            if prepend_label and level in ["ERROR", "WARNING", "CRITICAL"]
            else ""
        )
        if use_emojis and self.config.get("use_emojis", True) and level in self.EMOJIS:
            emoji = self.EMOJIS[level]
            color = self.COLOR_MAP.get(level, "white")
            return f"[{color}]{emoji} {label}{message}[/{color}]"
        return f"{label}{message}"

    def log_message(
        self,
        level: str,
        message: str,
        use_emojis: bool = True,
        prepend_label: bool = True,
        **kwargs,
    ) -> None:
        """
        Log a message at the specified level.

        Args:
            level (str): Log level
            message (str): Message to log
            use_emojis (bool): Whether to use emojis in console output
            prepend_label (bool): Whether to prepend the log level label
            **kwargs: Additional keyword arguments for Rich console print
        """
        if self.logger is None:
            console.print(
                f"[bold red]Logger not initialized. Message: {message}[/bold red]"
            )
            return

        log_level = getattr(logging, level)
        if self.logger.isEnabledFor(log_level):
            formatted_message = self.format_console_message(
                level, message, use_emojis, prepend_label
            )

            if not self.config.get("noConsole", False):
                try:
                    style = kwargs.pop("style", None)
                    if style:
                        console.print(formatted_message, style=style, **kwargs)
                    else:
                        console.print(formatted_message, **kwargs)
                except Exception as e:
                    print(f"Log message (fallback): {formatted_message}")
                    print(f"Rich console print error: {e}")

            log_method = getattr(self.logger, level.lower())
            log_method(message)

    def debug(self, message: str, **kwargs) -> None:
        """Log a debug message."""
        self.log_message("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log an info message."""
        self.log_message("INFO", message, prepend_label=False, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log a warning message."""
        self.log_message("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log an error message."""
        self.log_message("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log a critical message."""
        self.log_message("CRITICAL", message, **kwargs)

    def close(self) -> None:
        """Close all handlers and clean up resources."""
        if self.logger:
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)


class SingletonLogger:
    """Singleton class to ensure only one Logger instance is created."""

    _instance: Optional[Logger] = None

    @classmethod
    def get_instance(cls) -> Logger:
        """
        Get or create the single Logger instance.

        Returns:
            Logger: The singleton Logger instance
        """
        if cls._instance is None:
            cls._instance = Logger()
        return cls._instance


# Use this to get the logger instance
log = SingletonLogger.get_instance()
