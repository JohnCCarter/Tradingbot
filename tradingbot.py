import time
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

# Create timezone object once
LOCAL_TIMEZONE = timezone('Europe/Stockholm')

# Load environment variables
load_dotenv()

# Constants
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
if not API_SECRET:
    raise ValueError("API_SECRET is not set. Please check your environment variables.")
# Constants
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
if not API_KEY or not API_SECRET:
    raise ValueError("API_KEY and API_SECRET are required. Please check your environment variables.")

# Load config from config.json
with open("config.json") as f:
    config = json.load(f)

# Validate config values
required_config_keys = ["SYMBOL", "TIMEFRAME", "LIMIT", "EMA_LENGTH", "ATR_MULTIPLIER", "VOLUME_MULTIPLIER", "TRADING_START_HOUR", "TRADING_END_HOUR", "MAX_DAILY_LOSS", "MAX_TRADES_PER_DAY"]
for key in required_config_keys:
    if key not in config:
        raise ValueError(f"Missing required key '{key}' in config.json")

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

# Initialize exchange
exchange = ccxt.bitfinex({
    'apiKey': API_KEY,
    'secret': API_SECRET
})
exchange.nonce = lambda: int(time.time() * 1000)

# Utility functions

def fetch_balance():
    try:
        return exchange.fetch_balance()
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return None


def fetch_market_data(symbol, timeframe, limit):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv or not all(len(row) == 6 for row in ohlcv):
            print("Warning: Malformed or incomplete data fetched from API.")
            return None
        data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        data['datetime'] = pd.to_datetime(data['timestamp'], unit='ms', utc=True)
        return data
    except Exception as e:
        print(f"Error fetching market data: {e}")
        return None


def calculate_indicators(
    data, ema_length, volume_multiplier, trading_start_hour, trading_end_hour
):
    try:
        # print("\n[DEBUG] DataFrame head before indicator calculation:")
        # print(data.head())
        # print("[DEBUG] DataFrame info:")
        # print(data.info())
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
        print(f"Error calculating indicators: {e}")
        return None


def detect_fvg(data, lookback, bullish=True):
    # Förenklad FVG: returnera alltid senaste high/low för bullish/bearish
    if len(data) < 2:
        return np.nan, np.nan
    if bullish:
        return data['high'].iloc[-2], data['low'].iloc[-1]
    else:
        return data['high'].iloc[-1], data['low'].iloc[-2]


def place_order(order_type, symbol, amount, price=None):
    if amount <= 0:
        print(f"Invalid order amount: {amount}. Amount must be positive.")
        return

    try:
        if order_type == 'buy':
            order = exchange.create_limit_buy_order(symbol, amount, price) if price else exchange.create_market_buy_order(symbol, amount)
        elif order_type == 'sell':
            order = exchange.create_limit_sell_order(symbol, amount, price) if price else exchange.create_market_sell_order(symbol, amount)

        print("\nOrder Information:")
        print(f"Type: {order_type.capitalize()}")
        print(f"Symbol: {symbol}")
        print(f"Amount: {amount}")
        if price:
            print(f"Price: {price}")
        
        # Visa endast relevanta fält från Order Details
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
    except Exception as e:
        print(f"Error placing {order_type} order: {e}")


def get_current_price(symbol):
    try:
        ticker = exchange.fetch_ticker(symbol)
        if 'last' in ticker:
            return ticker['last']
        else:
            print("Warning: 'last' key not found in ticker data.")
            return None
    except Exception as e:
        print(f"Error fetching current price: {e}")
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
                print(f"Login successful for user <{data.get('userId')}>.")
    except websockets.exceptions.InvalidURI as e:
        print(f"Invalid WebSocket URI: {e}")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"WebSocket connection closed unexpectedly: {e}")
    except Exception as e:
        print(f"WebSocket authentication error: {e}")


async def fetch_realtime_data():
    max_retries = 5
    retry_delay = 5  # seconds
    retries = 0

    while retries < max_retries:
        try:
            async with websockets.connect("wss://api.bitfinex.com/ws/2") as websocket:
                subscription_message = {
                    "event": "subscribe",
                    "channel": "candles",
                    "key": f"trade:1m:{SYMBOL}"
                }
                await websocket.send(json.dumps(subscription_message))
                print("Subscribed to real-time data...")
                async for message in websocket:
                    data = json.loads(message)
                    if isinstance(data, list) and len(data) > 1:
                        return data
        except websockets.exceptions.ConnectionClosed as e:
            print(f"WebSocket connection closed: {e}. Retrying in {retry_delay} seconds...")
            retries += 1
            await asyncio.sleep(retry_delay)
        except Exception as e:
            print(f"Error fetching real-time data: {e}")
            return None

    print("Max retries reached. Failed to fetch real-time data.")
    return None


def convert_to_local_time(utc_time):
    try:
        return utc_time.astimezone(LOCAL_TIMEZONE)
    except Exception as e:
        print(f"Error converting time: {e}")
        return utc_time


def process_realtime_data(raw_data):
    try:
        candles = raw_data[1] if isinstance(raw_data, list) and len(raw_data) > 1 else []
        columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        data = pd.DataFrame(candles, columns=columns)
        data['datetime'] = pd.to_datetime(data['timestamp'], unit='ms', utc=True)
        data['local_datetime'] = data['datetime'].apply(convert_to_local_time)
        print("Structured Data:")
        print(data.head())
        return data
    except Exception as e:
        print(f"Error processing real-time data: {e}")
        return None


async def main():
    try:
        print("Fetching real-time data...")
        realtime_data = await fetch_realtime_data()
        if realtime_data:
            structured_data = process_realtime_data(realtime_data)
            if structured_data is not None:
                print("Real-time data processing completed.")
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
            print("Failed to fetch real-time data.")
    except Exception as e:
        print(f"Error in main function: {e}")


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
            print("Error: Data is invalid or empty. Trading strategy cannot be executed.")
            return
        if 'ema' not in data.columns or data['ema'].count() == 0:
            print("Critical Error: EMA indicator is missing or not calculated correctly. Exiting strategy.")
            return
        if 'high_volume' not in data.columns or data['high_volume'].count() == 0:
            print(
                "Critical Error: High volume indicator is missing or not calculated correctly. "
                "Exiting strategy."
            )
            return
        if 'atr' not in data.columns or data['atr'].count() == 0:
            print("Critical Error: ATR indicator is missing or not calculated correctly. Exiting strategy.")
            return
        mean_atr = data['atr'].mean()
        trade_count = 0
        daily_loss = 0
        for index, row in data.iterrows():
            if daily_loss < -max_daily_loss:
                print(f"[DEBUG] Avbryter: daily_loss ({daily_loss}) < -max_daily_loss ({-max_daily_loss})")
                break
            # ATR-villkor: endast köp/sälj om ATR är tillräckligt hög
            if row['atr'] <= atr_multiplier * mean_atr:
                print(f"[DEBUG] Skippad rad {index}: ATR {row['atr']} <= {atr_multiplier} * mean_ATR {mean_atr}")
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
            print(f"[DEBUG] Rad {index}: close={row['close']}, ema={row['ema']}, high_volume={row['high_volume']}, within_trading_hours={row['within_trading_hours']}, bull_fvg_high={bull_fvg_high}, bull_fvg_low={bull_fvg_low}, bear_fvg_high={bear_fvg_high}, bear_fvg_low={bear_fvg_low}")
            print(f"[DEBUG] long_condition={long_condition}, short_condition={short_condition}")
            if long_condition and trade_count < max_trades_per_day:
                print(f"[DEBUG] Lägger KÖP-order på rad {index}")
                trade_count += 1
                place_order('buy', symbol, 0.001, row['close'])
            if short_condition and trade_count < max_trades_per_day:
                print(f"[DEBUG] Lägger SÄLJ-order på rad {index}")
                trade_count += 1
                place_order('sell', symbol, 0.001, row['close'])
    except Exception as e:
        print(f"Error executing trading strategy: {e}")

# Signal handling

def signal_handler(sig, frame):
    print("\nExiting program...")
    exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Execute the main function to start the trading bot
# This is the primary execution flow of the program
asyncio.run(main())

def run_backtest(symbol, timeframe, limit, ema_length, volume_multiplier, trading_start_hour, trading_end_hour, max_trades_per_day, max_daily_loss, atr_multiplier, lookback=100, print_orders=False, save_to_file=None):
    """
    Kör backtest på historisk data och returnerar statistik.
    print_orders: Om True, skriv ut köp/sälj som skulle ha lagts.
    save_to_file: Om satt till filnamn, sparar trades till fil (CSV eller JSON).
    """
    data = fetch_market_data(symbol, timeframe, limit)
    if data is None or data.empty:
        print("Ingen historisk data kunde hämtas för backtest.")
        return
    data = calculate_indicators(data, ema_length, volume_multiplier, trading_start_hour, trading_end_hour)
    if data is None:
        print("Kunde inte beräkna indikatorer för backtest.")
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
                print(f"[BACKTEST] BUY @ {row['close']} (index {index})")
        if short_condition and trade_count < max_trades_per_day:
            trade_count += 1
            trades.append({'type': 'sell', 'price': row['close'], 'index': index})
            if print_orders:
                print(f"[BACKTEST] SELL @ {row['close']} (index {index})")
    print(f"[BACKTEST] Antal trades: {len(trades)}")
    if trades:
        print(f"[BACKTEST] Första trade: {trades[0]}")
        print(f"[BACKTEST] Sista trade: {trades[-1]}")
    else:
        print("[BACKTEST] Inga trades genererades.")
    if save_to_file and trades:
        import json, csv
        if save_to_file.endswith('.json'):
            with open(save_to_file, 'w') as f:
                json.dump(trades, f, indent=2)
            print(f"[BACKTEST] Trades sparade till {save_to_file} (JSON)")
        elif save_to_file.endswith('.csv'):
            with open(save_to_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=trades[0].keys())
                writer.writeheader()
                writer.writerows(trades)
            print(f"[BACKTEST] Trades sparade till {save_to_file} (CSV)")
        else:
            print("[BACKTEST] Okänt filformat. Ange .json eller .csv.")
    return trades
