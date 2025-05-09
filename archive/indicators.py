"""
Indikatorer och mönsterigenkänning för Tradingbot
"""
import pandas as pd
from functools import lru_cache
# TA-Lib krävs för tekniska indikatorer
try:
    import talib
except ImportError:
    talib = None

def calculate_indicators(df: pd.DataFrame, params: dict):
    """Beräknar tekniska indikatorer på en DataFrame."""
    if talib is None:
        raise ImportError("TA-Lib måste installeras för att använda indikatorer.")
    result = {}
    # Exempel: Lägg till fler indikatorer efter behov
    if 'ema' in params:
        result['ema'] = talib.EMA(df['close'], timeperiod=params['ema'])
    if 'rsi' in params:
        result['rsi'] = talib.RSI(df['close'], timeperiod=params['rsi'])
    return result

@lru_cache(maxsize=32)
def cached_calculate_indicators(df_hash, params_hash):
    # Denna wrapper används för cache på hash av df och params
    pass

def detect_fvg(df: pd.DataFrame):
    """Detekterar Fair Value Gap (FVG) i en DataFrame."""
    # Enkel FVG-detektion: returnera index där gap finns
    gaps = []
    for i in range(2, len(df)):
        if df['low'].iloc[i] > df['high'].iloc[i-2]:
            gaps.append(i)
    return gaps
