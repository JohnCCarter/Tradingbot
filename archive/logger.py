"""
Strukturerad loggning och telemetri för Tradingbot
"""
import logging
import json
import sys
from datetime import datetime
from typing import Optional

class TerminalColors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    WHITE = "\033[37m"
    GREY = "\033[90m"
    CATEGORY = {
        "STRATEGY": BLUE,
        "MARKET": CYAN,
        "ORDER": GREEN,
        "WEBSOCKET": MAGENTA,
        "ERROR": RED,
        "INFO": WHITE,
        "DEBUG": GREY,
    }

class StructuredLogger:
    def __init__(self, name: str, log_file: Optional[str] = None, level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        formatter = logging.Formatter('%(message)s')
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        # File handler
        if log_file:
            fh = logging.FileHandler(log_file)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

    def log(self, category: str, message: str, extra: Optional[dict] = None, level=logging.INFO):
        color = TerminalColors.CATEGORY.get(category, TerminalColors.WHITE)
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "category": category,
            "message": message,
            "extra": extra or {}
        }
        # ANSI färg för konsol
        colored = f"{color}[{category}]{TerminalColors.RESET} {message}"
        self.logger.log(level, colored)
        # JSON-format för fil/external
        self.logger.log(level, json.dumps(log_entry))

    def info(self, category, message, extra=None):
        self.log(category, message, extra, level=logging.INFO)

    def error(self, category, message, extra=None):
        self.log(category, message, extra, level=logging.ERROR)

    def debug(self, category, message, extra=None):
        self.log(category, message, extra, level=logging.DEBUG)

# Exempel på extern logghantering (kan utökas för ELK/Graylog)
# class ExternalLogHandler(logging.Handler):
#     def emit(self, record):
#         # Skicka logg till extern endpoint
#         pass
