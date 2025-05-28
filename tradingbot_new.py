#!/usr/bin/env python3
"""
Tradingbot main entry point.
This script is the main entry point for the trading bot.
"""

import os
import sys
import logging
import ccxt
from datetime import datetime
import time
import argparse

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import core modules
from Tradingbot.core.config import load_config, validate_api_keys
from Tradingbot.utils.logging import setup_logging, StructuredLogger
from Tradingbot.core.bot import TradingBot
from Tradingbot.data.market_data import fetch_market_data, get_current_price, ensure_paper_trading_symbol
from Tradingbot.utils.indicators import calculate_indicators, detect_fvg
from Tradingbot.core.strategy import execute_trading_strategy, run_backtest


# Global variables
API_KEY = os.getenv("BITFINEX_API_KEY", "")
API_SECRET = os.getenv("BITFINEX_API_SECRET", "")
EXCHANGE_NAME = os.getenv("EXCHANGE", "bitfinex")
PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() in ("true", "1", "yes", "y")
SYMBOL = "tTESTBTC:TESTUSD" if PAPER_TRADING else "tBTCUSD"
TIMEFRAME = "1m"  # Default timeframe

# Configure logging
logger, structured_logger = setup_logging()


def setup_exchange():
    """Set up the exchange instance"""
    global exchange, EXCHANGE_NAME
    
    if not API_KEY or not API_SECRET:
        logger.warning("API keys not set. Using public API only.")
        exchange = getattr(ccxt, EXCHANGE_NAME.lower())()
    else:
        exchange_options = {
            "apiKey": API_KEY,
            "secret": API_SECRET,
            "enableRateLimit": True,
        }
        
        if PAPER_TRADING and EXCHANGE_NAME.lower() == "bitfinex":
            exchange_options["paper"] = True
            logger.info("Using Bitfinex Paper Trading")
        
        exchange = getattr(ccxt, EXCHANGE_NAME.lower())(exchange_options)
        
        # Verify API keys
        try:
            logger.info("Verifying API keys...")
            exchange.load_markets()
            logger.info("API keys verified successfully.")
        except ccxt.AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            logger.error("API keys are invalid. Using public API only.")
            exchange = getattr(ccxt, EXCHANGE_NAME.lower())()
        except Exception as e:
            logger.error(f"Error verifying API keys: {e}")
            
    return exchange


def run_trading_bot(config_file="config.json"):
    """Run the main trading bot loop"""
    # Load configuration
    config = load_config(config_file, logger)
    
    # Create trading bot instance
    bot = TradingBot(config_file)
    
    # Set up exchange
    exchange = setup_exchange()
    
    # Start the bot
    bot.start()
    
    try:
        while bot.running:
            structured_logger.info("Trading bot running...")
            
            # Execute strategy
            result = bot.execute_strategy(exchange, structured_logger)
            
            if "error" in result:
                structured_logger.error(f"Strategy execution error: {result['error']}")
            else:
                structured_logger.info(f"Strategy execution: {result.get('action', 'unknown')}")
            
            # Sleep for the configured interval
            interval_seconds = config.TIMEFRAME[:-1]  # Remove the 'm', 'h', etc.
            interval_unit = config.TIMEFRAME[-1]  # Get 'm', 'h', etc.
            
            if interval_unit == 'm':
                sleep_time = int(interval_seconds) * 60
            elif interval_unit == 'h':
                sleep_time = int(interval_seconds) * 3600
            else:
                sleep_time = 60  # Default to 1 minute
            
            structured_logger.info(f"Sleeping for {sleep_time} seconds...")
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        structured_logger.info("Trading bot stopped by user.")
        bot.stop()
    except Exception as e:
        structured_logger.error(f"Unexpected error: {e}")
        bot.stop()
        raise


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Trading Bot")
    
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run backtest instead of live trading",
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path to configuration file",
    )
    
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="Trading symbol",
    )
    
    parser.add_argument(
        "--timeframe",
        type=str,
        default=None,
        help="Trading timeframe (1m, 5m, 15m, 30m, 1h, etc.)",
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of candles to fetch for backtest",
    )
    
    parser.add_argument(
        "--paper",
        action="store_true",
        help="Use paper trading",
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    # Override global variables from command line arguments
    if args.paper:
        PAPER_TRADING = True
        SYMBOL = "tTESTBTC:TESTUSD"
    
    if args.symbol:
        SYMBOL = args.symbol
        if PAPER_TRADING and EXCHANGE_NAME.lower() == "bitfinex":
            SYMBOL = ensure_paper_trading_symbol(SYMBOL)
    
    if args.timeframe:
        TIMEFRAME = args.timeframe
    
    # Load configuration
    config = load_config(args.config, logger)
    
    # Set up exchange
    exchange = setup_exchange()
    
    # Override config with command line arguments
    if args.symbol:
        config.SYMBOL = SYMBOL
    if args.timeframe:
        config.TIMEFRAME = TIMEFRAME
    if args.limit:
        config.LIMIT = args.limit
    
    # Run backtest or live trading
    if args.backtest:
        structured_logger.info("Running backtest...")
        
        # Load additional parameters from config
        EMA_LENGTH = config.EMA_LENGTH
        VOLUME_MULTIPLIER = config.VOLUME_MULTIPLIER
        TRADING_START_HOUR = config.TRADING_START_HOUR
        TRADING_END_HOUR = config.TRADING_END_HOUR
        MAX_TRADES_PER_DAY = config.MAX_TRADES_PER_DAY
        MAX_DAILY_LOSS = config.MAX_DAILY_LOSS
        ATR_MULTIPLIER = config.ATR_MULTIPLIER
        LOOKBACK = config.LOOKBACK
        
        # Run backtest
        trades = run_backtest(
            config.SYMBOL,
            config.TIMEFRAME,
            config.LIMIT,
            config.EMA_LENGTH,
            config.VOLUME_MULTIPLIER,
            config.TRADING_START_HOUR,
            config.TRADING_END_HOUR,
            config.MAX_TRADES_PER_DAY,
            config.MAX_DAILY_LOSS,
            config.ATR_MULTIPLIER,
            exchange,
            fetch_market_data,
            calculate_indicators,
            config.LOOKBACK,
            print_orders=True,
            save_to_file="backtest_result.json",
        )
        
        structured_logger.info(f"Backtest completed with {len(trades)} trades.")
    else:
        structured_logger.info("Running live trading...")
        run_trading_bot(args.config)