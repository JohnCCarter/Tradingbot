"""
Tests for the modularized Tradingbot components.
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np
import json
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules to test
from Tradingbot.utils.indicators import calculate_indicators, detect_fvg
from Tradingbot.data.market_data import ensure_paper_trading_symbol, fetch_market_data
from Tradingbot.core.config import load_config, validate_api_keys
from Tradingbot.core.strategy import TradingStrategy, run_backtest


class TestIndicators(unittest.TestCase):
    """Test cases for indicator calculations"""
    
    def setUp(self):
        """Set up test data"""
        # Create sample OHLCV data
        timestamps = pd.date_range(
            "2021-01-01", periods=5, freq="h", tz="UTC"
        )
        self.sample_data = pd.DataFrame(
            {
                "timestamp": [int(ts.value / 1e6) for ts in timestamps],
                "open": [1, 2, 3, 4, 5],
                "high": [2, 3, 4, 5, 6],
                "low": [0.5, 1.5, 2.5, 3.5, 4.5],
                "close": [1.5, 2.5, 3.5, 4.5, 5.5],
                "volume": [10, 20, 30, 40, 50],
            }
        )
        self.sample_data["datetime"] = timestamps
        
    def test_calculate_indicators(self):
        """Test indicator calculation"""
        df = calculate_indicators(
            self.sample_data.copy(),
            ema_length=3,
            volume_multiplier=1.5,
            trading_start_hour=0,
            trading_end_hour=23,
        )
        
        # Check that all expected columns were added
        self.assertIn("ema", df.columns)
        self.assertIn("atr", df.columns)
        self.assertIn("high_volume", df.columns)
        self.assertIn("within_trading_hours", df.columns)
        
        # Check that values are calculated
        self.assertTrue(df["ema"].notnull().any())
        self.assertTrue(df["atr"].notnull().any())
        
    def test_detect_fvg(self):
        """Test FVG detection"""
        # Test bullish FVG
        high_bull, low_bull = detect_fvg(self.sample_data, lookback=2, bullish=True)
        self.assertEqual(high_bull, self.sample_data["high"].iloc[-2])
        self.assertEqual(low_bull, self.sample_data["low"].iloc[-1])
        
        # Test bearish FVG
        high_bear, low_bear = detect_fvg(self.sample_data, lookback=2, bullish=False)
        self.assertEqual(high_bear, self.sample_data["high"].iloc[-1])
        self.assertEqual(low_bear, self.sample_data["low"].iloc[-2])
        
        # Test with empty data
        empty_data = pd.DataFrame()
        high, low = detect_fvg(empty_data, lookback=2, bullish=True)
        self.assertTrue(np.isnan(high))
        self.assertTrue(np.isnan(low))


class TestMarketData(unittest.TestCase):
    """Test cases for market data handling"""
    
    def test_ensure_paper_trading_symbol(self):
        """Test paper trading symbol conversion"""
        # Standard CCXT format
        self.assertEqual(ensure_paper_trading_symbol("BTC/USD"), "tTESTBTC:TESTUSD")
        
        # Standard Bitfinex format
        self.assertEqual(ensure_paper_trading_symbol("tBTCUSD"), "tTESTBTCUSD")
        
        # Already in paper trading format
        self.assertEqual(ensure_paper_trading_symbol("tTESTBTC:TESTUSD"), "tTESTBTC:TESTUSD")
        
        # Simple symbol
        self.assertEqual(ensure_paper_trading_symbol("XRP"), "tTESTXRP")
    
    @patch("ccxt.Exchange")
    def test_fetch_market_data(self, mock_exchange):
        """Test fetching market data"""
        # Mock exchange response
        mock_ohlcv = [
            [1625097600000, 35000, 36000, 34000, 35500, 100],
            [1625097900000, 35500, 36500, 35000, 36000, 150],
        ]
        mock_exchange.fetch_ohlcv.return_value = mock_ohlcv
        mock_exchange.id = "bitfinex"
        mock_exchange.options = {"paper": True}
        
        # Test function
        df = fetch_market_data(mock_exchange, "BTC/USD", "1m", 2)
        
        # Verify exchange was called with correct parameters
        mock_exchange.fetch_ohlcv.assert_called_with("tTESTBTC:TESTUSD", "1m", limit=2)
        
        # Check result
        self.assertEqual(len(df), 2)
        self.assertIn("datetime", df.columns)
        self.assertEqual(df["close"].iloc[0], 35500)
        self.assertEqual(df["close"].iloc[1], 36000)


class TestConfig(unittest.TestCase):
    """Test cases for configuration handling"""
    
    def setUp(self):
        """Set up test data"""
        # Create a temporary config file for testing
        self.config_file = "/tmp/test_config.json"
        config_data = {
            "EXCHANGE": "bitfinex",
            "SYMBOL": "BTC/USD",
            "TIMEFRAME": "1m",
            "LIMIT": 100,
            "EMA_LENGTH": 14,
            "ATR_MULTIPLIER": 1.5,
            "VOLUME_MULTIPLIER": 1.2,
            "TRADING_START_HOUR": 0,
            "TRADING_END_HOUR": 23,
            "MAX_DAILY_LOSS": 100.0,
            "MAX_TRADES_PER_DAY": 10,
            "LOOKBACK": 20,
        }
        with open(self.config_file, "w") as f:
            json.dump(config_data, f)
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove the temporary config file
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
    
    def test_load_config(self):
        """Test loading configuration from file"""
        config = load_config(self.config_file)
        self.assertEqual(config.EXCHANGE, "bitfinex")
        self.assertEqual(config.SYMBOL, "BTC/USD")
        self.assertEqual(config.EMA_LENGTH, 14)
    
    def test_validate_api_keys(self):
        """Test API key validation"""
        # Valid keys
        validate_api_keys("valid_key", "valid_secret")
        
        # Invalid keys should raise ValueError
        with self.assertRaises(ValueError):
            validate_api_keys("", "")
        
        with self.assertRaises(ValueError):
            validate_api_keys("DUMMY_KEY", "DUMMY_SECRET")


class TestStrategy(unittest.TestCase):
    """Test cases for trading strategies"""
    
    def setUp(self):
        """Set up test data"""
        # Create sample OHLCV data with indicators
        timestamps = pd.date_range(
            "2021-01-01", periods=5, freq="h", tz="UTC"
        )
        self.sample_data = pd.DataFrame(
            {
                "timestamp": [int(ts.value / 1e6) for ts in timestamps],
                "open": [1, 2, 3, 4, 5],
                "high": [2, 3, 4, 5, 6],
                "low": [0.5, 1.5, 2.5, 3.5, 4.5],
                "close": [1.5, 2.5, 3.5, 4.5, 5.5],
                "volume": [10, 20, 30, 40, 50],
                "ema": [1.2, 2.2, 3.2, 4.2, 5.2],
                "atr": [0.5, 0.6, 0.7, 0.8, 0.9],
                "high_volume": [True, True, False, True, True],
                "within_trading_hours": [True, True, True, False, True],
            }
        )
        self.sample_data["datetime"] = timestamps
    
    @patch("Tradingbot.core.exchange.place_order")
    def test_trading_strategy_execute(self, mock_place_order):
        """Test TradingStrategy.execute method"""
        # Create strategy instance
        strategy = TradingStrategy(
            symbol="BTC/USD",
            ema_length=14,
            atr_multiplier=1.5,
            volume_multiplier=1.2,
            start_hour=0,
            end_hour=23,
            max_trades=5,
            max_loss=100,
            stop_loss_pct=2,
            take_profit_pct=4,
            lookback=2,
        )
        
        # Mock dependencies
        mock_exchange = MagicMock()
        mock_logger = MagicMock()
        
        # Test execution
        trade_count = strategy.execute(self.sample_data, mock_exchange, mock_logger)
        
        # Verify results
        self.assertGreaterEqual(trade_count, 0)
    
    @patch("Tradingbot.core.strategy.place_order")
    def test_run_backtest(self, mock_place_order):
        """Test run_backtest function"""
        # Mock dependencies
        mock_exchange = MagicMock()
        mock_data_fetcher = MagicMock(return_value=self.sample_data)
        mock_indicator_calculator = MagicMock(return_value=self.sample_data)
        
        # Run backtest
        trades = run_backtest(
            symbol="BTC/USD",
            timeframe="1m",
            limit=100,
            ema_length=14,
            volume_multiplier=1.2,
            trading_start_hour=0,
            trading_end_hour=23,
            max_trades_per_day=5,
            max_daily_loss=100,
            atr_multiplier=1.5,
            exchange=mock_exchange,
            data_fetcher=mock_data_fetcher,
            indicator_calculator=mock_indicator_calculator,
            lookback=2,
        )
        
        # Verify results
        self.assertIsInstance(trades, list)
        mock_data_fetcher.assert_called_once()
        mock_indicator_calculator.assert_called_once()


if __name__ == "__main__":
    unittest.main()