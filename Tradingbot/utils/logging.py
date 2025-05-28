"""
Logging utilities for Tradingbot.
Provides structured and colorized logging functionality.
"""

import os
import logging
import traceback
import sys
from datetime import datetime


class TerminalColors:
    """ANSI-färgkoder för terminalfärgning"""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    # Text färger
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    # Ljusa färger
    LIGHT_RED = "\033[91m"
    LIGHT_GREEN = "\033[92m"
    LIGHT_YELLOW = "\033[93m"
    LIGHT_BLUE = "\033[94m"
    LIGHT_MAGENTA = "\033[95m"
    LIGHT_CYAN = "\033[96m"
    LIGHT_WHITE = "\033[97m"
    # Bakgrund
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


class StructuredLogger:
    """Wrapper över Python logger för att ge strukturerade, färgkodade meddelanden"""

    def __init__(self, logger_instance):
        self.logger = logger_instance
        # Läs miljövariabeln för att avgöra om färgad output ska användas
        self.use_colors = os.getenv("USE_COLORS", "true").lower() in (
            "true",
            "1",
            "yes",
        )
        # Läs lognivå från miljövariabel eller defaulta till INFO
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        # Sätt rotloggarens nivå
        self.logger.setLevel(getattr(logging, self.log_level))

    def _format(self, category, message, color=None):
        """Formatera meddelande med kategori och färg"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        category_str = f"[{category}]"

        if self.use_colors and color:
            return f"{color}{timestamp} {TerminalColors.BOLD}{category_str.ljust(12)}{TerminalColors.RESET}{color} {message}{TerminalColors.RESET}"
        else:
            return f"{timestamp} {category_str.ljust(12)} {message}"

    def debug(self, message, category="DEBUG"):
        """Logga debug-meddelande"""
        self.logger.debug(self._format(category, message, TerminalColors.CYAN))

    def info(self, message, category="INFO"):
        """Logga info-meddelande"""
        self.logger.info(self._format(category, message, TerminalColors.GREEN))

    def warning(self, message, category="WARNING"):
        """Logga varnings-meddelande"""
        self.logger.warning(self._format(category, message, TerminalColors.YELLOW))

    def error(self, message, category="ERROR"):
        """Logga felmeddelande"""
        self.logger.error(self._format(category, message, TerminalColors.RED))

    def critical(self, message, category="CRITICAL"):
        """Logga kritiskt meddelande"""
        self.logger.critical(self._format(category, message, TerminalColors.LIGHT_RED))

    def trade(self, message):
        """Logga ett handelsrelaterat meddelande"""
        self.logger.info(self._format("TRADE", message, TerminalColors.MAGENTA))

    def order(self, message):
        """Logga ett orderrelaterat meddelande"""
        self.logger.info(self._format("ORDER", message, TerminalColors.LIGHT_BLUE))

    def market(self, message):
        """Logga ett marknadsrelaterat meddelande"""
        self.logger.info(self._format("MARKET", message, TerminalColors.BLUE))

    def strategy(self, message):
        """Logga ett strategirelaterat meddelande"""
        self.logger.info(self._format("STRATEGY", message, TerminalColors.LIGHT_CYAN))

    def websocket(self, message):
        """Logga ett websocket-relaterat meddelande"""
        self.logger.info(
            self._format("WEBSOCKET", message, TerminalColors.LIGHT_MAGENTA)
        )

    def notification(self, message):
        """Logga ett notifikationsrelaterat meddelande"""
        self.logger.info(self._format("NOTIFY", message, TerminalColors.LIGHT_GREEN))

    def separator(self, char="-", length=80):
        """Skriv en separator i loggen"""
        if self.use_colors:
            self.logger.info(
                f"{TerminalColors.BLUE}{char * length}{TerminalColors.RESET}"
            )
        else:
            self.logger.info(char * length)


def setup_logging(log_file="tradingbot.log"):
    """
    Set up logging configuration for the application.
    
    Args:
        log_file: Path to the log file
    
    Returns:
        tuple: (logger, structured_logger) - Standard logger and structured logger instances
    """
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Capture all levels
    
    # Add handlers
    try:
        from pythonjsonlogger.json import JsonFormatter
        json_handler = logging.StreamHandler()
        json_formatter = JsonFormatter("%(asctime)s %(levelname)s %(message)s")
        json_handler.setFormatter(json_formatter)
        logger.addHandler(json_handler)
    except ImportError:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    # Add file handler for errors and info
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Set up exception handling
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception
    
    # Create structured logger
    structured_logger = StructuredLogger(logger)
    
    return logger, structured_logger