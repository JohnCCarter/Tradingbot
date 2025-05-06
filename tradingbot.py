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
# Determine sandbox mode from environment to allow missing keys
sandbox_env = os.getenv("SANDBOX", "false").lower() in ("1", "true")
# Validate essential API credentials early (skip in sandbox)
if not os.getenv("API_KEY") or not os.getenv("API_SECRET"):
    if sandbox_env:
        logging.warning("Missing API_KEY/API_SECRET, running in sandbox mode.")
    else:
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
    SANDBOX: bool = False  # Enable CCXT sandbox/testnet mode when true


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
SANDBOX = config.SANDBOX

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
# Enable testnet/sandbox mode om konfigurerat
if SANDBOX:
    if EXCHANGE_NAME == "bitfinex":
        # Rätta REST-endpunkter för Bitfinex testnet
        testnet_rest = "https://api-testnet.bitfinex.com"
        # ccxt kommer använda exchange.urls["api"] för alla v2-calls
        exchange.urls["api"] = testnet_rest
        logging.info(f"Using Bitfinex testnet REST endpoint: {testnet_rest}")
        # OBS: dina WebSocket-anrop styrs separat i fetch_realtime_data
    else:
        try:
            exchange.setSandboxMode(True)
            logging.info("CCXT sandbox mode enabled.")
        except Exception:
            logging.warning("Exchange does not support sandbox mode.")

# Explicitly export important variables needed by api.py
__all__ = ['exchange', 'SANDBOX', 'SYMBOL', 'get_current_price', 'fetch_balance', 'place_order']

# Nästa rad: ladda marknader först nu när vi satt rätt URLs
exchange.load_markets()

# Utility functions


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
def fetch_market_data(symbol, timeframe, limit):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv:
            logging.warning("No market data fetched from API.")
            return None
        # Filter out rows that don't have exactly 6 elements
        valid_rows = [row for row in ohlcv if isinstance(row, (list, tuple)) and len(row) == 6]
        if not valid_rows:
            logging.warning("All fetched market data rows are malformed.")
            return None
        if len(valid_rows) != len(ohlcv):
            dropped = len(ohlcv) - len(valid_rows)
            if not valid_rows:
                logging.error("No valid market data rows were fetched after filtering.")
            else:
                logging.warning(f"Dropped {dropped} malformed data rows.")
        data = pd.DataFrame(valid_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        data["datetime"] = pd.to_datetime(data["timestamp"], unit="ms", utc=True)
        return data
    except Exception as e:
        logging.error(f"Error fetching market data: {e}")
        return None


# Lägg till retry för nuvarande pris
@retry(max_attempts=3, initial_delay=1)
def get_current_price(symbol):
    try:
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
        # Sätt rätt typ för Bitfinex testsymboler
        if symbol and symbol.startswith("tTEST"):
            if price:
                params["type"] = "EXCHANGE LIMIT"
            else:
                params["type"] = "EXCHANGE MARKET"
                
        log.debug(f"Anropar {'limit' if price else 'market'} {order_type} order...")
                
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
        uri = "wss://api-pub-testnet.bitfinex.com/ws/2" if SANDBOX else "wss://api.bitfinex.com/ws/2"
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
    uri = "wss://api-pub-testnet.bitfinex.com/ws/2" if SANDBOX else "wss://api.bitfinex.com/ws/2"
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
                    status_upper = str(status).upper()
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
