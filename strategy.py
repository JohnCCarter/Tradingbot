"""
Enhanced Trading Strategies Module

This module provides various trading strategies for the TradingBot system.
Each strategy implements a common interface for easy integration.
"""

import numpy as np
import pandas as pd
import logging
from indicators import calculate_all_indicators

# Create a logger for this module
logger = logging.getLogger(__name__)

class StrategyBase:
    """Base class for all trading strategies"""
    
    def __init__(self, symbol, config=None):
        """
        Initialize the strategy with a symbol and configuration
        
        Parameters:
        symbol (str): Trading symbol
        config (dict): Strategy configuration parameters
        """
        self.symbol = symbol
        self.config = config or {}
        self.name = "Base Strategy"
        logger.info(f"Initialized {self.name} for {symbol}")
    
    def prepare_data(self, data):
        """
        Prepare and augment data with required indicators
        
        Parameters:
        data (pandas.DataFrame): Raw price data
        
        Returns:
        pandas.DataFrame: Processed data with indicators
        """
        return data
    
    def analyze(self, data):
        """
        Analyze the data and generate trading signals
        
        Parameters:
        data (pandas.DataFrame): Processed price data with indicators
        
        Returns:
        pandas.DataFrame: Data with added signal column
        """
        # Default implementation - no signals
        df = data.copy()
        df['signal'] = 0
        return df
    
    def get_signals(self, data):
        """
        Get trading signals from the data
        
        Parameters:
        data (pandas.DataFrame): Raw price data
        
        Returns:
        pandas.DataFrame: Data with signals
        """
        prepared_data = self.prepare_data(data)
        if prepared_data is None:
            logger.error(f"{self.name}: Failed to prepare data")
            return None
        
        signals = self.analyze(prepared_data)
        
        # Log signal statistics
        if 'signal' in signals.columns:
            buy_signals = (signals['signal'] > 0).sum()
            sell_signals = (signals['signal'] < 0).sum()
            logger.info(f"{self.name}: Generated {buy_signals} buy and {sell_signals} sell signals")
        
        return signals


class MACDStrategy(StrategyBase):
    """Trading strategy based on MACD crossovers"""
    
    def __init__(self, symbol, config=None):
        """
        Initialize MACD Strategy
        
        Parameters:
        symbol (str): Trading symbol
        config (dict): Strategy configuration with keys:
            - fast_period: Fast EMA period
            - slow_period: Slow EMA period
            - signal_period: Signal line period
            - volume_filter: Whether to use volume filter
        """
        config = config or {}
        self.fast_period = config.get('fast_period', 12)
        self.slow_period = config.get('slow_period', 26)
        self.signal_period = config.get('signal_period', 9)
        self.volume_filter = config.get('volume_filter', True)
        super().__init__(symbol, config)
        self.name = "MACD Strategy"
    
    def prepare_data(self, data):
        """Add MACD indicators to the data"""
        try:
            # Calculate all indicators including MACD
            return calculate_all_indicators(
                data, 
                macd_fast=self.fast_period,
                macd_slow=self.slow_period,
                macd_signal=self.signal_period
            )
        except Exception as e:
            logger.error(f"Error preparing data for MACD strategy: {e}")
            return None
    
    def analyze(self, data):
        """Generate signals based on MACD crossover"""
        df = data.copy()
        
        # Initialize signal column
        df['signal'] = 0
        
        # No signals if not enough data
        if len(df) < self.slow_period + self.signal_period:
            return df
        
        # MACD line crosses above signal line = buy signal
        df.loc[(df['macd'] > df['macd_signal']) & 
               (df['macd'].shift() <= df['macd_signal'].shift()), 'signal'] = 1
        
        # MACD line crosses below signal line = sell signal
        df.loc[(df['macd'] < df['macd_signal']) & 
               (df['macd'].shift() >= df['macd_signal'].shift()), 'signal'] = -1
        
        # Additional filters
        if self.volume_filter:
            # Only consider signals with high volume
            df.loc[~df['high_volume'], 'signal'] = 0
        
        # Only trade within trading hours
        df.loc[~df['within_trading_hours'], 'signal'] = 0
        
        return df


class BollingerBandsStrategy(StrategyBase):
    """Trading strategy based on Bollinger Bands"""
    
    def __init__(self, symbol, config=None):
        """
        Initialize Bollinger Bands Strategy
        
        Parameters:
        symbol (str): Trading symbol
        config (dict): Strategy configuration with keys:
            - bb_window: Bollinger Bands period
            - bb_std: Number of standard deviations
            - rsi_filter: Whether to use RSI filter
            - rsi_upper: RSI upper threshold
            - rsi_lower: RSI lower threshold
        """
        config = config or {}
        self.bb_window = config.get('bb_window', 20)
        self.bb_std = config.get('bb_std', 2.0)
        self.rsi_filter = config.get('rsi_filter', True)
        self.rsi_upper = config.get('rsi_upper', 70)
        self.rsi_lower = config.get('rsi_lower', 30)
        super().__init__(symbol, config)
        self.name = "Bollinger Bands Strategy"
    
    def prepare_data(self, data):
        """Add Bollinger Bands indicators to the data"""
        try:
            return calculate_all_indicators(
                data, 
                bb_window=self.bb_window,
                bb_std=self.bb_std
            )
        except Exception as e:
            logger.error(f"Error preparing data for Bollinger Bands strategy: {e}")
            return None
    
    def analyze(self, data):
        """Generate signals based on Bollinger Bands breakouts and mean reversion"""
        df = data.copy()
        
        # Initialize signal column
        df['signal'] = 0
        
        # No signals if not enough data
        if len(df) < self.bb_window:
            return df
        
        # Mean reversion strategy
        
        # Price closes below lower band = buy signal
        df.loc[df['close'] < df['bb_lower'], 'signal'] = 1
        
        # Price closes above upper band = sell signal
        df.loc[df['close'] > df['bb_upper'], 'signal'] = -1
        
        # Apply RSI filter if enabled
        if self.rsi_filter:
            # Confirm buy only if RSI is oversold
            df.loc[(df['signal'] == 1) & (df['rsi'] > self.rsi_lower), 'signal'] = 0
            
            # Confirm sell only if RSI is overbought
            df.loc[(df['signal'] == -1) & (df['rsi'] < self.rsi_upper), 'signal'] = 0
        
        # Only trade within trading hours
        df.loc[~df['within_trading_hours'], 'signal'] = 0
        
        return df


class EnhancedFVGStrategy(StrategyBase):
    """Enhanced Fair Value Gap (FVG) Strategy with additional indicators"""
    
    def __init__(self, symbol, config=None):
        """
        Initialize Enhanced FVG Strategy
        
        Parameters:
        symbol (str): Trading symbol
        config (dict): Strategy configuration with keys:
            - lookback: Lookback period for FVG detection
            - atr_multiplier: ATR filter multiplier
            - volume_multiplier: Volume filter multiplier
            - use_support_resistance: Whether to use support/resistance
        """
        config = config or {}
        self.lookback = config.get('lookback', 5)
        self.atr_multiplier = config.get('atr_multiplier', 1.5)
        self.volume_multiplier = config.get('volume_multiplier', 1.5)
        self.use_support_resistance = config.get('use_support_resistance', True)
        super().__init__(symbol, config)
        self.name = "Enhanced FVG Strategy"
    
    def detect_fvg(self, data, bullish):
        """Detect Fair Value Gap (FVG)"""
        # Simplified FVG detection
        if len(data) < 2:
            return np.nan, np.nan
        if bullish:
            return data["high"].iloc[-2], data["low"].iloc[-1]
        else:
            return data["high"].iloc[-1], data["low"].iloc[-2]
    
    def prepare_data(self, data):
        """Add required indicators for FVG strategy"""
        try:
            return calculate_all_indicators(
                data, 
                volume_multiplier=self.volume_multiplier
            )
        except Exception as e:
            logger.error(f"Error preparing data for FVG strategy: {e}")
            return None
    
    def analyze(self, data):
        """Generate signals based on FVG and additional filters"""
        df = data.copy()
        
        # Initialize signal column
        df['signal'] = 0
        
        if len(df) < 2:
            return df
        
        # Calculate mean ATR for filtering
        mean_atr = df['atr'].mean()
        
        # Process each candle for signals
        for idx in range(1, len(df)):
            # Skip if outside trading hours or ATR too low
            if (not df.iloc[idx]['within_trading_hours'] or 
                df.iloc[idx]['atr'] <= self.atr_multiplier * mean_atr):
                continue
            
            # Detect bullish and bearish FVGs
            bull_high, bull_low = self.detect_fvg(df.iloc[:idx+1], bullish=True)
            bear_high, bear_low = self.detect_fvg(df.iloc[:idx+1], bullish=False)
            
            current_price = df.iloc[idx]['close']
            current_ema = df.iloc[idx]['ema']
            high_volume = df.iloc[idx]['high_volume']
            
            # Long condition
            long_condition = (
                not np.isnan(bull_high) and
                current_price < bull_low and
                current_price > current_ema and
                high_volume
            )
            
            # Short condition
            short_condition = (
                not np.isnan(bear_high) and
                current_price > bear_high and
                current_price < current_ema and
                high_volume
            )
            
            # Enhanced conditions with support/resistance
            if self.use_support_resistance:
                # Check if price is near support or resistance
                if df.iloc[idx]['is_support']:
                    # Price near support strengthens buy signal
                    if long_condition:
                        df.at[df.index[idx], 'signal'] = 1
                
                elif df.iloc[idx]['is_resistance']:
                    # Price near resistance strengthens sell signal
                    if short_condition:
                        df.at[df.index[idx], 'signal'] = -1
            else:
                # Standard FVG signals
                if long_condition:
                    df.at[df.index[idx], 'signal'] = 1
                elif short_condition:
                    df.at[df.index[idx], 'signal'] = -1
        
        return df


class CombinedStrategy(StrategyBase):
    """Combined strategy that uses signals from multiple sub-strategies"""
    
    def __init__(self, symbol, config=None):
        """
        Initialize Combined Strategy
        
        Parameters:
        symbol (str): Trading symbol
        config (dict): Strategy configuration with keys for sub-strategies
        """
        super().__init__(symbol, config)
        self.name = "Combined Strategy"
        
        # Create sub-strategies
        self.strategies = [
            MACDStrategy(symbol, config.get('macd', {})),
            BollingerBandsStrategy(symbol, config.get('bollinger', {})),
            EnhancedFVGStrategy(symbol, config.get('fvg', {}))
        ]
        
        # Weights for each strategy (must sum to 1)
        self.weights = config.get('weights', [0.4, 0.3, 0.3])
        
        # Ensure weights sum to 1
        if len(self.weights) != len(self.strategies):
            self.weights = [1.0 / len(self.strategies)] * len(self.strategies)
        elif sum(self.weights) != 1.0:
            self.weights = [w / sum(self.weights) for w in self.weights]
    
    def prepare_data(self, data):
        """Prepare data using all required indicators"""
        try:
            # Calculate all indicators at once
            return calculate_all_indicators(data)
        except Exception as e:
            logger.error(f"Error preparing data for combined strategy: {e}")
            return None
    
    def analyze(self, data):
        """Generate signals by combining sub-strategy signals"""
        if data is None or len(data) < 20:
            logger.warning("Insufficient data for combined strategy analysis")
            return data
            
        # Get signals from all strategies
        signals = []
        for i, strategy in enumerate(self.strategies):
            logger.debug(f"Getting signals from {strategy.name}")
            result = strategy.analyze(data)
            if result is not None and 'signal' in result.columns:
                signals.append(result['signal'] * self.weights[i])
            else:
                signals.append(pd.Series(0, index=data.index))
        
        # Combine signals
        df = data.copy()
        df['signal'] = sum(signals)
        
        # Discretize signals to -1, 0, 1
        df['signal'] = np.where(df['signal'] > 0.3, 1, np.where(df['signal'] < -0.3, -1, 0))
        
        # Log the number of signals
        buy_count = (df['signal'] == 1).sum()
        sell_count = (df['signal'] == -1).sum()
        logger.info(f"Combined strategy generated {buy_count} buy signals and {sell_count} sell signals")
        
        return df
    
    def get_signals(self, data):
        """Override to show statistics from each sub-strategy"""
        logger.info("Analyzing with Combined Strategy")
        
        # Prepare data once
        prepared_data = self.prepare_data(data)
        if prepared_data is None:
            return None
            
        # Log sub-strategy signals for analysis
        for strategy in self.strategies:
            result = strategy.analyze(prepared_data)
            if result is not None and 'signal' in result.columns:
                buy_count = (result['signal'] == 1).sum()
                sell_count = (result['signal'] == -1).sum()
                logger.info(f"  - {strategy.name}: {buy_count} buy, {sell_count} sell signals")
        
        # Get combined signals
        return self.analyze(prepared_data)


def create_strategy(strategy_type, symbol, config=None):
    """
    Factory function to create a strategy instance
    
    Parameters:
    strategy_type (str): Type of strategy to create
    symbol (str): Trading symbol
    config (dict): Strategy configuration
    
    Returns:
    StrategyBase: Strategy instance
    """
    strategies = {
        'macd': MACDStrategy,
        'bollinger': BollingerBandsStrategy, 
        'fvg': EnhancedFVGStrategy,
        'combined': CombinedStrategy
    }
    
    if strategy_type.lower() not in strategies:
        logger.warning(f"Unknown strategy type: {strategy_type}. Using combined strategy.")
        return CombinedStrategy(symbol, config)
    
    return strategies[strategy_type.lower()](symbol, config)