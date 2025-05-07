from email.mime.multipart import MIMEMultipart
import os
import json
import hmac
import hashlib
import asyncio
import signal
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv():
        pass


import pandas as pd
import numpy as np
import talib
import ccxt
from websockets.sync.client import connect
import websockets
from pytz import timezone
import logging
import threading
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
import functools
from functools import lru_cache

# Lägg till enkel retry-decorator
import time as _time
from pydantic import BaseModel
# from prometheus_client import start_http_server, Summary, Counter  # Commented out Prometheus metrics as non-vital

try:
    from pythonjsonlogger.json import JsonFormatter
except ImportError:
    JsonFormatter = None
import http.server
import socketserver
import sys
from urllib.parse import urlparse

# --- Lägg till terminalutskrifter med färg och struktur ---
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
        self.use_colors = os.getenv("USE_COLORS", "true").lower() in ("true", "1", "yes")
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
        self.logger.info(self._format("WEBSOCKET", message, TerminalColors.LIGHT_MAGENTA))
    
    def notification(self, message):
        """Logga ett notifikationsrelaterat meddelande"""
        self.logger.info(self._format("NOTIFY", message, TerminalColors.LIGHT_GREEN))
    
    def separator(self, char="-", length=80):
        """Skriv en separator i loggen"""
        if self.use_colors:
            self.logger.info(f"{TerminalColors.BLUE}{char * length}{TerminalColors.RESET}")
        else:
            self.logger.info(char * length)

# Create timezone object once
LOCAL_TIMEZONE = timezone("Europe/Stockholm")

# Load environment variables (safe if python-dotenv is missing)
load_dotenv()
# Validate essential API credentials early
if not os.getenv("API_KEY") or not os.getenv("API_SECRET"):
    logging.critical(
        "Missing API_KEY or API_SECRET environment variables. Please define them in your .env or environment."
    )
    sys.exit(1)

# Constants
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# Default metrics port to handle early references before config load
METRICS_PORT = 8000

def validate_api_keys(api_key, api_secret, exchange_name=""):
    if not api_key or not api_secret:
        raise ValueError(
            f"API_KEY and API_SECRET are required{f' for {exchange_name}' if exchange_name else ''}. Please check your environment variables."
        )


# Metrics
# REQUEST_TIME = Summary("request_processing_seconds", "Time spent processing requests")  # Disabled
# ORDERS_PLACED = Counter("orders_placed_total", "Total number of orders placed")  # Disabled
# Placeholder for metrics server startup moved below

# Config schema
class BotConfig(BaseModel):
    EXCHANGE: str
    SYMBOL: str
    TIMEFRAME: str
    LIMIT: int
    EMA_LENGTH: int
    ATR_MULTIPLIER: float
    VOLUME_MULTIPLIER: float
    TRADING_START_HOUR: int
    TRADING_END_HOUR: int
    MAX_DAILY_LOSS: float
    MAX_TRADES_PER_DAY: int
    STOP_LOSS_PERCENT: float = 2.0
    TAKE_PROFIT_PERCENT: float = 4.0
    EMAIL_NOTIFICATIONS: bool = False
    EMAIL_SMTP_SERVER: str = "smtp.gmail.com"
    EMAIL_SMTP_PORT: int = 465
    EMAIL_SENDER: str = ""
    EMAIL_RECEIVER: str = ""
    EMAIL_PASSWORD: str = ""  # Lägg till SMTP-lösenord för e-postnotifikationer
    LOOKBACK: int
    TEST_BUY_ORDER: bool = True
    TEST_SELL_ORDER: bool = True
    TEST_LIMIT_ORDERS: bool = True
    METRICS_PORT: int = 8000
    HEALTH_PORT: int = 5001


# Load config via Pydantic
with open("config.json") as f:
    raw_config = json.load(f)
config = BotConfig(**raw_config)

# Assign config variables
EXCHANGE_NAME = config.EXCHANGE.lower()
SYMBOL = config.SYMBOL
TIMEFRAME = config.TIMEFRAME
LIMIT = config.LIMIT
EMA_LENGTH = config.EMA_LENGTH
ATR_MULTIPLIER = config.ATR_MULTIPLIER
VOLUME_MULTIPLIER = config.VOLUME_MULTIPLIER
TRADING_START_HOUR = config.TRADING_START_HOUR
TRADING_END_HOUR = config.TRADING_END_HOUR
MAX_DAILY_LOSS = config.MAX_DAILY_LOSS
MAX_TRADES_PER_DAY = config.MAX_TRADES_PER_DAY
STOP_LOSS_PERCENT = config.STOP_LOSS_PERCENT
TAKE_PROFIT_PERCENT = config.TAKE_PROFIT_PERCENT
EMAIL_NOTIFICATIONS = config.EMAIL_NOTIFICATIONS
EMAIL_SMTP_SERVER = config.EMAIL_SMTP_SERVER
EMAIL_SMTP_PORT = config.EMAIL_SMTP_PORT
EMAIL_SENDER = config.EMAIL_SENDER
EMAIL_RECEIVER = config.EMAIL_RECEIVER
EMAIL_PASSWORD = config.EMAIL_PASSWORD
LOOKBACK = config.LOOKBACK
TEST_BUY_ORDER = config.TEST_BUY_ORDER
TEST_SELL_ORDER = config.TEST_SELL_ORDER
TEST_LIMIT_ORDERS = config.TEST_LIMIT_ORDERS
METRICS_PORT = config.METRICS_PORT
HEALTH_PORT = config.HEALTH_PORT

# Override email credentials from environment if set
EMAIL_SENDER = os.getenv("EMAIL_SENDER", EMAIL_SENDER)
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", EMAIL_RECEIVER)
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", EMAIL_PASSWORD)

# Setup structured logging (JSON if available)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
if JsonFormatter:
    json_handler = logging.StreamHandler()
    json_formatter = JsonFormatter("%(asctime)s %(levelname)s %(message)s")
    json_handler.setFormatter(json_formatter)
    logger.addHandler(json_handler)
else:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Create structured logger instance
log = StructuredLogger(logger)

# Behåll bakåtkompatibilitet (viktigt för befintlig kod)
logging = logger

# # Prometheus metrics server startup disabled as not essential
# try:
#     from prometheus_client import start_http_server
#     port = METRICS_PORT
#     for attempt in range(port, port + 5):
#         try:
#             start_http_server(attempt)
#             logging.info(f"Prometheus metrics server started on port {attempt}")
#             break
#         except OSError as e:
#             logging.warning(f"Prometheus metrics server could not start on port {attempt}: {e}")
#     else:
#         logging.error(f"Failed to start Prometheus metrics server on ports {port}-{port+4}")
# except ImportError:
#     logging.warning("Prometheus client not installed, metrics server disabled.")

# Setup exchange instance
try:
    exchange_class = getattr(ccxt, EXCHANGE_NAME)
except AttributeError:
    raise ValueError(f"Unsupported exchange: {EXCHANGE_NAME}")
# Moved API key validation to just before creating exchange instance
validate_api_keys(API_KEY, API_SECRET, EXCHANGE_NAME)
exchange = exchange_class(
    {"apiKey": API_KEY, "secret": API_SECRET, "enableRateLimit": True}
)

# Explicitly export important variables needed by api.py
__all__ = ['exchange', 'SYMBOL', 'get_current_price', 'fetch_balance', 'place_order']

# Nästa rad: ladda marknader först nu när vi satt rätt URLs
exchange.load_markets()

# Utility functions

# Lägg till en funktion för att säkerställa rätt symbolformat för Bitfinex paper trading
def ensure_paper_trading_symbol(symbol):
    """
    Konverterar symboler till korrekt Bitfinex paper trading format (tTESTXXX:TESTYYY)
    
    Exempel:
    - 'BTC/USD' -> 'tTESTBTC:TESTUSD'
    - 'tBTCUSD' -> 'tTESTBTC:TESTUSD'
    - 'tTESTBTC:TESTUSD' -> 'tTESTBTC:TESTUSD' (ingen förändring)
    """
    # Om symbolen redan har rätt prefix, returnera den oförändrad
    if symbol.startswith('tTEST'):
        return symbol
        
    # Hantera standard CCXT format (BTC/USD)
    if '/' in symbol:
        base, quote = symbol.split('/')
        return f"tTEST{base}:TEST{quote}"
        
    # Hantera standard Bitfinex format utan TEST (tBTCUSD)
    if symbol.startswith('t') and not symbol.startswith('tTEST'):
        return f"tTEST{symbol[1:]}"
        
    # Fallback: Lägg till TEST prefix och logga varning
    log.warning(f"Okänt symbolformat: {symbol}, försöker lägga till TEST-prefix")
    return f"tTEST{symbol}"


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


import ccxt
def fetch_balance():
    try:
        return exchange.fetch_balance()
    except ccxt.AuthenticationError:
        # Propagate authentication errors to API layer
        raise
    except Exception as e:
        logging.error(f"py balance: {e}")
        return None


# Lägg till caching och retry för marknadsdata
@retry(max_attempts=3, initial_delay=1)
@lru_cache(maxsize=32)
def fetch_market_data(exchange, symbol, timeframe='1h', limit=100):
    """Hämtar marknadsdata från börs"""
    try:
        # Konvertera symbol till rätt format för Bitfinex paper trading
        if exchange.id == 'bitfinex' and exchange.options.get('paper', False):
            formatted_symbol = ensure_paper_trading_symbol(symbol)
            log.info(f"Använder paper trading symbol: {formatted_symbol} (ursprungligen {symbol})")
            symbol = formatted_symbol
            
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        log.error(f"Kunde inte hämta marknadsdata för {symbol}: {e}")
        return pd.DataFrame()


# Lägg till retry för nuvarande pris
@retry(max_attempts=3, initial_delay=1)
def get_current_price(symbol):
    try:
        # Säkerställ rätt symbolformat för paper trading
        if EXCHANGE_NAME == 'bitfinex':
            symbol = ensure_paper_trading_symbol(symbol)
            
        ticker = exchange.fetch_ticker(symbol)
        if "last" in ticker:
            return ticker["last"]
        else:
            logging.warning("'last' key not found in ticker data.")
            return None
    except Exception as e:
        logging.error(f"Error fetching current price: {e}")
        return None


def calculate_indicators(
    data, ema_length, volume_multiplier, trading_start_hour, trading_end_hour
):
    try:
        required_columns = {"close", "high", "low", "volume"}
        if not required_columns.issubset(data.columns):
            raise ValueError(
                f"Data is missing required columns: {required_columns - set(data.columns)}"
            )

        # Konvertera till float för talib-kompatibilitet
        for col in ["close", "high", "low", "volume"]:
            data[col] = data[col].astype(float)

        if data["close"].isnull().all():
            raise ValueError(
                "The 'close' column is empty or contains only null values. Cannot calculate EMA."
            )

        data["ema"] = talib.EMA(data["close"], timeperiod=ema_length)
        # Compute ATR manually to support small datasets
        atr_period = min(14, len(data))
        high_low = data["high"] - data["low"]
        high_pc = (data["high"] - data["close"].shift()).abs()
        low_pc = (data["low"] - data["close"].shift()).abs()
        tr = pd.concat([high_low, high_pc, low_pc], axis=1).max(axis=1)
        data["atr"] = tr.rolling(window=atr_period, min_periods=1).mean()
        # Rolling average volume with at least one period for small datasets
        data["avg_volume"] = data["volume"].rolling(window=20, min_periods=1).mean()
        data["high_volume"] = data["volume"] > data["avg_volume"] * volume_multiplier
        data_len = len(data)
        # RSI requires timeperiod >=2
        # Calculate RSI safely
        rsi_period = min(14, data_len - 1) if data_len > 1 else 2
        try:
            data["rsi"] = talib.RSI(data["close"], timeperiod=rsi_period)
        except Exception:
            data["rsi"] = 0
        # Fill initial NaN RSI values
        data["rsi"] = data["rsi"].fillna(0)
        # Calculate ADX safely
        adx_period = min(14, data_len - 1) if data_len > 1 else 2
        try:
            data["adx"] = talib.ADX(data["high"], data["low"], data["close"], timeperiod=adx_period)
        except Exception:
            data["adx"] = 0
        # Fill initial NaN ADX values
        data["adx"] = data["adx"].fillna(0)
        data["hour"] = data["datetime"].dt.hour
        data["within_trading_hours"] = data["hour"].between(
            trading_start_hour, trading_end_hour
        )
        return data
    except Exception as e:
        logging.error(f"Error calculating indicators: {e}")
        return None


def detect_fvg(data, lookback, bullish=True):
    # Förenklad FVG: returnera alltid senaste high/low för bullish/bearish
    if len(data) < 2:
        return np.nan, np.nan
    if bullish:
        return data["high"].iloc[-2], data["low"].iloc[-1]
    else:
        return data["high"].iloc[-1], data["low"].iloc[-2]


def send_email_notification(subject, body):
    if not EMAIL_NOTIFICATIONS:
        logging.info(
            "[EMAIL] E-postnotifieringar är inaktiverade (EMAIL_NOTIFICATIONS=False)."
        )
        return

    required = [EMAIL_SENDER, EMAIL_RECEIVER, EMAIL_PASSWORD]
    if not all(required):
        logging.warning(
            "[EMAIL] E-postinställningar saknas (avsändare, mottagare eller lösenord). Inget mejl skickat."
        )
        return
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        # Använd SMTP_SSL för Gmail (port 465)
        with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, int(EMAIL_SMTP_PORT)) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        logging.info("[EMAIL] E-post skickad via Gmail SMTP_SSL!")
    except Exception as e:
        logging.error(f"[EMAIL] Misslyckades att skicka e-post: {e}")


def place_order(
    order_type, symbol, amount, price=None, stop_loss=None, take_profit=None
):
    log.order(f"Försöker lägga {order_type}-order: symbol: {symbol}, amount: {amount}, price: {price}")
    
    # Respect test mode flags
    if order_type == "buy" and not TEST_BUY_ORDER:
        log.info("Buy orders are disabled, skipping.", "TEST")
        return
    if order_type == "sell" and not TEST_SELL_ORDER:
        log.info("Sell orders are disabled, skipping.", "TEST")
        return
    # If limit orders are disabled, convert to market
    if price and not TEST_LIMIT_ORDERS:
        log.info("Limit orders are disabled, placing market order instead.", "TEST")
        price = None
    if amount <= 0:
        log.error(f"Invalid order amount: {amount}. Amount must be positive.")
        return
    try:
        params = {}
        
        # Specifik hantering för Bitfinex paper trading
        if EXCHANGE_NAME == 'bitfinex':
            # För paper trading på Bitfinex behöver vi använda rätt ordertyp
            # och se till att symbolen hanteras korrekt
            
            # Kontrollera om vi använder en paper trading symbol (t.ex. tTESTBTC:TESTUSD)
            is_paper_trading = "TEST" in symbol
            
            # Använd alltid EXCHANGE ordrar för paper trading på Bitfinex
            if is_paper_trading or "TEST" in SYMBOL:
                if price:
                    params["type"] = "EXCHANGE LIMIT"
                else:
                    params["type"] = "EXCHANGE MARKET"
                    
                log.debug(f"Använder paper trading parametrar för symbol {symbol}")
        
        log.debug(f"Anropar {'limit' if price else 'market'} {order_type} order...")
        log.debug(f"Params: {params}")
                
        if order_type == "buy":
            order = (
                exchange.create_limit_buy_order(symbol, amount, price, params)
                if price
                else exchange.create_market_buy_order(symbol, amount, params)
            )
        elif order_type == "sell":
            order = (
                exchange.create_limit_sell_order(symbol, amount, price, params)
                if price
                else exchange.create_market_sell_order(symbol, amount, params)
            )
        else:
            log.error(f"Okänt ordertyp: {order_type}")
            return
        
        # Backwards compatibility prints for tests - MATCHING EXACT CASE FROM TESTS
        print("\nOrder Information:")
        print(f"type: {order_type}")
        print(f"symbol: {symbol}")
        print(f"Amount: {amount}")
        if price:
            print(f"price: {price}")  # lowercase 'price' to match test expectation
        if stop_loss:
            print(f"Stop Loss: {stop_loss}")
        if take_profit:
            print(f"Take Profit: {take_profit}")
            
        # Skapa en gemensam orderinfo-sträng
        order_info = []
        order_info.append(f"Type: {order_type.capitalize()}")
        order_info.append(f"Symbol: {symbol}")
        order_info.append(f"Amount: {amount}")
        if price:
            order_info.append(f"Price: {price}")
        if stop_loss:
            order_info.append(f"Stop Loss: {stop_loss}")
        if take_profit:
            order_info.append(f"Take Profit: {take_profit}")
            
        # Formatera för separata loggutskrifter
        order_info_str = ", ".join(order_info)
        log.trade(f"Order skapad: {order_info_str}")
        
        # Skapa orderdetaljer för loggning
        relevant_details = {
            "Order-ID": order.get("id", "N/A") if order else "N/A",
            "Status": order.get("status", "N/A") if order else "N/A",
            "Pris": order.get("price", "N/A") if order else "N/A",
            "Mängd": order.get("amount", "N/A") if order else "N/A",
            "Utförd mängd": order.get("filled", "N/A") if order else "N/A",
            "Ordertyp": order.get("type", "N/A") if order else "N/A",
            "Tidsstämpel": order.get("datetime", "N/A") if order else "N/A",
        }
        
        # Skriv ut detaljer med snyggt formatering
        log.separator("-", 40)
        log.order("Order detaljer:")
        for key, value in relevant_details.items():
            log.order(f"  {key}: {value}")
        log.separator("-", 40)
        
        # Print for backward compatibility with tests
        print("\nOrderdetaljer (förenklade):")
        for key, value in relevant_details.items():
            print(f"{key}: {value}")
        
        # Skicka e-postnotis om ordern lyckas
        if EMAIL_NOTIFICATIONS:
            subject = f"Tradingbot Order: {order_type.upper()} {symbol}"
            body = (
                f"Ordertyp: {order_type}\n"
                f"Symbol: {symbol}\n"
                f"Amount: {amount}\n"
                f"Price: {price}\n"
                f"Stop Loss: {stop_loss}\n"
                f"Take Profit: {take_profit}\n"
                f"Orderdetaljer: {relevant_details}"
            )
            send_email_notification(subject, body)
            log.notification(f"E-postnotifiering skickad för order {order.get('id', 'N/A') if order else 'N/A'}")
            
        return order
        
    except Exception as e:
        log.error(f"Fel vid orderläggning: {str(e)}")
        log.debug(f"Detaljerat fel vid {order_type} order: {repr(e)}")
        return None


def create_limit_order(symbol, side, amount, price):
    try:
        # Säkerställ rätt symbolformat för paper trading
        if EXCHANGE_NAME == 'bitfinex':
            symbol = ensure_paper_trading_symbol(symbol)
            
        order = exchange.create_limit_order(symbol, side, amount, price)
        log.info(f"Limit order: {order}")
        return order
    except Exception as e:
        log.error(f"Fel vid skapande av limit order: {e}")
        return None

def create_market_order(symbol, side, amount):
    try:
        # Säkerställ rätt symbolformat för paper trading
        if EXCHANGE_NAME == 'bitfinex':
            symbol = ensure_paper_trading_symbol(symbol)
            
        order = exchange.create_market_order(symbol, side, amount)
        log.info(f"Marknadsorder: {order}")
        return order
    except Exception as e:
        log.error(f"Fel vid skapande av marknadsorder: {e}")
        return None

def get_open_orders(symbol=None):
    try:
        # Säkerställ rätt symbolformat för paper trading
        if symbol and EXCHANGE_NAME == 'bitfinex':
            symbol = ensure_paper_trading_symbol(symbol)
            
        open_orders = exchange.fetch_open_orders(symbol)
        return open_orders
    except Exception as e:
        log.error(f"Fel vid hämtning av öppna ordrar: {e}")
        return []

def cancel_order(order_id, symbol=None):
    try:
        # Säkerställ rätt symbolformat för paper trading
        if symbol and EXCHANGE_NAME == 'bitfinex':
            symbol = ensure_paper_trading_symbol(symbol)
            
        result = exchange.cancel_order(order_id, symbol)
        log.info(f"Avbruten order: {result}")
        return result
    except Exception as e:
        log.error(f"Fel vid avbrytande av order: {e}")
        return None


# WebSocket authentication


def build_auth_message(api_key, api_secret):
    nonce = round(datetime.now().timestamp() * 1_000)
    payload = f"AUTH{nonce}"
    signature = hmac.new(
        api_secret.encode(), payload.encode(), hashlib.sha384
    ).hexdigest()
    return json.dumps(
        {
            "event": "auth",
            "apiKey": api_key,
            "authNonce": nonce,
            "authPayload": payload,
            "authSig": signature,
        }
    )


def authenticate_websocket(uri, api_key, api_secret):
    try:
        with connect(uri) as websocket:
            websocket.send(build_auth_message(api_key, api_secret))
            for message in websocket:
                data = json.loads(message)
                if (
                    isinstance(data, dict)
                    and data.get("event") == "auth"
                    and data.get("status") != "OK"
                ):
                    raise Exception("Authentication failed.")
                logging.info(f"Login successful for user <{data.get('userId')}>.")
    except websockets.exceptions.InvalidURI as e:
        logging.error(f"Invalid WebSocket URI: {e}")
    except websockets.exceptions.ConnectionClosedError as e:
        logging.error(f"WebSocket connection closed unexpectedly: {e}")
    except Exception as e:
        logging.error(f"WebSocket authentication error: {e}")

async def fetch_realtime_data():
    retry_delay = 5  # seconds
    retries = 0
    channel_id = None
    candles = []
    try:
        # Select WebSocket endpoint based on SANDBOX flag
        uri = "wss://api.bitfinex.com/ws/2"
        async with websockets.connect(uri) as websocket:
            # No longer starting ping loop - removed
            subscription_message = {
                "event": "subscribe",
                "channel": "candles",
                "key": f"trade:1m:{SYMBOL}",
            }
            await websocket.send(json.dumps(subscription_message))
            logging.info("Subscribed to real-time data...")
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                logging.debug(f"WebSocket message: {data}")
                # Handle subscription confirmation
                if isinstance(data, dict):
                    if (
                        data.get("event") == "subscribed"
                        and data.get("channel") == "candles"
                    ):
                        channel_id = data.get("chanId")
                        logging.info(
                            f"Subscribed to candles channel with id {channel_id}"
                        )
                    elif data.get("event") in ("info", "conf"):
                        logging.info(f"Info/conf message: {data}")
                    elif data.get("event") == "error":
                        logging.error(f"WebSocket error: {data}")
                        return None
                    elif data.get("event") == "pong":
                        # received pong response
                        logging.debug(f"Received pong: cid={data.get('cid')} ts={data.get('ts')}")
                        continue
                # Ignore heartbeat
                if isinstance(data, list) and len(data) > 1 and data[1] == "hb":
                    continue
                # Only process messages for the correct channel
                if isinstance(data, list) and (
                    channel_id is None or data[0] == channel_id
                ):
                    # Snapshot: [chanId, [ [candle1], [candle2], ... ] ]
                    if isinstance(data[1], list) and isinstance(data[1][0], list):
                        candles = data[1]
                        logging.info(f"Received snapshot with {len(candles)} candles.")
                        # Return snapshot as initial data
                        return [data[0], candles]
                    # Update: [chanId, [candle]]
                    elif isinstance(data[1], list) and isinstance(
                        data[1][0], (int, float)
                    ):
                        candles.append(data[1])
                        logging.info(f"Received candle update: {data[1]}")
                        # Return the latest candle as a single-row DataFrame
                        return [data[0], [data[1]]]
    except websockets.exceptions.ConnectionClosed as e:
        logging.error(
            f"WebSocket connection closed: {e}. Retrying in {retry_delay} seconds..."
        )
        retries += 1
        await asyncio.sleep(retry_delay)
    except Exception as e:
        logging.error(f"Error fetching real-time data: {e}")
        return None
    logging.error("Max retries reached. Failed to fetch real-time data.")
    return None


def convert_to_local_time(utc_time):
    try:
        return utc_time.astimezone(LOCAL_TIMEZONE)
    except Exception as e:
        logging.error(f"Error converting time: {e}")
        return utc_time


def process_realtime_data(raw_data):
    try:
        if not isinstance(raw_data, list):
            logging.error(
                f"process_realtime_data: Skippade icke-lista raw_data: {raw_data}"
            )
            return None
        candles = raw_data[1] if len(raw_data) > 1 else []
        if not candles:
            logging.warning(
                f"process_realtime_data: Tomma candles i raw_data: {raw_data}"
            )
        columns = ["timestamp", "open", "high", "low", "close", "volume"]
        data = pd.DataFrame(candles, columns=columns)
        data["datetime"] = pd.to_datetime(data["timestamp"], unit="ms", utc=True)
        data["local_datetime"] = data["datetime"].apply(convert_to_local_time)
        logging.info(f"Structured Data: {data.head()}")
        return data
    except Exception as e:
        logging.error(f"Error processing real-time data: {e}")
        return None


# Lägg till asynkron wrapper för historisk datahämtning
async def fetch_historical_data_async(symbol, timeframe, limit):
    """
    Async wrapper runt fetch_market_data för att hämta historisk OHLCV-data i bakgrund utan att blockera huvudloopen.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fetch_market_data, symbol, timeframe, limit)


async def main():
    try:
        # Starta bakgrundsuppgift för att hämta historisk data asynkront
        hist_task = asyncio.create_task(
            fetch_historical_data_async(SYMBOL, TIMEFRAME, LIMIT)
        )
        logging.info("Fetching real-time data...")
        # Hämta realtidsdata från WebSocket
        realtime_data = await fetch_realtime_data()
        # Vänta på att historisk data är färdighämtad
        historical_data = await hist_task
        if historical_data is not None:
            logging.info(f"Fetched historical data: {len(historical_data)} entries.")
            # Du kan beräkna indikatorer på historisk data vid behov
            _ = calculate_indicators(
                historical_data,
                EMA_LENGTH,
                VOLUME_MULTIPLIER,
                TRADING_START_HOUR,
                TRADING_END_HOUR,
            )
        if realtime_data:
            structured_data = process_realtime_data(realtime_data)
            if structured_data is not None:
                logging.info("Real-time data processing completed.")
                # Beräkna indikatorer direkt efter process_realtime_data
                structured_data = calculate_indicators(
                    structured_data,
                    EMA_LENGTH,
                    VOLUME_MULTIPLIER,
                    TRADING_START_HOUR,
                    TRADING_END_HOUR,
                )
                execute_trading_strategy(
                    structured_data,
                    MAX_TRADES_PER_DAY,
                    MAX_DAILY_LOSS,
                    ATR_MULTIPLIER,
                    SYMBOL,
                )
        else:
            logging.error("Failed to fetch real-time data.")
    except Exception as e:
        logging.error(f"Error in main function: {e}")


def execute_trading_strategy(
    data, max_trades_per_day, max_daily_loss, atr_multiplier, symbol, lookback=100
):
    try:
        if data is None or data.empty:
            logging.error(
                "Data is invalid or empty. Trading strategy cannot be executed."
            )
            return
        if "ema" not in data.columns or data["ema"].count() == 0:
            logging.critical(
                "EMA indicator is missing or not calculated correctly. Exiting strategy."
            )
            return
        if "high_volume" not in data.columns or data["high_volume"].count() == 0:
            logging.critical(
                "High volume indicator is missing or not calculated correctly. Exiting strategy."
            )
            return
        if "atr" not in data.columns or data["atr"].count() == 0:
            logging.critical(
                "ATR indicator is missing or not calculated correctly. Exiting strategy."
            )
            return
        mean_atr = data["atr"].mean()
        trade_count = 0
        daily_loss = 0
        for index, row in data.iterrows():
            if daily_loss < -max_daily_loss:
                logging.debug(
                    f"Avbryter: daily_loss ({daily_loss}) < -max_daily_loss ({-max_daily_loss})"
                )
                break
            # ATR-villkor: endast köp/sälj om ATR är tillräckligt hög
            if row["atr"] <= atr_multiplier * mean_atr:
                logging.debug(
                    f"Skippad rad {index}: ATR {row['atr']} <= {atr_multiplier} * mean_ATR {mean_atr}"
                )
                continue
            bull_fvg_high, bull_fvg_low = detect_fvg(
                data.iloc[: index + 1], lookback, bullish=True
            )
            bear_fvg_high, bear_fvg_low = detect_fvg(
                data.iloc[: index + 1], lookback, bullish=False
            )
            long_condition = (
                not np.isnan(bull_fvg_high)
                and row["close"] < bull_fvg_low
                and row["close"] > row["ema"]
                and row["high_volume"]
                and row["within_trading_hours"]
            )
            short_condition = (
                not np.isnan(bear_fvg_high)
                and row["close"] > bear_fvg_high
                and row["close"] < row["ema"]
                and row["high_volume"]
                and row["within_trading_hours"]
            )
            logging.debug(
                f"Rad {index}: close={row['close']}, ema={row['ema']}, high_volume={row['high_volume']}, within_trading_hours={row['within_trading_hours']}, bull_fvg_high={bull_fvg_high}, bull_fvg_low={bull_fvg_low}, bear_fvg_high={bear_fvg_high}, bear_fvg_low={bear_fvg_low}"
            )
            logging.debug(
                f"long_condition={long_condition}, short_condition={short_condition}"
            )
            if long_condition and trade_count < max_trades_per_day:
                logging.info(f"Lägger KÖP-order på rad {index}")
                trade_count += 1
                # Beräkna stop loss och take profit nivåer
                stop_loss = row["close"] * (1 - STOP_LOSS_PERCENT / 100)
                take_profit = row["close"] * (1 + TAKE_PROFIT_PERCENT / 100)
                place_order("buy", symbol, 0.001, row["close"], stop_loss, take_profit)
            if short_condition and trade_count < max_trades_per_day:
                logging.info(f"Lägger SÄLJ-order på rad {index}")
                trade_count += 1
                stop_loss = row["close"] * (1 + STOP_LOSS_PERCENT / 100)
                take_profit = row["close"] * (1 - TAKE_PROFIT_PERCENT / 100)
                place_order("sell", symbol, 0.001, row["close"], stop_loss, take_profit)
    except Exception as e:
        logging.error(f"Error executing trading strategy: {e}")


# Strategimodularisering: definiera TradingStrategy-klass
class TradingStrategy:
    def __init__(
        self,
        symbol,
        ema_length,
        atr_multiplier,
        volume_multiplier,
        start_hour,
        end_hour,
        max_trades,
        max_loss,
        stop_loss_pct,
        take_profit_pct,
        lookback=100,
    ):
        self.symbol = symbol
        self.ema_length = ema_length
        self.atr_multiplier = atr_multiplier
        self.volume_multiplier = volume_multiplier
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.max_trades = max_trades
        self.max_loss = max_loss
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.lookback = lookback

    def calculate_indicators(self, data):
        return calculate_indicators(
            data,
            self.ema_length,
            self.volume_multiplier,
            self.start_hour,
            self.end_hour,
        )

    def detect_fvg(self, data, bullish):
        return detect_fvg(data, self.lookback, bullish)

    def execute(self, data):
        if data is None or data.empty:
            logging.error(
                "Data is invalid or empty. Trading strategy cannot be executed."
            )
            return
        # init counters
        trade_count = 0
        daily_loss = 0
        mean_atr = data["atr"].mean() if "atr" in data.columns else 0
        for idx, row in data.iterrows():
            if daily_loss < -self.max_loss or trade_count >= self.max_trades:
                break
            if "atr" in row and row["atr"] <= self.atr_multiplier * mean_atr:
                continue
            bull_high, bull_low = self.detect_fvg(data.iloc[: idx + 1], True)
            bear_high, bear_low = self.detect_fvg(data.iloc[: idx + 1], False)
            long_cond = (
                not np.isnan(bull_high)
                and row["close"] < bull_low
                and row["close"] > row["ema"]
                and row["high_volume"]
                and row["within_trading_hours"]
            )
            short_cond = (
                not np.isnan(bear_high)
                and row["close"] > bear_high
                and row["close"] < row["ema"]
                and row["high_volume"]
                and row["within_trading_hours"]
            )
            if long_cond:
                trade_count += 1
                sl = row["close"] * (1 - self.stop_loss_pct / 100)
                tp = row["close"] * (1 + self.take_profit_pct / 100)
                place_order("buy", self.symbol, 0.001, row["close"], sl, tp)
            if short_cond:
                trade_count += 1
                sl = row["close"] * (1 + self.stop_loss_pct / 100)
                tp = row["close"] * (1 - self.take_profit_pct / 100)
                place_order("sell", self.symbol, 0.001, row["close"], sl, tp)


async def listen_order_updates():
    import json
    import hmac
    import hashlib
    import time as time_mod
    from pytz import timezone
    from datetime import datetime

    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")
    stockholm = timezone("Europe/Stockholm")

    def get_auth_payload():
        nonce = str(int(time_mod.time() * 1000))
        auth_payload = f"AUTH{nonce}"
        signature = hmac.new(
            API_SECRET.encode(), auth_payload.encode(), hashlib.sha384
        ).hexdigest()
        return {
            "event": "auth",
            "apiKey": API_KEY,
            "authSig": signature,
            "authPayload": auth_payload,
            "authNonce": nonce,
        }

    # Använd config.SANDBOX istället för att kontrollera miljövariabeln direkt
    # Detta säkerställer konsekvent användning av samma inställning som resten av programmet
    uri = "wss://api.bitfinex.com/ws/2"
    log.websocket(f"Ansluter till WebSocket: {uri}")
    
    try:
        async with websockets.connect(uri) as ws:
            auth_payload = get_auth_payload()
            await ws.send(json.dumps(auth_payload))
            log.websocket("Skickade autentiseringsförfrågan, väntar på svar...")
            
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                if isinstance(data, list) and len(data) > 1 and data[1] == "oc":
                    order_info = data[2]
                    status = order_info[13]
                    order_id = order_info[0]
                    symbol = order_info[3] if len(order_info) > 3 else "N/A"
                    
                    # Formatera status
                    status_upper = str(status).toUpperCase()
                    status_color = ""
                    if "EXECUTED" in status_upper:
                        status_color = TerminalColors.GREEN
                    elif "CANCELED" in status_upper or "CANCELLED" in status_upper:
                        status_color = TerminalColors.RED
                    
                    # Skriv tidsstämpel i Europe/Stockholm, alltid korrekt med sommartid
                    now_stockholm = datetime.now(stockholm)
                    
                    # Logga order uppdatering i terminalfärger
                    log.separator("-", 50)
                    log.order(f"Order status uppdaterad: {order_id}")
                    log.order(f"  Symbol: {symbol}")
                    log.order(f"  Status: {status}")
                    log.order(f"  Tid: {now_stockholm.strftime('%Y-%m-%d %H:%M:%S')}")
                    log.debug(f"Fullt orderinfo: {order_info}")
                    log.separator("-", 50)
                    
                    # Spara till loggfil
                    with open("order_status_log.txt", "a") as f:
                        f.write(
                            f"{now_stockholm.strftime('%Y-%m-%d %H:%M:%S.%f')}: Order-ID: {order_id}, Status: {status}, Info: {order_info}\n"
                        )
                    
                    # Skicka e-postnotis vid viktiga statusändringar
                    if EMAIL_NOTIFICATIONS and (
                        status_upper.startswith("EXECUTED")
                        or status_upper.startswith("CANCELLED")
                        or status_upper.startswith("MODIFIED")
                        or status_upper.startswith("FILLED")
                        or status_upper.startswith("CLOSED")
                    ):
                        subject = f"Order status uppdaterad: {order_id}"
                        body = (
                            f"Order-ID: {order_id}\n"
                            f"Symbol: {symbol}\n"
                            f"Status: {status}\n"
                            f"Tidpunkt: {now_stockholm.strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"Orderinfo: {order_info}"
                        )
                        send_email_notification(subject, body)
                        log.notification(f"E-postnotifiering skickad för order {order_id}")
                
                # Hantera ping/pong
                elif isinstance(data, dict) and data.get("event") == "ping":
                    log.debug(f"Mottog ping: {data}")
                    pong = {"event": "pong", "cid": data.get("cid", 0)}
                    await ws.send(json.dumps(pong))
                    log.debug(f"Skickade pong-svar: {pong}")
                
                # Hantera autentiseringssvar
                elif isinstance(data, dict) and data.get("event") == "auth":
                    if data.get("status") == "OK":
                        log.websocket(f"Autentisering lyckades! Användare: {data.get('userId', 'Okänd')}")
                    else:
                        log.error(f"Autentisering misslyckades: {data}")
                
                # Hantera heartbeat
                elif isinstance(data, list) and len(data) > 1 and data[1] == "hb":
                    log.debug("WebSocket heartbeat mottagen")
                    
    except websockets.exceptions.ConnectionClosed as e:
        log.error(f"WebSocket-anslutningen stängdes: {e}")
    except Exception as e:
        log.error(f"Fel i WebSocket-lyssnaren: {str(e)}")
        log.debug(f"Detaljerat fel: {repr(e)}")


# Starta WebSocket-lyssnare i bakgrunden när boten startar
def print_env_vars():
    import os

    print("API_KEY:", os.getenv("API_KEY"))
    print("API_SECRET:", os.getenv("API_SECRET"))
    # print("COINBASE_API_KEY:", os.getenv("COINBASE_API_KEY"))
    # print("COINBASE_API_SECRET:", os.getenv("COINBASE_API_SECRET"))


# Helper to start WebSocket listener in thread
def _start_listen_updates():
    """Wrapper to run listen_order_updates as an asyncio task in a separate thread."""
    asyncio.run(listen_order_updates())


# Health-check endpoint server on port 5000


class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path_only = urlparse(self.path).path
        if path_only in ("/", "/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

# Define a Reusable TCPServer to avoid "Address already in use" errors
class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def signal_handler(signum, frame):
    logging.info("Signal received, shutting down bot gracefully.")
    sys.exit(0)

if __name__ == "__main__":
    import signal as signal_module

    signal_module.signal(signal_module.SIGINT, signal_handler)
    # Start health-check server on configured port with address reuse
    server = ReusableTCPServer(("0.0.0.0", HEALTH_PORT), HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    
    # Starta WebSocket-lyssnaren för orderuppdateringar i en separat tråd
    log.info("Startar WebSocket-lyssnare för orderuppdateringar...")
    websocket_thread = threading.Thread(target=_start_listen_updates, daemon=True)
    websocket_thread.start()
    
    # Starta huvudloopen
    asyncio.run(main())
    # Håll programmet igång så att WebSocket-lyssnaren lever
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Avslutar boten...")


def run_backtest(
    symbol,
    timeframe,
    limit,
    ema_length,
    volume_multiplier,
    trading_start_hour,
    trading_end_hour,
    max_trades_per_day,
    max_daily_loss,
    atr_multiplier,
    lookback=100,
    print_orders=False,
    save_to_file=None,
):
    """
    Kör backtest på historisk data och returnerar statistik.
    print_orders: Om True, skriv ut köp/sälj som skulle ha lagts.
    save_to_file: Om satt till filnamn, sparar trades till fil (CSV eller JSON).
    """
    data = fetch_market_data(symbol, timeframe, limit)
    if data is None or data.empty:
        logging.error("Ingen historisk data kunde hämtas för backtest.")
        return
    data = calculate_indicators(
        data, ema_length, volume_multiplier, trading_start_hour, trading_end_hour
    )
    if data is None:
        logging.error("Kunde inte beräkna indikatorer för backtest.")
        return
    trades = []
    trade_count = 0
    daily_loss = 0
    mean_atr = data["atr"].mean() if "atr" in data.columns else 0
    for index, row in data.iterrows():
        if daily_loss < -max_daily_loss:
            break
        if "atr" in row and row["atr"] <= atr_multiplier * mean_atr:
            continue
        bull_fvg_high, bull_fvg_low = detect_fvg(
            data.iloc[: index + 1], lookback, bullish=True
        )
        bear_fvg_high, bear_fvg_low = detect_fvg(
            data.iloc[: index + 1], lookback, bullish=False
        )
        long_condition = (
            not np.isnan(bull_fvg_high)
            and row["close"] < bull_fvg_low
            and row["close"] > row["ema"]
            and row["high_volume"]
            and row["within_trading_hours"]
        )
        short_condition = (
            not np.isnan(bear_fvg_high)
            and row["close"] > bear_fvg_high
            and row["close"] < row["ema"]
            and row["high_volume"]
            and row["within_trading_hours"]
        )
        if long_condition and trade_count < max_trades_per_day:
            trade_count += 1
            trades.append({"type": "buy", "price": row["close"], "index": index})
            if print_orders:
                logging.info(f"[BACKTEST] BUY @ {row['close']} (index {index})")
        if short_condition and trade_count < max_trades_per_day:
            trade_count += 1
            trades.append({"type": "sell", "price": row["close"], "index": index})
            if print_orders:
                logging.info(f"[BACKTEST] SELL @ {row['close']} (index {index})")
    logging.info(f"[BACKTEST] Antal trades: {len(trades)}")
    if trades:
        logging.info(f"[BACKTEST] Första trade: {trades[0]}")
        logging.info(f"[BACKTEST] Sista trade: {trades[-1]}")
    else:
        logging.info("[BACKTEST] Inga trades genererades.")
    if save_to_file and trades:
        import json, csv

        if save_to_file.endswith(".json"):
            with open(save_to_file, "w") as f:
                json.dump(trades, f, indent=2)
            logging.info(f"[BACKTEST] Trades sparade till {save_to_file} (JSON)")
        elif save_to_file.endswith(".csv"):
            with open(save_to_file, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=trades[0].keys())
                writer.writeheader()
                writer.writerows(trades)
            logging.info(f"[BACKTEST] Trades sparade till {save_to_file} (CSV)")
        else:
            logging.warning("[BACKTEST] Okänt filformat. Ange .json eller .csv.")
    return trades

import json
import time
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import requests
from typing import Dict, List, Tuple, Optional, Any, Union
import traceback

# Konfiguration av loggning
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tradingbot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TradingBot")

class TradingBot:
    def __init__(self, config_file='config.json'):
        """
        Initialiserar tradingbot med konfiguration från en JSON-fil.
        
        Args:
            config_file: Sökväg till konfigurationsfilen
        """
        logger.info("Initialiserar TradingBot")
        try:
            # Läs konfiguration
            self.config_file = config_file
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            
            # Sätt API-nycklar och hemligheter
            self.api_key = self.config.get('api_key', '')
            self.api_secret = self.config.get('api_secret', '')
            
            # Sätt standardvärden
            self.base_url = self.config.get('base_url', 'https://api.example.com')
            self.symbols = self.config.get('symbols', ['tTESTBTC:TESTUSD'])
            self.default_symbol = self.symbols[0] if self.symbols else 'tTESTBTC:TESTUSD'
            self.running = False
            self.log_file = "order_status_log.txt"
            
            # Strategi-parametrar
            self.strategy_params = self.config.get('strategy', {})
            self.strategy_type = self.strategy_params.get('type', 'simple')
            
            # Data för prestandaberäkningar
            self.performance_data = {}
            
            logger.info(f"TradingBot initialiserad med strategi: {self.strategy_type}")
        except Exception as e:
            logger.error(f"Fel vid initialisering av TradingBot: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def start(self):
        """Startar trading-botten"""
        logger.info("Startar TradingBot")
        self.running = True
        return {"status": "started"}

    def stop(self):
        """Stoppar trading-botten"""
        logger.info("Stoppar TradingBot")
        self.running = False
        return {"status": "stopped"}

    def get_status(self):
        """Hämtar botens nuvarande status"""
        status = "running" if self.running else "stopped"
        return {"status": status}

    def get_balance(self):
        """
        Hämtar kontobalanserna från börsen.
        
        Returns:
            Dict: Lexikon med valuta som nyckel och saldo som värde
        """
        # Simulerar en API-anrop för saldon
        logger.info("Hämtar kontobalans")
        try:
            # I en verklig implementation skulle detta anropa börsens API
            return {
                "USD": 10000.0,
                "BTC": 0.5,
                "ETH": 5.0
            }
        except Exception as e:
            logger.error(f"Fel vid hämtning av balans: {str(e)}")
            return {"error": str(e)}

    def get_ticker(self, symbol=None):
        """
        Hämtar aktuellt pris för en symbol.
        
        Args:
            symbol: Symbol att hämta pris för (t.ex. 'tTESTBTC:TESTUSD')
            
        Returns:
            Dict: Aktuellt pris och annan ticker-information
        """
        if symbol is None:
            symbol = self.default_symbol
            
        logger.info(f"Hämtar ticker för {symbol}")
        
        try:
            # Simulerar en API-anrop för ticker-data
            # I en verklig implementation skulle detta anropa börsens API
            prices = {
                'tTESTBTC:TESTUSD': 50000 + np.random.normal(0, 500),
                'tTESTETH:TESTUSD': 3000 + np.random.normal(0, 50),
                'tTESTLTC:TESTUSD': 200 + np.random.normal(0, 5)
            }
            
            price = prices.get(symbol, 0)
            return {
                "symbol": symbol,
                "last_price": price,
                "bid": price - 10,
                "ask": price + 10,
                "daily_change": np.random.normal(0, 0.02),
                "volume": 1000 + np.random.normal(0, 100)
            }
        except Exception as e:
            logger.error(f"Fel vid hämtning av ticker för {symbol}: {str(e)}")
            return {"error": str(e)}

    def place_order(self, symbol=None, order_type=None, amount=None, price=None):
        """
        Placerar en order på börsen.
        
        Args:
            symbol: Handelssymbol (t.ex. 'tTESTBTC:TESTUSD')
            order_type: Typ av order ('buy' eller 'sell')
            amount: Antal enheter att köpa/sälja
            price: Pris per enhet (lämna tomt för marknadspris)
            
        Returns:
            Dict: Information om den placerade ordern
        """
        if symbol is None:
            symbol = self.default_symbol
            
        if order_type not in ['buy', 'sell']:
            return {"error": "Ogiltig order-typ. Använd 'buy' eller 'sell'."}
            
        if amount is None:
            return {"error": "Mängd måste anges."}
            
        logger.info(f"Placerar order: {order_type} {amount} {symbol} @ {price or 'marknadspris'}")
            
        try:
            # Simulerar en API-anrop för att placera en order
            # I en verklig implementation skulle detta anropa börsens API
            order_id = f"order-{int(time.time())}"
            executed = np.random.choice([True, False], p=[0.8, 0.2])
            
            ticker = self.get_ticker(symbol)
            if isinstance(ticker, dict) and "error" in ticker:
                return ticker
                
            executed_price = price or ticker["last_price"]
            
            order_info = {
                "id": order_id,
                "symbol": symbol,
                "type": order_type,
                "amount": float(amount),
                "price": executed_price,
                "status": "executed" if executed else "cancelled",
                "timestamp": datetime.now().isoformat()
            }
            
            # Logga orderinformation
            self._log_order(order_info)
            
            return order_info
            
        except Exception as e:
            error_msg = f"Fel vid placering av order: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {"error": error_msg}

    def _log_order(self, order_info):
        """
        Loggar orderinformation till en fil för spårning.
        
        Args:
            order_info: Information om ordern
        """
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(order_info) + '\n')
        except Exception as e:
            logger.error(f"Fel vid loggning av order: {str(e)}")

    def get_orders(self, symbol=None, start_date=None, end_date=None):
        """
        Hämtar historiska ordrar.
        
        Args:
            symbol: Filter för handelssymbol
            start_date: Filtrera från detta datum (ISO-format)
            end_date: Filtrera till detta datum (ISO-format)
            
        Returns:
            List: Lista med ordrar
        """
        logger.info(f"Hämtar ordrar med filter - symbol: {symbol}, start_date: {start_date}, end_date: {end_date}")
        
        try:
            orders = []
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    for line in f:
                        try:
                            order = json.loads(line.strip())
                            
                            # Applicera filter
                            if symbol and order.get('symbol') != symbol:
                                continue
                                
                            order_date = datetime.fromisoformat(order.get('timestamp'))
                            
                            if start_date:
                                start = datetime.fromisoformat(start_date)
                                if order_date < start:
                                    continue
                                    
                            if end_date:
                                end = datetime.fromisoformat(end_date)
                                if order_date > end:
                                    continue
                                    
                            orders.append(order)
                        except json.JSONDecodeError:
                            logger.warning(f"Kunde inte parsa orderrad: {line}")
                        except Exception as e:
                            logger.error(f"Fel vid bearbetning av orderrad: {str(e)}")
            
            # Sortera efter tidsstämpel (nyaste först)
            orders.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return orders
            
        except Exception as e:
            error_msg = f"Fel vid hämtning av ordrar: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_open_orders(self):
        """
        Hämtar öppna ordrar.
        
        Returns:
            List: Lista med öppna ordrar
        """
        # Simulerar en API-anrop för öppna ordrar
        # I en verklig implementation skulle detta anropa börsens API
        logger.info("Hämtar öppna ordrar")
        
        try:
            return [
                {
                    "id": f"order-{int(time.time())-100}",
                    "symbol": self.default_symbol,
                    "type": "buy",
                    "amount": 0.01,
                    "price": 49500,
                    "status": "open"
                }
            ]
        except Exception as e:
            error_msg = f"Fel vid hämtning av öppna ordrar: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_logs(self, limit=10):
        """
        Hämtar de senaste loggarna.
        
        Args:
            limit: Antal loggrader att hämta
            
        Returns:
            List: Lista med loggmeddelanden
        """
        logger.info(f"Hämtar senaste {limit} loggar")
        
        try:
            logs = []
            # I en verklig implementation skulle detta läsa från en loggfil
            logs.append({"timestamp": datetime.now().isoformat(), "message": "Bot startad"})
            logs.append({"timestamp": datetime.now().isoformat(), "message": "Anslutning till API upprättad"})
            return logs
        except Exception as e:
            error_msg = f"Fel vid hämtning av loggar: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_config(self):
        """
        Hämtar nuvarande konfiguration.
        
        Returns:
            Dict: Konfigurationen
        """
        logger.info("Hämtar konfiguration")
        
        try:
            return self.config
        except Exception as e:
            error_msg = f"Fel vid hämtning av konfiguration: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def update_config(self, new_config):
        """
        Uppdaterar konfigurationen.
        
        Args:
            new_config: Ny konfiguration som ett lexikon
            
        Returns:
            Dict: Status för uppdateringen
        """
        logger.info("Uppdaterar konfiguration")
        
        try:
            # Uppdatera konfigurationsobjektet
            self.config.update(new_config)
            
            # Spara till fil
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
                
            return {"status": "success", "message": "Konfiguration uppdaterad"}
        except Exception as e:
            error_msg = f"Fel vid uppdatering av konfiguration: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_price_history(self, symbol=None, timeframe='1h', limit=100):
        """
        Hämtar historiska prisdata.
        
        Args:
            symbol: Handelssymbol
            timeframe: Tidsramen ('1m', '5m', '15m', '30m', '1h', '3h', '6h', '12h', '1d', '1w')
            limit: Antal punkter att hämta
            
        Returns:
            List: Lista med prisdata-punkter
        """
        if symbol is None:
            symbol = self.default_symbol
            
        logger.info(f"Hämtar prishistorik för {symbol}, timeframe {timeframe}, limit {limit}")
        
        try:
            # Simulerar en API-anrop för historiska data
            # I en verklig implementation skulle detta anropa börsens API
            end_time = int(time.time() * 1000)
            
            # Bestäm intervall baserat på timeframe
            interval_map = {
                '1m': 60 * 1000,
                '5m': 5 * 60 * 1000,
                '15m': 15 * 60 * 1000,
                '30m': 30 * 60 * 1000,
                '1h': 60 * 60 * 1000,
                '3h': 3 * 60 * 1000,
                '6h': 6 * 60 * 1000,
                '12h': 12 * 60 * 1000,
                '1d': 24 * 60 * 1000,
                '1w': 7 * 24 * 60 * 1000
            }
            
            interval = interval_map.get(timeframe, 60 * 60 * 1000)  # Default till 1h
            
            # Generera simulerad historik
            base_prices = {
                'tTESTBTC:TESTUSD': 50000,
                'tTESTETH:TESTUSD': 3000,
                'tTESTLTC:TESTUSD': 200
            }
            
            base_price = base_prices.get(symbol, 100)
            volatility = base_price * 0.05
            
            price_data = []
            for i in range(limit):
                timestamp = end_time - (interval * (limit - i))
                
                # Skapa simulerad prisrörelse
                if i == 0:
                    price = base_price
                else:
                    prev_price = price_data[i-1][2]  # Föregående stängningspris
                    change = np.random.normal(0, volatility * 0.01)
                    price = prev_price * (1 + change)
                
                # Skapa OHLCV-punkt (Open, High, Low, Close, Volume)
                open_price = price
                close_price = price * (1 + np.random.normal(0, 0.005))
                high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.005)))
                low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.005)))
                volume = abs(np.random.normal(10, 5))
                
                price_data.append([timestamp, open_price, close_price, high_price, low_price, volume])
            
            return price_data
        
        except Exception as e:
            error_msg = f"Fel vid hämtning av prishistorik: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def analyze_strategy_performance(self, symbol=None, start_date=None, end_date=None, debug=False):
        """
        Analyserar strategins prestanda baserat på orderhistoriken.
        
        Args:
            symbol: Filtrera efter symbol
            start_date: Filtrera från detta datum
            end_date: Filtrera till detta datum
            debug: Om debug-information ska inkluderas
            
        Returns:
            Dict: Resultat av prestandaanalysen
        """
        logger.info(f"Analyserar strategi-prestanda med filter - symbol: {symbol}, start_date: {start_date}, end_date: {end_date}")
        
        try:
            # Hämta orderhistorik
            orders = self.get_orders(symbol, start_date, end_date)
            if isinstance(orders, dict) and "error" in orders:
                return orders
                
            # Statistikobjekt för att lagra resultat
            stats = {
                "total_trades": len(orders),
                "total_buys": 0,
                "total_sells": 0,
                "executed": 0,
                "cancelled": 0,
                "profit_loss": 0.0,
                "symbols": {},
                "daily_performance": {},
                "hourly_distribution": {},
                "weekly_distribution": {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0},  # Mån-Sön
                "executed_orders": [],
                "cancelled_orders": [],
                "avg_buy_price": 0,
                "avg_sell_price": 0,
                "win_trades": 0,
                "loss_trades": 0,
                "break_even_trades": 0,
                "longest_win_streak": 0,
                "longest_loss_streak": 0,
                "current_streak_type": None,  # 'win' eller 'loss'
                "current_streak_count": 0,
                "avg_profit_per_trade": 0,
                "max_profit_trade": 0,
                "max_loss_trade": 0,
                "total_volume": 0,
                "risk_reward_ratio": 0
            }
            
            # Debug statistik
            debug_stats = {
                "total_lines_processed": len(orders),
                "lines_filtered": 0,
                "parse_errors": 0,
                "debug_messages": []
            }
            
            if not orders:
                if debug:
                    return {"stats": stats, "debug": debug_stats}
                return stats
            
            buy_prices = []
            sell_prices = []
            daily_trades = {}
            daily_profit_loss = {}
            
            prev_pair = None  # För att spåra par av köp-sälj
            pairs = []  # För att spåra kompletta par
            
            current_streak = 0
            current_streak_type = None
            max_win_streak = 0
            max_loss_streak = 0
            
            profits = []
            losses = []
            
            try:
                for order in orders:
                    # Basstatistik
                    order_type = order.get('type')
                    status = order.get('status')
                    symbol = order.get('symbol')
                    price = float(order.get('price', 0))
                    amount = float(order.get('amount', 0))
                    value = price * amount
                    
                    # Uppdatera symbolstatistik
                    if symbol not in stats["symbols"]:
                        stats["symbols"][symbol] = {
                            "trades": 0,
                            "buys": 0,
                            "sells": 0,
                            "executed": 0,
                            "cancelled": 0,
                            "volume": 0,
                            "profit_loss": 0
                        }
                    
                    stats["symbols"][symbol]["trades"] += 1
                    stats["symbols"][symbol]["volume"] += value
                    stats["total_volume"] += value
                    
                    # Uppdatera typ-statistik
                    if order_type == 'buy':
                        stats["total_buys"] += 1
                        stats["symbols"][symbol]["buys"] += 1
                        if status == 'executed':
                            buy_prices.append(price)
                    elif order_type == 'sell':
                        stats["total_sells"] += 1
                        stats["symbols"][symbol]["sells"] += 1
                        if status == 'executed':
                            sell_prices.append(price)
                    
                    # Uppdatera status-statistik
                    if status == 'executed':
                        stats["executed"] += 1
                        stats["symbols"][symbol]["executed"] += 1
                        stats["executed_orders"].append(order)
                    elif status == 'cancelled':
                        stats["cancelled"] += 1
                        stats["symbols"][symbol]["cancelled"] += 1
                        stats["cancelled_orders"].append(order)
                    
                    # Tidsdistributionsanalys
                    try:
                        timestamp = datetime.fromisoformat(order.get('timestamp'))
                        
                        # Daglig statistik
                        day_key = timestamp.strftime('%Y-%m-%d')
                        if day_key not in daily_trades:
                            daily_trades[day_key] = {
                                "buys": 0, "sells": 0, "executed": 0, "cancelled": 0
                            }
                            daily_profit_loss[day_key] = 0
                        
                        daily_trades[day_key][order_type + "s"] += 1
                        if status == 'executed':
                            daily_trades[day_key]["executed"] += 1
                        elif status == 'cancelled':
                            daily_trades[day_key]["cancelled"] += 1
                        
                        # Veckodagsanalys
                        weekday = timestamp.weekday()  # 0 = Måndag, 6 = Söndag
                        stats["weekly_distribution"][weekday] += 1
                        
                        # Timanalys
                        hour = timestamp.hour
                        if hour not in stats["hourly_distribution"]:
                            stats["hourly_distribution"][hour] = 0
                        stats["hourly_distribution"][hour] += 1
                        
                    except Exception as e:
                        error_msg = f"Fel vid analys av tidsstämpel: {str(e)}"
                        logger.error(error_msg)
                        debug_stats["debug_messages"].append(error_msg)
                    
                    # Spåra par av köp-sälj för P&L-beräkningar
                    if status == 'executed':
                        if not prev_pair:
                            prev_pair = order
                        else:
                            # Vi har ett potentiellt par
                            if (prev_pair.get('type') == 'buy' and order_type == 'sell') or \
                               (prev_pair.get('type') == 'sell' and order_type == 'buy'):
                                # Beräkna P&L
                                if prev_pair.get('type') == 'buy':
                                    buy_order = prev_pair
                                    sell_order = order
                                else:
                                    sell_order = prev_pair
                                    buy_order = order
                                
                                buy_price = float(buy_order.get('price', 0))
                                sell_price = float(sell_order.get('price', 0))
                                trade_amount = min(float(buy_order.get('amount', 0)), float(sell_order.get('amount', 0)))
                                
                                # P&L för detta par
                                pair_pl = (sell_price - buy_price) * trade_amount
                                stats["profit_loss"] += pair_pl
                                stats["symbols"][symbol]["profit_loss"] += pair_pl
                                
                                # Uppdatera daglig P&L
                                sell_day = datetime.fromisoformat(sell_order.get('timestamp')).strftime('%Y-%m-%d')
                                if sell_day in daily_profit_loss:
                                    daily_profit_loss[sell_day] += pair_pl
                                
                                # Spåra vinst/förlust och serier
                                if pair_pl > 0:
                                    stats["win_trades"] += 1
                                    profits.append(pair_pl)
                                    
                                    if current_streak_type == 'win':
                                        current_streak += 1
                                    else:
                                        current_streak = 1
                                        current_streak_type = 'win'
                                    
                                    if current_streak > max_win_streak:
                                        max_win_streak = current_streak
                                        
                                elif pair_pl < 0:
                                    stats["loss_trades"] += 1
                                    losses.append(pair_pl)
                                    
                                    if current_streak_type == 'loss':
                                        current_streak += 1
                                    else:
                                        current_streak = 1
                                        current_streak_type = 'loss'
                                    
                                    if current_streak > max_loss_streak:
                                        max_loss_streak = current_streak
                                        
                                else:
                                    stats["break_even_trades"] += 1
                                    
                                # Spara paret
                                pairs.append({
                                    "buy_order": buy_order,
                                    "sell_order": sell_order,
                                    "profit_loss": pair_pl,
                                    "trade_amount": trade_amount
                                })
                                
                                # Återställ för nästa par
                                prev_pair = None
                            else:
                                # Samma typ i rad, vi ersätter föregående
                                prev_pair = order
                    
            except Exception as e:
                error_msg = f"Fel under orderanalys: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                debug_stats["debug_messages"].append(error_msg)
            
            # Beräkna genomsnitt och mer avancerad statistik
            stats["avg_buy_price"] = sum(buy_prices) / len(buy_prices) if buy_prices else 0
            stats["avg_sell_price"] = sum(sell_prices) / len(sell_prices) if sell_prices else 0
            
            # Vinststatistik
            if stats["win_trades"] + stats["loss_trades"] > 0:
                stats["win_rate"] = stats["win_trades"] / (stats["win_trades"] + stats["loss_trades"])
            else:
                stats["win_rate"] = 0
                
            # Genomsnittlig vinst per trade
            if len(pairs) > 0:
                stats["avg_profit_per_trade"] = stats["profit_loss"] / len(pairs)
            
            # Risk/reward-ratio
            if profits and losses:
                avg_profit = sum(profits) / len(profits) if len(profits) > 0 else 0
                avg_loss = abs(sum(losses) / len(losses)) if len(losses) > 0 else 0
                stats["risk_reward_ratio"] = avg_profit / avg_loss if avg_loss > 0 else 0
                stats["max_profit_trade"] = max(profits) if profits else 0
                stats["max_loss_trade"] = min(losses) if losses else 0
            
            # Utförandetal
            stats["execution_rate"] = stats["executed"] / stats["total_trades"] if stats["total_trades"] > 0 else 0
            stats["cancellation_rate"] = stats["cancelled"] / stats["total_trades"] if stats["total_trades"] > 0 else 0
            
            # Buy/Sell ratio
            stats["buy_sell_ratio"] = stats["total_buys"] / stats["total_sells"] if stats["total_sells"] > 0 else 0
            
            # Serielängder
            stats["longest_win_streak"] = max_win_streak
            stats["longest_loss_streak"] = max_loss_streak
            stats["current_streak_type"] = current_streak_type
            stats["current_streak_count"] = current_streak
            
            # Formatera daglig prestandadata
            stats["daily_performance"] = []
            for day, day_stats in daily_trades.items():
                stats["daily_performance"].append({
                    "date": day,
                    "trades": day_stats["buys"] + day_stats["sells"],
                    "buys": day_stats["buys"],
                    "sells": day_stats["sells"],
                    "executed": day_stats["executed"],
                    "cancelled": day_stats["cancelled"],
                    "profit_loss": daily_profit_loss.get(day, 0)
                })
            
            # Sortera daglig prestandadata efter datum
            stats["daily_performance"].sort(key=lambda x: x["date"])
            
            # Lägg till de senaste handelsuppgifterna
            stats["recent_trades"] = orders[:min(10, len(orders))]
            
            if debug:
                return {"stats": stats, "debug": debug_stats}
            return stats
            
        except Exception as e:
            error_msg = f"Fel vid analys av strategi-prestanda: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            if debug:
                debug_stats["debug_messages"].append(error_msg)
                debug_stats["debug_messages"].append(traceback.format_exc())
                return {"error": error_msg, "debug": debug_stats}
            
            return {"error": error_msg}
    
    def execute_strategy(self):
        """
        Utför handelsstrategi baserad på konfigurationsparametrar.
        
        Returns:
            Dict: Resultat av strategiutförandet
        """
        if not self.running:
            return {"status": "stopped", "message": "Boten är inte igång"}
            
        strategy_type = self.strategy_params.get('type', 'simple')
        
        if strategy_type == 'simple':
            return self._execute_simple_strategy()
        elif strategy_type == 'moving_average':
            return self._execute_ma_strategy()
        else:
            return {"error": f"Okänd strategi-typ: {strategy_type}"}
    
    def _execute_simple_strategy(self):
        """
        Utför en enkel handelsstrategi baserad på slumpmässiga prispunkter.
        
        Returns:
            Dict: Resultat av strategiutförandet
        """
        logger.info("Utför enkel strategi")
        
        try:
            symbol = self.strategy_params.get('symbol', self.default_symbol)
            
            # Hämta aktuellt pris
            ticker = self.get_ticker(symbol)
            if isinstance(ticker, dict) and "error" in ticker:
                return ticker
                
            current_price = ticker["last_price"]
            
            # Slumpmässigt beslut för demonstration
            decision = np.random.choice(['buy', 'sell', 'hold'], p=[0.3, 0.3, 0.4])
            
            if decision == 'hold':
                logger.info(f"Strategi-beslut: HOLD vid {current_price}")
                return {"action": "hold", "price": current_price, "reason": "Prisnivå indikerar att vi bör hålla positionen"}
                
            # Bestäm mängd
            amount = self.strategy_params.get('amount', 0.001)
            
            # Placera order
            order_result = self.place_order(
                symbol=symbol,
                order_type=decision,
                amount=amount,
                price=current_price
            )
            
            return {
                "action": decision,
                "price": current_price,
                "amount": amount,
                "result": order_result,
                "reason": f"Exekverade {decision} baserat på nuvarande prisnivå"
            }
            
        except Exception as e:
            error_msg = f"Fel vid utförande av enkel strategi: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {"error": error_msg}
    
    def _execute_ma_strategy(self):
        """
        Utför en glidande medelvärde-baserad handelsstrategi.
        
        Returns:
            Dict: Resultat av strategiutförandet
        """
        logger.info("Utför moving average strategi")
        
        try:
            symbol = self.strategy_params.get('symbol', self.default_symbol)
            short_period = self.strategy_params.get('short_ma', 10)
            long_period = self.strategy_params.get('long_ma', 30)
            
            # Hämta historiska data
            history = self.get_price_history(symbol, timeframe='1h', limit=long_period + 10)
            if isinstance(history, dict) and "error" in history:
                return history
                
            # Beräkna glidande medelvärden
            prices = [candle[2] for candle in history]  # Använd stängningspriser
            
            if len(prices) < long_period:
                return {"error": f"Otillräcklig prishistorik för MA-strategi. Behöver minst {long_period} punkter."}
                
            short_ma = sum(prices[-short_period:]) / short_period
            long_ma = sum(prices[-long_period:]) / long_period
            
            current_price = prices[-1]
            
            # Beslutlogik
            if short_ma > long_ma:
                decision = 'buy'
                reason = f"Kort MA ({short_ma:.2f}) högre än lång MA ({long_ma:.2f})"
            else:
                decision = 'sell'
                reason = f"Kort MA ({short_ma:.2f}) lägre än lång MA ({long_ma:.2f})"
                
            # Bestäm mängd
            amount = self.strategy_params.get('amount', 0.001)
            
            # Slumpmässigt beslut om att exekvera eller ej för demo
            if np.random.random() < 0.7:  # 70% chans att exekvera
                # Placera order
                order_result = self.place_order(
                    symbol=symbol,
                    order_type=decision,
                    amount=amount,
                    price=current_price
                )
                
                executed = True
            else:
                order_result = {"status": "simulated", "message": "Order simulerad men inte exekverad"}
                executed = False
                
            return {
                "action": decision,
                "executed": executed,
                "price": current_price,
                "amount": amount,
                "short_ma": short_ma,
                "long_ma": long_ma,
                "result": order_result,
                "reason": reason
            }
            
        except Exception as e:
            error_msg = f"Fel vid utförande av MA-strategi: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {"error": error_msg}

def get_ticker(symbol):
    """
    Hämtar aktuell ticker information för vald symbol
    """
    try:
        if EXCHANGE_NAME.lower() == 'bitfinex':
            # Säkerställ rätt symbolformat för paper trading
            paper_symbol = ensure_paper_trading_symbol(symbol)
            ticker = exchange.fetch_ticker(paper_symbol)
        else:
            ticker = exchange.fetch_ticker(symbol)
        return ticker
    except Exception as e:
        log.error(f"Error fetching ticker for {symbol}: {str(e)}")
        return None

def get_orderbook(symbol):
    """
    Hämtar orderbook för vald symbol
    """
    try:
        if EXCHANGE_NAME.lower() == 'bitfinex':
            # Säkerställ rätt symbolformat för paper trading
            paper_symbol = ensure_paper_trading_symbol(symbol)
            orderbook = exchange.fetch_order_book(paper_symbol)
        else:
            orderbook = exchange.fetch_order_book(symbol)
        return orderbook
    except Exception as e:
        log.error(f"Error fetching orderbook for {symbol}: {str(e)}")
        return None

def get_historical_data(symbol, timeframe, limit=100):
    """
    Hämtar historisk OHLCV data
    """
    try:
        # Säkerställ rätt symbolformat för paper trading på Bitfinex
        if EXCHANGE_NAME.lower() == 'bitfinex':
            symbol = ensure_paper_trading_symbol(symbol)
            
        return fetch_market_data(exchange, symbol, timeframe, limit)
    except Exception as e:
        log.error(f"Error fetching historical data: {e}")
        return None

def create_order(symbol, order_type, side, amount, price=None):
    """
    Skapar en order med specificerade parametrar
    """
    try:
        if EXCHANGE_NAME.lower() == 'bitfinex':
            # Säkerställ rätt symbolformat för paper trading
            paper_symbol = ensure_paper_trading_symbol(symbol)
            order = exchange.create_order(paper_symbol, order_type, side, amount, price)
        else:
            order = exchange.create_order(symbol, order_type, side, amount, price)
        
        log.info(f"Order created: {order}")
        
        with open('order_status_log.txt', 'a') as f:
            f.write(f"{datetime.now()}: Created order - Symbol: {symbol}, Type: {order_type}, Side: {side}, Amount: {amount}, Price: {price}, Order ID: {order['id'] if 'id' in order else 'N/A'}\n")
        
        return order
    except Exception as e:
        log.error(f"Error creating order for {symbol}: {str(e)}")
        return None

def cancel_order(order_id, symbol):
    """
    Avbryter en order med specificerat order-ID
    """
    try:
        if EXCHANGE_NAME.lower() == 'bitfinex':
            # Säkerställ rätt symbolformat för paper trading
            paper_symbol = ensure_paper_trading_symbol(symbol)
            result = exchange.cancel_order(order_id, paper_symbol)
        else:
            result = exchange.cancel_order(order_id, symbol)
        
        log.info(f"Order canceled: {order_id}")
        
        with open('order_status_log.txt', 'a') as f:
            f.write(f"{datetime.now()}: Canceled order - Order ID: {order_id}, Symbol: {symbol}\n")
        
        return result
    except Exception as e:
        log.error(f"Error canceling order {order_id} for {symbol}: {str(e)}")
        return None

def get_open_orders(symbol=None):
    """
    Hämtar alla öppna ordrar, optionellt filtrerat på symbol
    """
    try:
        if symbol:
            if EXCHANGE_NAME.lower() == 'bitfinex':
                # Säkerställ rätt symbolformat för paper trading
                paper_symbol = ensure_paper_trading_symbol(symbol)
                orders = exchange.fetch_open_orders(paper_symbol)
            else:
                orders = exchange.fetch_open_orders(symbol)
        else:
            orders = exchange.fetch_open_orders()
        return orders
    except Exception as e:
        log.error(f"Error fetching open orders: {str(e)}")
        return []
