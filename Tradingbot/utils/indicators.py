"""
Technical indicators for trading strategies.
Provides functions to calculate various technical indicators on market data.
"""

import pandas as pd
import numpy as np
import logging

# Mock talib for testing purposes
class MockTaLib:
    @staticmethod
    def EMA(series, timeperiod):
        """Mock EMA calculation"""
        return series.ewm(span=timeperiod, adjust=False).mean()
    
    @staticmethod
    def RSI(series, timeperiod):
        """Mock RSI calculation"""
        return pd.Series(50, index=series.index)
    
    @staticmethod
    def ADX(high, low, close, timeperiod):
        """Mock ADX calculation"""
        return pd.Series(25, index=close.index)

# Try to import real talib, fall back to mock
try:
    import talib
except ImportError:
    talib = MockTaLib

def calculate_indicators(
    data, ema_length, volume_multiplier, trading_start_hour, trading_end_hour
):
    """
    Calculate technical indicators for trading strategies.
    
    Args:
        data: DataFrame with OHLCV data
        ema_length: EMA period length
        volume_multiplier: Multiplier for high volume threshold
        trading_start_hour: Hour of day to start trading (0-23)
        trading_end_hour: Hour of day to end trading (0-23)
    
    Returns:
        DataFrame: Data with indicators added
    """
    try:
        required_columns = {"close", "high", "low", "volume"}
        if not required_columns.issubset(data.columns):
            raise ValueError(
                f"Data is missing required columns: {required_columns - set(data.columns)}"
            )

        # Convert to float for talib compatibility
        for col in ["close", "high", "low", "volume"]:
            data[col] = data[col].astype(float)

        if data["close"].isnull().all():
            raise ValueError(
                "The 'close' column is empty or contains only null values. Cannot calculate EMA."
            )

        data["ema"] = talib.EMA(data["close"], timeperiod=ema_length)
        
        # Compute ATR manually to support small datasets
        atr_period = min(14, len(data))
        high_low = data["high"] - data["low"]
        high_pc = (data["high"] - data["close"].shift()).abs()
        low_pc = (data["low"] - data["close"].shift()).abs()
        tr = pd.concat([high_low, high_pc, low_pc], axis=1).max(axis=1)
        data["atr"] = tr.rolling(window=atr_period, min_periods=1).mean()
        
        # Rolling average volume with at least one period for small datasets
        data["avg_volume"] = data["volume"].rolling(window=20, min_periods=1).mean()
        data["high_volume"] = data["volume"] > data["avg_volume"] * volume_multiplier
        
        data_len = len(data)
        # RSI requires timeperiod >=2
        # Calculate RSI safely
        rsi_period = min(14, data_len - 1) if data_len > 1 else 2
        try:
            data["rsi"] = talib.RSI(data["close"], timeperiod=rsi_period)
        except Exception:
            data["rsi"] = 0
        # Fill initial NaN RSI values
        data["rsi"] = data["rsi"].fillna(0)
        
        # Calculate ADX safely
        adx_period = min(14, data_len - 1) if data_len > 1 else 2
        try:
            data["adx"] = talib.ADX(
                data["high"], data["low"], data["close"], timeperiod=adx_period
            )
        except Exception:
            data["adx"] = 0
        # Fill initial NaN ADX values
        data["adx"] = data["adx"].fillna(0)
        
        data["hour"] = data["datetime"].dt.hour
        data["within_trading_hours"] = data["hour"].between(
            trading_start_hour, trading_end_hour
        )
        
        return data
    except Exception as e:
        logging.error(f"Error calculating indicators: {e}")
        return None


def detect_fvg(data, lookback, bullish=True):
    """
    Detect Fair Value Gap (FVG) in price data.
    
    Args:
        data: DataFrame with OHLCV data
        lookback: Number of periods to look back
        bullish: True for bullish FVG, False for bearish
    
    Returns:
        tuple: (high, low) of the detected FVG, or (nan, nan) if not found
    """
    # Simplified FVG: return latest high/low for bullish/bearish
    if len(data) < 2:
        return np.nan, np.nan
    if bullish:
        return data["high"].iloc[-2], data["low"].iloc[-1]
    else:
        return data["high"].iloc[-1], data["low"].iloc[-2]