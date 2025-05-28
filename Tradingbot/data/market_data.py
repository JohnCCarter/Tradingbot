"""
Market data handling for Tradingbot.
Provides functions for fetching and processing market data.
"""

import pandas as pd
import logging
import asyncio
import json
import websockets
import time as _time
import functools
from functools import lru_cache


def retry(max_attempts=3, initial_delay=1):
    """
    Retry decorator for functions that might fail temporarily.
    
    Args:
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay before retrying (doubles with each attempt)
    
    Returns:
        Decorated function
    """
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


def ensure_paper_trading_symbol(symbol):
    """
    Converts symbols to the correct Bitfinex paper trading format (tTESTXXX:TESTYYY)

    Examples:
    - 'BTC/USD' -> 'tTESTBTC:TESTUSD'
    - 'tBTCUSD' -> 'tTESTBTC:TESTUSD'
    - 'tTESTBTC:TESTUSD' -> 'tTESTBTC:TESTUSD' (no change)
    
    Args:
        symbol: Symbol to convert
    
    Returns:
        str: Converted symbol
    """
    # If symbol already has the right prefix, return unchanged
    if symbol.startswith("tTEST"):
        return symbol

    # Handle standard CCXT format (BTC/USD)
    if "/" in symbol:
        base, quote = symbol.split("/")
        return f"tTEST{base}:TEST{quote}"

    # Handle standard Bitfinex format without TEST (tBTCUSD)
    if symbol.startswith("t") and not symbol.startswith("tTEST"):
        return f"tTEST{symbol[1:]}"

    # Fallback: Add TEST prefix and log warning
    logging.warning(f"Unknown symbol format: {symbol}, trying to add TEST prefix")
    return f"tTEST{symbol}"


@retry(max_attempts=3, initial_delay=1)
@lru_cache(maxsize=32)
def fetch_market_data(exchange, symbol, timeframe="1h", limit=100):
    """
    Fetch market data from exchange
    
    Args:
        exchange: Exchange instance
        symbol: Trading symbol
        timeframe: Timeframe ('1m', '5m', '1h', etc)
        limit: Maximum number of candles to fetch
    
    Returns:
        DataFrame: OHLCV data
    """
    try:
        # Convert symbol to the right format for Bitfinex paper trading
        if exchange.id == "bitfinex" and exchange.options.get("paper", False):
            formatted_symbol = ensure_paper_trading_symbol(symbol)
            logging.info(
                f"Using paper trading symbol: {formatted_symbol} (original {symbol})"
            )
            symbol = formatted_symbol

        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(
            ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        # Ensure timestamp is int and create datetime column
        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        return df
    except Exception as e:
        logging.error(f"Could not fetch market data for {symbol}: {e}")
        return pd.DataFrame()


@retry(max_attempts=3, initial_delay=1)
def get_current_price(exchange, symbol):
    """
    Get current price for a symbol
    
    Args:
        exchange: Exchange instance
        symbol: Trading symbol
    
    Returns:
        float: Current price or None if failed
    """
    try:
        # Ensure correct symbol format for paper trading
        if exchange.id == "bitfinex":
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


async def fetch_realtime_data(websocket_uri, symbol, timeframe="1m"):
    """
    Fetch real-time data from WebSocket
    
    Args:
        websocket_uri: WebSocket URI
        symbol: Trading symbol
        timeframe: Timeframe ('1m', '5m', '1h', etc)
    
    Returns:
        list: Real-time data or None if failed
    """
    retry_delay = 5  # seconds
    retries = 0
    channel_id = None
    candles = []
    try:
        async with websockets.connect(websocket_uri) as websocket:
            subscription_message = {
                "event": "subscribe",
                "channel": "candles",
                "key": f"trade:{timeframe}:{symbol}",
            }
            await websocket.send(json.dumps(subscription_message))
            logging.info("Subscribed to real-time data...")
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                logging.debug(f"WebSocket message: {data}")
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
                        logging.debug(
                            f"Received pong: cid={data.get('cid')} ts={data.get('ts')}"
                        )
                        continue
                if isinstance(data, list) and len(data) > 1 and data[1] == "hb":
                    continue
                if isinstance(data, list) and (
                    channel_id is None or data[0] == channel_id
                ):
                    # Snapshot: [chanId, [ [candle1], [candle2], ... ] ]
                    if isinstance(data[1], list) and isinstance(data[1][0], list):
                        candles = data[1]
                        logging.info(f"Received snapshot with {len(candles)} candles.")
                        # Bitfinex candle format: [MTS, OPEN, CLOSE, HIGH, LOW, VOLUME]
                        return [data[0], candles]
                    # Update: [chanId, [candle]]
                    elif isinstance(data[1], list) and isinstance(
                        data[1][0], (int, float)
                    ):
                        candles.append(data[1])
                        logging.info(f"Received candle update: {data[1]}")
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


def process_realtime_data(raw_data):
    """
    Process real-time data from WebSocket
    
    Args:
        raw_data: Raw data from WebSocket
    
    Returns:
        DataFrame: Processed data
    """
    try:
        if not isinstance(raw_data, list):
            logging.error(
                f"process_realtime_data: Skipped non-list raw_data: {raw_data}"
            )
            return None
        candles = raw_data[1] if len(raw_data) > 1 else []
        if not candles:
            logging.warning(
                f"process_realtime_data: Empty candles in raw_data: {raw_data}"
            )
        # Bitfinex candle format: [MTS, OPEN, CLOSE, HIGH, LOW, VOLUME]
        # Map to DataFrame columns: timestamp, open, close, high, low, volume
        columns = ["timestamp", "open", "close", "high", "low", "volume"]
        if candles and isinstance(candles[0], (list, tuple)):
            data = pd.DataFrame(candles, columns=columns)
        else:
            data = pd.DataFrame([], columns=columns)
        if not data.empty:
            data["datetime"] = pd.to_datetime(data["timestamp"], unit="ms", utc=True)
        else:
            data["datetime"] = pd.Series(dtype="datetime64[ns, UTC]")
        logging.info(f"Structured Data: {data.head()}")
        return data
    except Exception as e:
        logging.error(f"Error processing real-time data: {e}")
        return None


async def fetch_historical_data_async(exchange, symbol, timeframe, limit):
    """
    Async wrapper around fetch_market_data
    
    Args:
        exchange: Exchange instance
        symbol: Trading symbol
        timeframe: Timeframe
        limit: Maximum number of candles
    
    Returns:
        DataFrame: Historical data
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, fetch_market_data, exchange, symbol, timeframe, limit
    )