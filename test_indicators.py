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
    from indicators import (
        calculate_macd,
        calculate_bollinger_bands,
        detect_support_resistance,
        analyze_volume,
        calculate_all_indicators
    )
except ImportError:
    print("Could not import indicators module. Make sure it exists in the correct location.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestIndicators(unittest.TestCase):
    """Test cases for the indicators module"""
    
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
    
    def test_calculate_macd(self):
        """Test MACD calculation"""
        result = calculate_macd(self.sample_data)
        
        # Check that the result contains required columns
        self.assertIn('macd', result.columns)
        self.assertIn('macd_signal', result.columns)
        self.assertIn('macd_hist', result.columns)
        
        # Check that values are calculated (not all NaN)
        self.assertTrue(result['macd'].notna().any())
        self.assertTrue(result['macd_signal'].notna().any())
        self.assertTrue(result['macd_hist'].notna().any())
        
        # MACD line should be the difference between fast and slow EMAs
        self.assertAlmostEqual(
            result['ema_fast'].iloc[-1] - result['ema_slow'].iloc[-1],
            result['macd'].iloc[-1],
            places=4
        )
        
        logger.info("MACD test passed")
    
    def test_calculate_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        result = calculate_bollinger_bands(self.sample_data)
        
        # Check that the result contains required columns
        self.assertIn('bb_middle', result.columns)
        self.assertIn('bb_upper', result.columns)
        self.assertIn('bb_lower', result.columns)
        
        # Check that values are calculated (not all NaN)
        self.assertTrue(result['bb_middle'].notna().any())
        self.assertTrue(result['bb_upper'].notna().any())
        self.assertTrue(result['bb_lower'].notna().any())
        
        # Upper band should be higher than middle band
        self.assertTrue((result['bb_upper'] > result['bb_middle']).all())
        
        # Lower band should be lower than middle band
        self.assertTrue((result['bb_lower'] < result['bb_middle']).all())
        
        # Middle band should be the rolling mean of close
        pd.testing.assert_series_equal(
            result['bb_middle'],
            result['close'].rolling(window=20).mean(),
            check_exact=False,
            rtol=1e-10
        )
        
        logger.info("Bollinger Bands test passed")
    
    def test_detect_support_resistance(self):
        """Test support and resistance detection"""
        result = detect_support_resistance(self.sample_data)
        
        # Check that the result contains required columns
        self.assertIn('is_support', result.columns)
        self.assertIn('is_resistance', result.columns)
        self.assertIn('support_level', result.columns)
        self.assertIn('resistance_level', result.columns)
        
        # There should be some support/resistance levels detected
        # (but not necessarily in this random data)
        
        # Support levels should be populated only where is_support is True
        non_support_levels = result.loc[~result['is_support'], 'support_level']
        if len(non_support_levels) > 0:
            self.assertTrue(non_support_levels.isna().all())
        
        # Resistance levels should be populated only where is_resistance is True
        non_resistance_levels = result.loc[~result['is_resistance'], 'resistance_level']
        if len(non_resistance_levels) > 0:
            self.assertTrue(non_resistance_levels.isna().all())
        
        logger.info("Support/resistance test passed")
    
    def test_analyze_volume(self):
        """Test volume analysis"""
        result = analyze_volume(self.sample_data)
        
        # Check that the result contains required columns
        self.assertIn('vol_sma_short', result.columns)
        self.assertIn('vol_sma_long', result.columns)
        self.assertIn('vol_ratio', result.columns)
        self.assertIn('vol_surge', result.columns)
        
        # Check that values are calculated (not all NaN)
        self.assertTrue(result['vol_sma_short'].notna().any())
        self.assertTrue(result['vol_sma_long'].notna().any())
        self.assertTrue(result['vol_ratio'].notna().any())
        
        # Volume ratio should be short SMA / long SMA
        pd.testing.assert_series_equal(
            result['vol_ratio'],
            result['vol_sma_short'] / result['vol_sma_long'],
            check_exact=False,
            rtol=1e-10
        )
        
        logger.info("Volume analysis test passed")
    
    def test_calculate_all_indicators(self):
        """Test calculation of all indicators"""
        result = calculate_all_indicators(self.sample_data)
        
        # Check that the result contains key indicator columns
        required_columns = [
            'ema', 'atr', 'high_volume', 'rsi', 'within_trading_hours',
            'macd', 'macd_signal', 'macd_hist',
            'bb_upper', 'bb_middle', 'bb_lower',
            'vol_ratio', 'vol_surge'
        ]
        
        for col in required_columns:
            self.assertIn(col, result.columns)
            self.assertTrue(result[col].notna().any())
        
        # Validate data hasn't been corrupted
        self.assertEqual(len(result), len(self.sample_data))
        pd.testing.assert_series_equal(result['close'], self.sample_data['close'])
        
        logger.info("Calculate all indicators test passed")
    
    def test_error_handling(self):
        """Test error handling with bad data"""
        # Test with empty DataFrame
        empty_df = pd.DataFrame()
        with self.assertRaises(ValueError):
            calculate_all_indicators(empty_df)
        
        # Test with missing columns
        bad_df = pd.DataFrame({'close': [1, 2, 3]})
        with self.assertRaises(ValueError):
            calculate_all_indicators(bad_df)
        
        logger.info("Error handling test passed")


if __name__ == "__main__":
    unittest.main()