"""
Backward compatibility adapter for Tradingbot.
This module provides compatibility with the older codebase.
"""

# Import from new modules
from Tradingbot.data.market_data import (
    fetch_market_data,
    get_current_price,
    ensure_paper_trading_symbol,
)
from Tradingbot.utils.indicators import calculate_indicators, detect_fvg
from Tradingbot.core.strategy import execute_trading_strategy, run_backtest
from Tradingbot.core.exchange import place_order, create_exchange
from Tradingbot.core.config import load_config
from Tradingbot.utils.logging import setup_logging

import os
import ccxt
import json
import logging
import numpy as np
import pandas as pd
import time

# Set up global variables
API_KEY = os.getenv("BITFINEX_API_KEY", "")
API_SECRET = os.getenv("BITFINEX_API_SECRET", "")
EXCHANGE_NAME = "bitfinex"
PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() in ("true", "1", "yes", "y")

# Set up exchange
exchange = None
if not API_KEY or not API_SECRET:
    exchange = getattr(ccxt, EXCHANGE_NAME.lower())()
else:
    exchange_options = {
        "apiKey": API_KEY,
        "secret": API_SECRET,
        "enableRateLimit": True,
    }
    
    if PAPER_TRADING and EXCHANGE_NAME.lower() == "bitfinex":
        exchange_options["paper"] = True
    
    exchange = getattr(ccxt, EXCHANGE_NAME.lower())(exchange_options)

# Load configuration
config = {}
try:
    with open("config.json") as f:
        config = json.load(f)
except Exception:
    # Default configuration
    config = {
        "SYMBOL": "tTESTBTC:TESTUSD" if PAPER_TRADING else "tBTCUSD",
        "TIMEFRAME": "1m",
        "LIMIT": 100,
        "EMA_LENGTH": 14,
        "ATR_MULTIPLIER": 1.5,
        "VOLUME_MULTIPLIER": 1.2,
        "TRADING_START_HOUR": 0,
        "TRADING_END_HOUR": 23,
        "MAX_DAILY_LOSS": 100.0,
        "MAX_TRADES_PER_DAY": 10,
        "STOP_LOSS_PERCENT": 2.0,
        "TAKE_PROFIT_PERCENT": 4.0,
        "LOOKBACK": 20,
    }

# Set up global constants from config
SYMBOL = config.get("SYMBOL", "tTESTBTC:TESTUSD" if PAPER_TRADING else "tBTCUSD")
TIMEFRAME = config.get("TIMEFRAME", "1m")
LIMIT = config.get("LIMIT", 100)
EMA_LENGTH = config.get("EMA_LENGTH", 14)
ATR_MULTIPLIER = config.get("ATR_MULTIPLIER", 1.5)
VOLUME_MULTIPLIER = config.get("VOLUME_MULTIPLIER", 1.2)
TRADING_START_HOUR = config.get("TRADING_START_HOUR", 0)
TRADING_END_HOUR = config.get("TRADING_END_HOUR", 23)
MAX_DAILY_LOSS = config.get("MAX_DAILY_LOSS", 100.0)
MAX_TRADES_PER_DAY = config.get("MAX_TRADES_PER_DAY", 10)
LOOKBACK = config.get("LOOKBACK", 20)

# Set up logging
logger, structured_logger = setup_logging()


# Compatibility functions that match the original API

def get_current_price(symbol=SYMBOL):
    """
    Compatibility wrapper for get_current_price
    
    Args:
        symbol: Symbol to get price for
    
    Returns:
        float: Current price
    """
    from Tradingbot.data.market_data import get_current_price as _get_current_price
    return _get_current_price(exchange, symbol)


def place_order(order_type, symbol, amount, price=None, stop_loss=None, take_profit=None):
    """
    Compatibility wrapper for place_order
    
    Args:
        order_type: 'buy' or 'sell'
        symbol: Trading symbol
        amount: Amount to trade
        price: Price (None for market order)
        stop_loss: Stop loss price
        take_profit: Take profit price
        
    Returns:
        dict: Order result
    """
    from Tradingbot.core.exchange import place_order as _place_order
    return _place_order(
        exchange, 
        structured_logger, 
        order_type, 
        symbol, 
        amount, 
        price, 
        stop_loss, 
        take_profit,
        TEST_BUY_ORDER=config.get("TEST_BUY_ORDER", True),
        TEST_SELL_ORDER=config.get("TEST_SELL_ORDER", True),
        TEST_LIMIT_ORDERS=config.get("TEST_LIMIT_ORDERS", True),
    )


def fetch_market_data(exchange, symbol, timeframe="1h", limit=100):
    """
    Compatibility wrapper for fetch_market_data
    """
    from Tradingbot.data.market_data import fetch_market_data as _fetch_market_data
    return _fetch_market_data(exchange, symbol, timeframe, limit)


def calculate_indicators(
    data, ema_length, volume_multiplier, trading_start_hour, trading_end_hour
):
    """
    Compatibility wrapper for calculate_indicators
    """
    from Tradingbot.utils.indicators import calculate_indicators as _calculate_indicators
    return _calculate_indicators(
        data, ema_length, volume_multiplier, trading_start_hour, trading_end_hour
    )


def detect_fvg(data, lookback, bullish=True):
    """
    Compatibility wrapper for detect_fvg
    """
    from Tradingbot.utils.indicators import detect_fvg as _detect_fvg
    return _detect_fvg(data, lookback, bullish)


def execute_trading_strategy(
    data, max_trades_per_day, max_daily_loss, atr_multiplier, symbol, lookback=100
):
    """
    Compatibility wrapper for execute_trading_strategy
    """
    from Tradingbot.core.strategy import execute_trading_strategy as _execute_trading_strategy
    return _execute_trading_strategy(
        data, 
        max_trades_per_day, 
        max_daily_loss, 
        atr_multiplier, 
        symbol,
        exchange,
        structured_logger,
        lookback
    )


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
    Compatibility wrapper for run_backtest
    """
    from Tradingbot.core.strategy import run_backtest as _run_backtest
    return _run_backtest(
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
        exchange,
        fetch_market_data,
        calculate_indicators,
        lookback,
        print_orders,
        save_to_file,
    )


# Expose all imports to maintain backward compatibility
__all__ = [
    'fetch_market_data',
    'get_current_price',
    'ensure_paper_trading_symbol',
    'calculate_indicators',
    'detect_fvg',
    'execute_trading_strategy',
    'run_backtest',
    'place_order',
    'exchange',
    'SYMBOL',
    'TIMEFRAME',
    'LIMIT',
    'EMA_LENGTH',
    'ATR_MULTIPLIER',
    'VOLUME_MULTIPLIER',
    'TRADING_START_HOUR',
    'TRADING_END_HOUR',
    'MAX_DAILY_LOSS',
    'MAX_TRADES_PER_DAY',
    'LOOKBACK',
    'PAPER_TRADING',
    'EXCHANGE_NAME',
]