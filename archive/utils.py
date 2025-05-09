"""
Hjälpfunktioner och loggning för Tradingbot
"""
import logging
import pytz
import csv
import pandas as pd
from datetime import datetime
import random

class TerminalColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    GREEN = '\033[32m'
    RED = '\033[31m'
    YELLOW = '\033[33m'
    CYAN = '\033[36m'
    MAGENTA = '\033[35m'
    WHITE = '\033[37m'
    GREY = '\033[90m'

class StructuredLogger:
    def __init__(self, name: str = "TradingBot"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

    def info(self, msg):
        self.logger.info(msg)

    def error(self, msg):
        self.logger.error(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def debug(self, msg):
        self.logger.debug(msg)

    def trade(self, msg):
        print(f"{TerminalColors.OKGREEN}[TRADE]{TerminalColors.ENDC} {msg}")

    def order(self, msg):
        print(f"{TerminalColors.OKBLUE}[ORDER]{TerminalColors.ENDC} {msg}")

    def notification(self, msg):
        print(f"{TerminalColors.OKCYAN}[NOTIFY]{TerminalColors.ENDC} {msg}")

    def websocket(self, msg):
        print(f"{TerminalColors.MAGENTA}[WS]{TerminalColors.ENDC} {msg}")

    def separator(self, char="-", length=40):
        print(char * length)

# Global log instance for convenience
log = StructuredLogger()

# Andra hjälpfunktioner, t.ex. symbolhantering

def ensure_paper_trading_symbol(symbol):
    """
    Konverterar symboler till korrekt Bitfinex paper trading format (tTESTXXX:TESTYYY)
    Exempel:
    - 'BTC/USD' -> 'tTESTBTC:TESTUSD'
    - 'tBTCUSD' -> 'tTESTBTC:TESTUSD'
    - 'tTESTBTC:TESTUSD' -> 'tTESTBTC:TESTUSD' (ingen förändring)
    """
    if symbol.startswith('tTEST'):
        return symbol
    if '/' in symbol:
        base, quote = symbol.split('/')
        return f"tTEST{base}:TEST{quote}"
    if symbol.startswith('t') and not symbol.startswith('tTEST'):
        return f"tTEST{symbol[1:]}"
    # Fallback
    print(f"Varning: Okänt symbolformat: {symbol}, försöker lägga till TEST-prefix")
    return f"tTEST{symbol}"

import functools
import time as _time

def retry(max_attempts=3, initial_delay=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts:
                        raise
                    _time.sleep(delay)
                    delay *= 2
        return wrapper
    return decorator

def get_next_nonce():
    """Returnerar ett monotont ökande nonce-värde."""
    return int(_time.time() * 1000) + random.randint(0, 999)

def timestamp_nonce():
    """Returnerar en tidsstämplad nonce."""
    return f"{int(_time.time())}-{random.randint(1000,9999)}"

def convert_to_local_time(ts, tz):
    """Konverterar UTC-timestamp till lokal tidzon."""
    utc_dt = datetime.utcfromtimestamp(ts).replace(tzinfo=pytz.utc)
    local_dt = utc_dt.astimezone(pytz.timezone(tz))
    return local_dt

def export_to_csv(data, path):
    """Exporterar lista av dicts till CSV."""
    if not data:
        return
    with open(path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

def export_to_excel(data, path):
    """Exporterar lista av dicts till Excel."""
    if not data:
        return
    df = pd.DataFrame(data)
    df.to_excel(path, index=False)
