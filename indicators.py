"""
Enhanced Trading Indicators Module

This module provides advanced technical analysis indicators and pattern detection
algorithms used by the TradingBot trading strategies.

Indicators included:
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- RSI (Relative Strength Index)
- ATR (Average True Range)
- Support and Resistance Detection
- Enhanced Volume Analysis
"""

import numpy as np
import pandas as pd
import logging

# Create a logger for this module
logger = logging.getLogger(__name__)

def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9):
    """
    Calculate Moving Average Convergence Divergence (MACD)
    
    Parameters:
    data (pandas.DataFrame): DataFrame with 'close' price column
    fast_period (int): Fast EMA period
    slow_period (int): Slow EMA period
    signal_period (int): Signal line period
    
    Returns:
    pandas.DataFrame: Input DataFrame with added MACD columns
    """
    try:
        # Make a copy to avoid modifying the original dataframe
        df = data.copy()
        
        # Calculate fast and slow EMAs
        df['ema_fast'] = df['close'].ewm(span=fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=slow_period, adjust=False).mean()
        
        # Calculate MACD line
        df['macd'] = df['ema_fast'] - df['ema_slow']
        
        # Calculate signal line
        df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
        
        # Calculate histogram
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        logger.debug(f"MACD calculated with fast={fast_period}, slow={slow_period}, signal={signal_period}")
        return df
    except Exception as e:
        logger.error(f"Error calculating MACD: {e}")
        # Add empty columns if calculation fails
        for col in ['ema_fast', 'ema_slow', 'macd', 'macd_signal', 'macd_hist']:
            data[col] = np.nan
        return data

def calculate_bollinger_bands(data, window=20, num_std=2):
    """
    Calculate Bollinger Bands
    
    Parameters:
    data (pandas.DataFrame): DataFrame with 'close' price column
    window (int): Rolling window size
    num_std (float): Number of standard deviations for bands
    
    Returns:
    pandas.DataFrame: Input DataFrame with added Bollinger Bands columns
    """
    try:
        # Make a copy to avoid modifying the original dataframe
        df = data.copy()
        
        # Calculate rolling mean and standard deviation
        df['bb_middle'] = df['close'].rolling(window=window).mean()
        rolling_std = df['close'].rolling(window=window).std()
        
        # Calculate upper and lower bands
        df['bb_upper'] = df['bb_middle'] + (rolling_std * num_std)
        df['bb_lower'] = df['bb_middle'] - (rolling_std * num_std)
        
        # Calculate bandwidth
        df['bb_bandwidth'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Calculate %B (position within bands)
        df['bb_percent_b'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        logger.debug(f"Bollinger Bands calculated with window={window}, std={num_std}")
        return df
    except Exception as e:
        logger.error(f"Error calculating Bollinger Bands: {e}")
        # Add empty columns if calculation fails
        for col in ['bb_middle', 'bb_upper', 'bb_lower', 'bb_bandwidth', 'bb_percent_b']:
            data[col] = np.nan
        return data

def detect_support_resistance(data, window=10, threshold=0.0015):
    """
    Detect support and resistance levels using local minima and maxima
    
    Parameters:
    data (pandas.DataFrame): DataFrame with 'high' and 'low' price columns
    window (int): Lookback window for identifying local extremes
    threshold (float): Threshold for price movement significance
    
    Returns:
    pandas.DataFrame: Input DataFrame with added support/resistance columns
    """
    try:
        df = data.copy()
        
        # Initialize columns
        df['is_support'] = False
        df['is_resistance'] = False
        df['support_level'] = np.nan
        df['resistance_level'] = np.nan
        
        # Required minimum data points
        if len(df) < window * 2 + 1:
            logger.warning("Not enough data points to detect support/resistance levels")
            return df
        
        # Function to identify local minima and maxima
        for i in range(window, len(df) - window):
            # Get window data
            low_window = df['low'].iloc[i-window:i+window+1]
            high_window = df['high'].iloc[i-window:i+window+1]
            
            # Check if center point is local minimum/maximum
            if df['low'].iloc[i] == min(low_window):
                # Verify significance
                if (df['low'].iloc[i-1] - df['low'].iloc[i]) / df['low'].iloc[i] > threshold:
                    df.at[df.index[i], 'is_support'] = True
                    df.at[df.index[i], 'support_level'] = df['low'].iloc[i]
            
            if df['high'].iloc[i] == max(high_window):
                # Verify significance
                if (df['high'].iloc[i] - df['high'].iloc[i-1]) / df['high'].iloc[i] > threshold:
                    df.at[df.index[i], 'is_resistance'] = True
                    df.at[df.index[i], 'resistance_level'] = df['high'].iloc[i]
        
        logger.debug(f"Support/resistance detection completed with window={window}")
        return df
    except Exception as e:
        logger.error(f"Error detecting support/resistance: {e}")
        # Add empty columns if calculation fails
        for col in ['is_support', 'is_resistance', 'support_level', 'resistance_level']:
            if col not in data.columns:
                data[col] = np.nan if col.endswith('level') else False
        return data

def analyze_volume(data, short_window=5, long_window=20, volume_surge_threshold=2.0):
    """
    Perform enhanced volume analysis
    
    Parameters:
    data (pandas.DataFrame): DataFrame with 'volume' column
    short_window (int): Short-term rolling window for volume
    long_window (int): Long-term rolling window for volume
    volume_surge_threshold (float): Threshold to identify volume surges
    
    Returns:
    pandas.DataFrame: Input DataFrame with added volume analysis columns
    """
    try:
        df = data.copy()
        
        # Calculate volume moving averages
        df['vol_sma_short'] = df['volume'].rolling(window=short_window).mean()
        df['vol_sma_long'] = df['volume'].rolling(window=long_window).mean()
        
        # Volume ratio (short-term to long-term)
        df['vol_ratio'] = df['vol_sma_short'] / df['vol_sma_long']
        
        # Identify volume surges
        df['vol_surge'] = df['volume'] > (df['vol_sma_long'] * volume_surge_threshold)
        
        # Volume trend (increasing or decreasing)
        df['vol_trend'] = df['vol_ratio'] > 1.0
        
        logger.debug(f"Volume analysis completed with windows={short_window},{long_window}")
        return df
    except Exception as e:
        logger.error(f"Error analyzing volume: {e}")
        # Add empty columns if calculation fails
        for col in ['vol_sma_short', 'vol_sma_long', 'vol_ratio', 'vol_surge', 'vol_trend']:
            data[col] = np.nan if not col.endswith(('surge', 'trend')) else False
        return data

def calculate_all_indicators(data, 
                            ema_length=20, 
                            volume_multiplier=1.5, 
                            trading_start_hour=0, 
                            trading_end_hour=23,
                            macd_fast=12,
                            macd_slow=26,
                            macd_signal=9,
                            bb_window=20,
                            bb_std=2.0):
    """
    Calculate all indicators in one function call
    
    Parameters:
    data (pandas.DataFrame): DataFrame with OHLCV data
    ema_length (int): EMA period for standard indicators
    volume_multiplier (float): Volume threshold multiplier
    trading_start_hour (int): Trading session start hour
    trading_end_hour (int): Trading session end hour
    macd_* (int): MACD parameters
    bb_* (float): Bollinger Bands parameters
    
    Returns:
    pandas.DataFrame: DataFrame with all indicators added
    """
    try:
        required_columns = {"close", "high", "low", "volume", "datetime"}
        if not required_columns.issubset(data.columns):
            missing = required_columns - set(data.columns)
            raise ValueError(f"Data is missing required columns: {missing}")
        
        # Make a copy to avoid modifying the original dataframe
        df = data.copy()
        
        # Ensure numeric types
        for col in ["close", "high", "low", "volume"]:
            df[col] = df[col].astype(float)
        
        # Basic indicators (similar to existing calculate_indicators)
        df['ema'] = df['close'].ewm(span=ema_length, adjust=False).mean()
        
        # Compute ATR
        atr_period = min(14, len(df) - 1) if len(df) > 1 else 2
        high_low = df["high"] - df["low"]
        high_pc = (df["high"] - df["close"].shift()).abs()
        low_pc = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_pc, low_pc], axis=1).max(axis=1)
        df["atr"] = tr.rolling(window=atr_period, min_periods=1).mean()
        
        # Volume indicators
        df["avg_volume"] = df["volume"].rolling(window=20, min_periods=1).mean()
        df["high_volume"] = df["volume"] > df["avg_volume"] * volume_multiplier
        
        # RSI calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi'] = df['rsi'].fillna(50)  # Fill NaN values with neutral RSI
        
        # Trading hours
        df["hour"] = df["datetime"].dt.hour
        df["within_trading_hours"] = df["hour"].between(trading_start_hour, trading_end_hour)
        
        # Enhanced indicators
        df = calculate_macd(df, macd_fast, macd_slow, macd_signal)
        df = calculate_bollinger_bands(df, bb_window, bb_std)
        df = analyze_volume(df, 5, 20, 2.0)
        df = detect_support_resistance(df, 10, 0.0015)
        
        logger.info("All indicators calculated successfully")
        return df
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return None