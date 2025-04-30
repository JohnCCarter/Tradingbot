from email.mime.multipart import MIMEMultipart
import os
import json
import hmac
import hashlib
import asyncio
import signal
from datetime import datetime
from dotenv import load_dotenv
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
from email.mime.text import MIMEText
import time

# Create timezone object once
LOCAL_TIMEZONE = timezone('Europe/Stockholm')

# Load environment variables
load_dotenv()

# Constants
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
def validate_api_keys(api_key, api_secret, exchange_name=""):
    if not api_key or not api_secret:
        raise ValueError(f"API_KEY and API_SECRET are required{f' for {exchange_name}' if exchange_name else ''}. Please check your environment variables.")

validate_api_keys(API_KEY, API_SECRET)

# Load config from config.json
with open("config.json") as f:
    config = json.load(f)

# Validate config values
required_config_keys = ["EXCHANGE", "SYMBOL", "TIMEFRAME", "LIMIT", "EMA_LENGTH", "ATR_MULTIPLIER", "VOLUME_MULTIPLIER", "TRADING_START_HOUR", "TRADING_END_HOUR", "MAX_DAILY_LOSS", "MAX_TRADES_PER_DAY"]
for key in required_config_keys:
    if key not in config:
        raise ValueError(f"Missing required key '{key}' in config.json")

# Add stop loss and take profit config
STOP_LOSS_PERCENT = config.get("STOP_LOSS_PERCENT", 2.0)
TAKE_PROFIT_PERCENT = config.get("TAKE_PROFIT_PERCENT", 4.0)

EMAIL_NOTIFICATIONS = config.get("EMAIL_NOTIFICATIONS", False)
EMAIL_SMTP_SERVER = config.get("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = config.get("EMAIL_SMTP_PORT", 465)
EMAIL_SENDER = config.get("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = config.get("EMAIL_RECEIVER", "")

EXCHANGE_NAME = config["EXCHANGE"].lower()
SYMBOL = config["SYMBOL"]
TIMEFRAME = config["TIMEFRAME"]
LIMIT = config["LIMIT"]
EMA_LENGTH = config["EMA_LENGTH"]
ATR_MULTIPLIER = config["ATR_MULTIPLIER"]
VOLUME_MULTIPLIER = config["VOLUME_MULTIPLIER"]
TRADING_START_HOUR = config["TRADING_START_HOUR"]
TRADING_END_HOUR = config["TRADING_END_HOUR"]
MAX_DAILY_LOSS = config["MAX_DAILY_LOSS"]
MAX_TRADES_PER_DAY = config["MAX_TRADES_PER_DAY"]

# Initialize exchange based on config
if EXCHANGE_NAME == "bitfinex":
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")
    validate_api_keys(API_KEY, API_SECRET, "Bitfinex")
    exchange = ccxt.bitfinex({
        'apiKey': API_KEY,
        'secret': API_SECRET
    })
    exchange.nonce = lambda: int(time.time() * 1000)
# Coinbase-kod bortkommenterad nedan
# elif EXCHANGE_NAME == "coinbase":
#     API_KEY = os.getenv("COINBASE_API_KEY")
#     API_SECRET = os.getenv("COINBASE_API_SECRET")
#     if not API_KEY or not API_SECRET:
#         raise ValueError("COINBASE_API_KEY och COINBASE_API_SECRET krävs för Coinbase. Lägg till dem i din .env-fil.")
#     exchange = ccxt.coinbase({
#         'apiKey': API_KEY,
#         'secret': API_SECRET
#     })
else:
    raise ValueError(f"Exchange '{EXCHANGE_NAME}' stöds inte ännu.")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Utility functions

def fetch_balance():
    try:
        return exchange.fetch_balance()
    except Exception as e:
        logging.error(f"py balance: {e}")
        return None


def fetch_market_data(symbol, timeframe, limit):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv or not all(len(row) == 6 for row in ohlcv):
            logging.warning("Malformed or incomplete data fetched from API.")
            return None
        data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        data['datetime'] = pd.to_datetime(data['timestamp'], unit='ms', utc=True)
        return data
    except Exception as e:
        logging.error(f"Error fetching market data: {e}")
        return None


def calculate_indicators(
    data, ema_length, volume_multiplier, trading_start_hour, trading_end_hour
):
    try:
        required_columns = {'close', 'high', 'low', 'volume'}
        if not required_columns.issubset(data.columns):
            raise ValueError(
                f"Data is missing required columns: {required_columns - set(data.columns)}"
            )

        # Konvertera till float för talib-kompatibilitet
        for col in ['close', 'high', 'low', 'volume']:
            data[col] = data[col].astype(float)

        if data['close'].isnull().all():
            raise ValueError("The 'close' column is empty or contains only null values. Cannot calculate EMA.")

        data['ema'] = talib.EMA(data['close'], timeperiod=ema_length)
        data['atr'] = talib.ATR(data['high'], data['low'], data['close'], timeperiod=14)
        data['avg_volume'] = data['volume'].rolling(window=20).mean()
        data['high_volume'] = data['volume'] > data['avg_volume'] * volume_multiplier
        data['rsi'] = talib.RSI(data['close'], timeperiod=14)
        data['adx'] = talib.ADX(data['high'], data['low'], data['close'], timeperiod=14)
        data['hour'] = data['datetime'].dt.hour
        data['within_trading_hours'] = data['hour'].between(trading_start_hour, trading_end_hour)
        return data
    except Exception as e:
        logging.error(f"Error calculating indicators: {e}")
        return None


def detect_fvg(data, lookback, bullish=True):
    # Förenklad FVG: returnera alltid senaste high/low för bullish/bearish
    if len(data) < 2:
        return np.nan, np.nan
    if bullish:
        return data['high'].iloc[-2], data['low'].iloc[-1]
    else:
        return data['high'].iloc[-1], data['low'].iloc[-2]


def send_email_notification(subject, body):
    if not EMAIL_NOTIFICATIONS:
        logging.info("[EMAIL] E-postnotifieringar är inaktiverade (EMAIL_NOTIFICATIONS=False).")
        return

    required = [EMAIL_SENDER, EMAIL_RECEIVER, EMAIL_PASSWORD]
    if not all(required):
        logging.warning("[EMAIL] E-postinställningar saknas (avsändare, mottagare eller lösenord). Inget mejl skickat.")
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


def place_order(order_type, symbol, amount, price=None, stop_loss=None, take_profit=None):
    print(f"[DEBUG] Försöker lägga {order_type}-order: symbol={symbol}, amount={amount}, price={price}")
    if amount <= 0:
        print(f"Invalid order amount: {amount}. Amount must be positive.")
        return
    try:
        params = {}
        if order_type == 'buy':
            print("[DEBUG] Anropar create_limit_buy_order eller create_market_buy_order...")
            order = exchange.create_limit_buy_order(symbol, amount, price, params) if price else exchange.create_market_buy_order(symbol, amount, params)
        elif order_type == 'sell':
            print("[DEBUG] Anropar create_limit_sell_order eller create_market_sell_order...")
            order = exchange.create_limit_sell_order(symbol, amount, price, params) if price else exchange.create_market_sell_order(symbol, amount, params)
        else:
            print(f"[DEBUG] Okänt ordertyp: {order_type}")
            return
        print("\nOrder Information:")
        print(f"Type: {order_type.capitalize()}")
        print(f"Symbol: {symbol}")
        print(f"Amount: {amount}")
        if price:
            print(f"Price: {price}")
        if stop_loss:
            print(f"Stop Loss: {stop_loss}")
        if take_profit:
            print(f"Take Profit: {take_profit}")
        relevant_details = {
            'Order-ID': order.get('id', 'N/A') if order else 'N/A',
            'Status': order.get('status', 'N/A') if order else 'N/A',
            'Pris': order.get('price', 'N/A') if order else 'N/A',
            'Mängd': order.get('amount', 'N/A') if order else 'N/A',
            'Utförd mängd': order.get('filled', 'N/A') if order else 'N/A',
            'Ordertyp': order.get('type', 'N/A') if order else 'N/A',
            'Tidsstämpel': order.get('datetime', 'N/A') if order else 'N/A',
        }
        print("\nOrderdetaljer (förenklade):")
        for key, value in relevant_details.items():
            print(f"{key}: {value}")
        # Skicka e-postnotis om ordern lyckas
        if EMAIL_NOTIFICATIONS:
            subject = f"Tradingbot Order: {order_type.upper()} {symbol}"
            body = f"Ordertyp: {order_type}\nSymbol: {symbol}\nAmount: {amount}\nPrice: {price}\nStop Loss: {stop_loss}\nTake Profit: {take_profit}\nOrderdetaljer: {relevant_details}"
            send_email_notification(subject, body)
        # Starta övervakning av orderstatus (kommenterad, vi använder nu WebSocket)
        # if order and order.get('id'):
        #     monitor_order_status(order.get('id'), symbol)
    except Exception as e:
        print(f"[DEBUG] Fel vid orderläggning: {e}")
        print(f"Error placing {order_type} order: {e}")


def get_current_price(symbol):
    try:
        ticker = exchange.fetch_ticker(symbol)
        if 'last' in ticker:
            return ticker['last']
        else:
            logging.warning("'last' key not found in ticker data.")
            return None
    except Exception as e:
        logging.error(f"Error fetching current price: {e}")
        return None

# WebSocket authentication

def build_auth_message(api_key, api_secret):
    nonce = round(datetime.now().timestamp() * 1_000)
    payload = f"AUTH{nonce}"
    signature = hmac.new(api_secret.encode(), payload.encode(), hashlib.sha384).hexdigest()
    return json.dumps({
        "event": "auth",
        "apiKey": api_key,
        "authNonce": nonce,
        "authPayload": payload,
        "authSig": signature
    })


def authenticate_websocket(uri, api_key, api_secret):
    try:
        with connect(uri) as websocket:
            websocket.send(build_auth_message(api_key, api_secret))
            for message in websocket:
                data = json.loads(message)
                if isinstance(data, dict) and data.get("event") == "auth" and data.get("status") != "OK":
                    raise Exception("Authentication failed.")
                logging.info(f"Login successful for user <{data.get('userId')}>.")
    except websockets.exceptions.InvalidURI as e:
        logging.error(f"Invalid WebSocket URI: {e}")
    except websockets.exceptions.ConnectionClosedError as e:
        logging.error(f"WebSocket connection closed unexpectedly: {e}")
    except Exception as e:
        logging.error(f"WebSocket authentication error: {e}")


async def fetch_realtime_data():
    max_retries = 5
    retry_delay = 5  # seconds
    retries = 0
    channel_id = None
    candles = []
    try:
        async with websockets.connect("wss://api.bitfinex.com/ws/2") as websocket:
            subscription_message = {
                "event": "subscribe",
                "channel": "candles",
                "key": f"trade:1m:{SYMBOL}"
            }
            await websocket.send(json.dumps(subscription_message))
            logging.info("Subscribed to real-time data...")
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                logging.debug(f"WebSocket message: {data}")
                # Handle subscription confirmation
                if isinstance(data, dict):
                    if data.get("event") == "subscribed" and data.get("channel") == "candles":
                        channel_id = data.get("chanId")
                        logging.info(f"Subscribed to candles channel with id {channel_id}")
                    elif data.get("event") in ("info", "conf"):
                        logging.info(f"Info/conf message: {data}")
                    elif data.get("event") == "error":
                        logging.error(f"WebSocket error: {data}")
                        return None
                    continue
                # Ignore heartbeat
                if isinstance(data, list) and len(data) > 1 and data[1] == "hb":
                    continue
                # Only process messages for the correct channel
                if isinstance(data, list) and (channel_id is None or data[0] == channel_id):
                    # Snapshot: [chanId, [ [candle1], [candle2], ... ] ]
                    if isinstance(data[1], list) and isinstance(data[1][0], list):
                        candles = data[1]
                        logging.info(f"Received snapshot with {len(candles)} candles.")
                        # Return snapshot as initial data
                        return [data[0], candles]
                    # Update: [chanId, [candle]]
                    elif isinstance(data[1], list) and isinstance(data[1][0], (int, float)):
                        candles.append(data[1])
                        logging.info(f"Received candle update: {data[1]}")
                        # Return the latest candle as a single-row DataFrame
                        return [data[0], [data[1]]]
    except websockets.exceptions.ConnectionClosed as e:
        logging.error(f"WebSocket connection closed: {e}. Retrying in {retry_delay} seconds...")
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
            logging.error(f"process_realtime_data: Skippade icke-lista raw_data: {raw_data}")
            return None
        candles = raw_data[1] if len(raw_data) > 1 else []
        if not candles:
            logging.warning(f"process_realtime_data: Tomma candles i raw_data: {raw_data}")
        columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        data = pd.DataFrame(candles, columns=columns)
        data['datetime'] = pd.to_datetime(data['timestamp'], unit='ms', utc=True)
        data['local_datetime'] = data['datetime'].apply(convert_to_local_time)
        logging.info(f"Structured Data: {data.head()}")
        return data
    except Exception as e:
        logging.error(f"Error processing real-time data: {e}")
        return None


async def main():
    try:
        logging.info("Fetching real-time data...")
        realtime_data = await fetch_realtime_data()
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
                    TRADING_END_HOUR
                )
                execute_trading_strategy(
                    structured_data,
                    MAX_TRADES_PER_DAY,
                    MAX_DAILY_LOSS,
                    ATR_MULTIPLIER,
                    SYMBOL
                )
        else:
            logging.error("Failed to fetch real-time data.")
    except Exception as e:
        logging.error(f"Error in main function: {e}")


def execute_trading_strategy(
    data,
    max_trades_per_day,
    max_daily_loss,
    atr_multiplier,
    symbol,
    lookback=100
):
    try:
        if data is None or data.empty:
            logging.error("Data is invalid or empty. Trading strategy cannot be executed.")
            return
        if 'ema' not in data.columns or data['ema'].count() == 0:
            logging.critical("EMA indicator is missing or not calculated correctly. Exiting strategy.")
            return
        if 'high_volume' not in data.columns or data['high_volume'].count() == 0:
            logging.critical("High volume indicator is missing or not calculated correctly. Exiting strategy.")
            return
        if 'atr' not in data.columns or data['atr'].count() == 0:
            logging.critical("ATR indicator is missing or not calculated correctly. Exiting strategy.")
            return
        mean_atr = data['atr'].mean()
        trade_count = 0
        daily_loss = 0
        for index, row in data.iterrows():
            if daily_loss < -max_daily_loss:
                logging.debug(f"Avbryter: daily_loss ({daily_loss}) < -max_daily_loss ({-max_daily_loss})")
                break
            # ATR-villkor: endast köp/sälj om ATR är tillräckligt hög
            if row['atr'] <= atr_multiplier * mean_atr:
                logging.debug(f"Skippad rad {index}: ATR {row['atr']} <= {atr_multiplier} * mean_ATR {mean_atr}")
                continue
            bull_fvg_high, bull_fvg_low = detect_fvg(data.iloc[:index+1], lookback, bullish=True)
            bear_fvg_high, bear_fvg_low = detect_fvg(data.iloc[:index+1], lookback, bullish=False)
            long_condition = (
                not np.isnan(bull_fvg_high) and
                row['close'] < bull_fvg_low and
                row['close'] > row['ema'] and
                row['high_volume'] and
                row['within_trading_hours']
            )
            short_condition = (
                not np.isnan(bear_fvg_high) and
                row['close'] > bear_fvg_high and
                row['close'] < row['ema'] and
                row['high_volume'] and
                row['within_trading_hours']
            )
            logging.debug(f"Rad {index}: close={row['close']}, ema={row['ema']}, high_volume={row['high_volume']}, within_trading_hours={row['within_trading_hours']}, bull_fvg_high={bull_fvg_high}, bull_fvg_low={bull_fvg_low}, bear_fvg_high={bear_fvg_high}, bear_fvg_low={bear_fvg_low}")
            logging.debug(f"long_condition={long_condition}, short_condition={short_condition}")
            if long_condition and trade_count < max_trades_per_day:
                logging.info(f"Lägger KÖP-order på rad {index}")
                trade_count += 1
                # Beräkna stop loss och take profit nivåer
                stop_loss = row['close'] * (1 - STOP_LOSS_PERCENT / 100)
                take_profit = row['close'] * (1 + TAKE_PROFIT_PERCENT / 100)
                place_order('buy', symbol, 0.001, row['close'], stop_loss, take_profit)
            if short_condition and trade_count < max_trades_per_day:
                logging.info(f"Lägger SÄLJ-order på rad {index}")
                trade_count += 1
                stop_loss = row['close'] * (1 + STOP_LOSS_PERCENT / 100)
                take_profit = row['close'] * (1 - TAKE_PROFIT_PERCENT / 100)
                place_order('sell', symbol, 0.001, row['close'], stop_loss, take_profit)
    except Exception as e:
        logging.error(f"Error executing trading strategy: {e}")

# Signal handling

def signal_handler(sig, frame):
    logging.info("\nExiting program...")
    exit(0)

# Execute the main function to start the trading bot
# This is the primary execution flow of the program
if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT, signal_handler)
    # print("[DEBUG] Miljövariabler:")
    # print_env_vars()
    # Starta WebSocket-lyssnare i bakgrunden
    threading.Thread(target=lambda: asyncio.run(listen_order_updates()), daemon=True).start()
    asyncio.run(main())
    # Håll programmet igång så att WebSocket-lyssnaren lever
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Avslutar boten...")

def run_backtest(symbol, timeframe, limit, ema_length, volume_multiplier, trading_start_hour, trading_end_hour, max_trades_per_day, max_daily_loss, atr_multiplier, lookback=100, print_orders=False, save_to_file=None):
    """
    Kör backtest på historisk data och returnerar statistik.
    print_orders: Om True, skriv ut köp/sälj som skulle ha lagts.
    save_to_file: Om satt till filnamn, sparar trades till fil (CSV eller JSON).
    """
    data = fetch_market_data(symbol, timeframe, limit)
    if data is None or data.empty:
        logging.error("Ingen historisk data kunde hämtas för backtest.")
        return
    data = calculate_indicators(data, ema_length, volume_multiplier, trading_start_hour, trading_end_hour)
    if data is None:
        logging.error("Kunde inte beräkna indikatorer för backtest.")
        return
    trades = []
    trade_count = 0
    daily_loss = 0
    mean_atr = data['atr'].mean() if 'atr' in data.columns else 0
    for index, row in data.iterrows():
        if daily_loss < -max_daily_loss:
            break
        if 'atr' in row and row['atr'] <= atr_multiplier * mean_atr:
            continue
        bull_fvg_high, bull_fvg_low = detect_fvg(data.iloc[:index+1], lookback, bullish=True)
        bear_fvg_high, bear_fvg_low = detect_fvg(data.iloc[:index+1], lookback, bullish=False)
        long_condition = (
            not np.isnan(bull_fvg_high) and
            row['close'] < bull_fvg_low and
            row['close'] > row['ema'] and
            row['high_volume'] and
            row['within_trading_hours']
        )
        short_condition = (
            not np.isnan(bear_fvg_high) and
            row['close'] > bear_fvg_high and
            row['close'] < row['ema'] and
            row['high_volume'] and
            row['within_trading_hours']
        )
        if long_condition and trade_count < max_trades_per_day:
            trade_count += 1
            trades.append({'type': 'buy', 'price': row['close'], 'index': index})
            if print_orders:
                logging.info(f"[BACKTEST] BUY @ {row['close']} (index {index})")
        if short_condition and trade_count < max_trades_per_day:
            trade_count += 1
            trades.append({'type': 'sell', 'price': row['close'], 'index': index})
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
        if save_to_file.endswith('.json'):
            with open(save_to_file, 'w') as f:
                json.dump(trades, f, indent=2)
            logging.info(f"[BACKTEST] Trades sparade till {save_to_file} (JSON)")
        elif save_to_file.endswith('.csv'):
            with open(save_to_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=trades[0].keys())
                writer.writeheader()
                writer.writerows(trades)
            logging.info(f"[BACKTEST] Trades sparade till {save_to_file} (CSV)")
        else:
            logging.warning("[BACKTEST] Okänt filformat. Ange .json eller .csv.")
    return trades

async def listen_order_updates():
    import json
    import hmac
    import hashlib
    import time as time_mod
    from pytz import timezone
    from datetime import datetime
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")
    stockholm = timezone('Europe/Stockholm')
    def get_auth_payload():
        nonce = str(int(time_mod.time() * 1000))
        auth_payload = f'AUTH{nonce}'
        signature = hmac.new(
            API_SECRET.encode(),
            auth_payload.encode(),
            hashlib.sha384
        ).hexdigest()
        return {
            "event": "auth",
            "apiKey": API_KEY,
            "authSig": signature,
            "authPayload": auth_payload,
            "authNonce": nonce
        }
    uri = "wss://api.bitfinex.com/ws/2"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps(get_auth_payload()))
        print("[WS] Skickade auth-meddelande, väntar på order-event...")
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if isinstance(data, list) and len(data) > 1 and data[1] == 'oc':
                order_info = data[2]
                status = order_info[13]
                order_id = order_info[0]
                # Skriv tidsstämpel i Europe/Stockholm, alltid korrekt med sommartid
                now_stockholm = datetime.now(stockholm)
                with open("order_status_log.txt", "a") as f:
                    f.write(f"{now_stockholm.strftime('%Y-%m-%d %H:%M:%S.%f')}: Order-ID: {order_id}, Status: {status}, Info: {order_info}\n")
                print(f"[WS-ORDER] Order-ID: {order_id}, Status: {status}")
                logging.info(f"[WS-DEBUG] Fullt orderinfo: {order_info}")
                logging.info(f"[WS-DEBUG] Status-sträng: {status}")
                # Skicka e-postnotis om status börjar med EXECUTED, FILLED, CANCELLED, MODIFIED or CLOSED
                status_upper = str(status).upper()
                if EMAIL_NOTIFICATIONS and (
                    status_upper.startswith("EXECUTED") or
                    status_upper.startswith("CANCELLED") or
                    status_upper.startswith("MODIFIED") or
                    status_upper.startswith("FILLED") or
                    status_upper.startswith("CLOSED")
                ):
                    subject = f"Order status updated: {order_id}"
                    body = f"Order-ID: {order_id}\nStatus: {status}\nOrderinfo: {order_info}"
                    send_email_notification(subject, body)
            elif isinstance(data, dict) and data.get("event") == "auth":
                if data.get("status") == "OK":
                    print("[WS] Autentisering OK!")
                else:
                    print("[WS] Autentisering misslyckades:", data)

# Starta WebSocket-lyssnare i bakgrunden när boten startar
threading.Thread(target=lambda: asyncio.run(listen_order_updates()), daemon=True).start()

def print_env_vars():
    import os
    print("API_KEY:", os.getenv("API_KEY"))
    print("API_SECRET:", os.getenv("API_SECRET"))
    # print("COINBASE_API_KEY:", os.getenv("COINBASE_API_KEY"))
    # print("COINBASE_API_SECRET:", os.getenv("COINBASE_API_SECRET"))

if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT, signal_handler)
    # print("[DEBUG] Miljövariabler:")
    # print_env_vars()
    # Starta WebSocket-lyssnare i bakgrunden
    threading.Thread(target=lambda: asyncio.run(listen_order_updates()), daemon=True).start()
    asyncio.run(main())
    # Håll programmet igång så att WebSocket-lyssnaren lever
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Avslutar boten...")
