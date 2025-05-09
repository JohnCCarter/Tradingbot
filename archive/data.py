"""
Dataprocessing och indikatorberäkning för Tradingbot
"""
# Här placeras funktioner som process_realtime_data, calculate_indicators, detect_fvg etc.
import pandas as pd
import talib
import numpy as np

def calculate_indicators(
    data, ema_length, volume_multiplier, trading_start_hour, trading_end_hour
):
    try:
        required_columns = {"close", "high", "low", "volume"}
        if not required_columns.issubset(data.columns):
            raise ValueError(
                f"Data is missing required columns: {required_columns - set(data.columns)}"
            )
        for col in ["close", "high", "low", "volume"]:
            data[col] = data[col].astype(float)
        if data["close"].isnull().all():
            raise ValueError(
                "The 'close' column is empty or contains only null values. Cannot calculate EMA."
            )
        data["ema"] = talib.EMA(data["close"], timeperiod=ema_length)
        atr_period = min(14, len(data))
        high_low = data["high"] - data["low"]
        high_pc = (data["high"] - data["close"].shift()).abs()
        low_pc = (data["low"] - data["close"].shift()).abs()
        tr = pd.concat([high_low, high_pc, low_pc], axis=1).max(axis=1)
        data["atr"] = tr.rolling(window=atr_period, min_periods=1).mean()
        data["avg_volume"] = data["volume"].rolling(window=20, min_periods=1).mean()
        data["high_volume"] = data["volume"] > data["avg_volume"] * volume_multiplier
        data_len = len(data)
        rsi_period = min(14, data_len - 1) if data_len > 1 else 2
        try:
            data["rsi"] = talib.RSI(data["close"], timeperiod=rsi_period)
        except Exception:
            data["rsi"] = 0
        data["rsi"] = data["rsi"].fillna(0)
        adx_period = min(14, data_len - 1) if data_len > 1 else 2
        try:
            data["adx"] = talib.ADX(data["high"], data["low"], data["close"], timeperiod=adx_period)
        except Exception:
            data["adx"] = 0
        data["adx"] = data["adx"].fillna(0)
        data["hour"] = data["datetime"].dt.hour
        data["within_trading_hours"] = data["hour"].between(
            trading_start_hour, trading_end_hour
        )
        return data
    except Exception as e:
        import logging
        logging.error(f"Error calculating indicators: {e}")
        return None

def detect_fvg(data, lookback, bullish=True):
    if len(data) < 2:
        return np.nan, np.nan
    if bullish:
        return data["high"].iloc[-2], data["low"].iloc[-1]
    else:
        return data["high"].iloc[-1], data["low"].iloc[-2]
