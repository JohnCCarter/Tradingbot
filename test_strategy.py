import sys
import os
import unittest
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the modules we want to test
try:
    from strategy import (
        StrategyBase,
        MACDStrategy,
        BollingerBandsStrategy,
        EnhancedFVGStrategy,
        CombinedStrategy,
        create_strategy
    )
except ImportError:
    print("Could not import strategy module. Make sure it exists in the correct location.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestStrategy(unittest.TestCase):
    """Test cases for the strategy module"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a sample dataframe with OHLCV data
        timestamps = pd.date_range(start='2023-01-01', periods=100, freq='H')
        
        # Create realistic price data with some trends and volatility
        seed_price = 100.0
        close_prices = []
        high_prices = []
        low_prices = []
        open_prices = []
        volumes = []
        
        # Generate synthetic price data
        for i in range(100):
            # Add some randomness and trend
            price_change = np.random.normal(0, 1) + (i % 20 - 10) * 0.05
            seed_price += price_change
            
            # Add some random variation for high/low
            high_offset = abs(np.random.normal(0, 0.5))
            low_offset = abs(np.random.normal(0, 0.5))
            
            close_prices.append(seed_price)
            high_prices.append(seed_price + high_offset)
            low_prices.append(max(0.1, seed_price - low_offset))  # Ensure positive
            
            # Open price is previous close or initial value
            if i == 0:
                open_prices.append(seed_price - np.random.normal(0, 0.5))
            else:
                open_prices.append(close_prices[i-1])
            
            # Generate volume with some spikes
            base_vol = 1000 + i % 50 * 20
            vol_spike = np.random.choice([1, 1, 1, 1, 2, 3, 5])  # Occasional spikes
            volumes.append(base_vol * vol_spike)
        
        # Create the dataframe
        self.sample_data = pd.DataFrame({
            'timestamp': timestamps.astype(np.int64) // 10**6,
            'datetime': timestamps,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volumes
        })
        
        logger.info(f"Created sample data with {len(self.sample_data)} rows")
    
    def test_strategy_base(self):
        """Test the base strategy class"""
        strategy = StrategyBase("BTC/USD")
        
        # Should return unchanged data
        result = strategy.prepare_data(self.sample_data)
        self.assertEqual(len(result), len(self.sample_data))
        pd.testing.assert_frame_equal(result, self.sample_data)
        
        # Base strategy should generate no signals
        signals = strategy.get_signals(self.sample_data)
        self.assertIn('signal', signals.columns)
        self.assertEqual(signals['signal'].sum(), 0)  # No signals
        
        logger.info("Base strategy test passed")
    
    def test_macd_strategy(self):
        """Test MACD strategy"""
        strategy = MACDStrategy("BTC/USD", {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9,
            'volume_filter': True
        })
        
        # Prepare data should add MACD indicators
        prepared_data = strategy.prepare_data(self.sample_data)
        self.assertIn('macd', prepared_data.columns)
        self.assertIn('macd_signal', prepared_data.columns)
        
        # Should generate signals
        signals = strategy.get_signals(self.sample_data)
        self.assertIn('signal', signals.columns)
        self.assertIn(-1, signals['signal'].unique().tolist() + [0, 1])
        self.assertIn(0, signals['signal'].unique())
        
        logger.info("MACD strategy test passed")
    
    def test_bollinger_bands_strategy(self):
        """Test Bollinger Bands strategy"""
        strategy = BollingerBandsStrategy("BTC/USD", {
            'bb_window': 20,
            'bb_std': 2.0,
            'rsi_filter': True,
        })
        
        # Prepare data should add Bollinger Bands indicators
        prepared_data = strategy.prepare_data(self.sample_data)
        self.assertIn('bb_upper', prepared_data.columns)
        self.assertIn('bb_lower', prepared_data.columns)
        
        # Should generate signals
        signals = strategy.get_signals(self.sample_data)
        self.assertIn('signal', signals.columns)
        
        logger.info("Bollinger Bands strategy test passed")
    
    def test_enhanced_fvg_strategy(self):
        """Test Enhanced FVG strategy"""
        strategy = EnhancedFVGStrategy("BTC/USD", {
            'lookback': 5,
            'atr_multiplier': 1.5,
            'use_support_resistance': True
        })
        
        # Generate signals
        signals = strategy.get_signals(self.sample_data)
        self.assertIn('signal', signals.columns)
        
        logger.info("Enhanced FVG strategy test passed")
    
    def test_combined_strategy(self):
        """Test Combined strategy"""
        strategy = CombinedStrategy("BTC/USD", {
            'macd': {
                'fast_period': 12,
                'slow_period': 26,
            },
            'bollinger': {
                'bb_window': 20,
                'bb_std': 2.0,
            },
            'fvg': {
                'lookback': 5,
                'use_support_resistance': True
            },
            'weights': [0.4, 0.3, 0.3]
        })
        
        # Generate signals
        signals = strategy.get_signals(self.sample_data)
        self.assertIn('signal', signals.columns)
        
        logger.info("Combined strategy test passed")
    
    def test_create_strategy(self):
        """Test strategy factory function"""
        # Test with valid strategy type
        macd_strategy = create_strategy('macd', 'BTC/USD')
        self.assertIsInstance(macd_strategy, MACDStrategy)
        
        # Test with invalid strategy type (should default to combined)
        unknown_strategy = create_strategy('nonexistent', 'BTC/USD')
        self.assertIsInstance(unknown_strategy, CombinedStrategy)
        
        logger.info("Create strategy test passed")


if __name__ == "__main__":
    unittest.main()