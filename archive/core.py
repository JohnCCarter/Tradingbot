"""
Kärnklasser för Tradingbot: TradingBot och TradingStrategy
"""
import logging
from typing import Optional, Any, Dict
from data import calculate_indicators, detect_fvg
from utils import log, ensure_paper_trading_symbol
from exchange import place_order
import numpy as np

class TradingStrategy:
    """
    Encapsulates a trading strategy with indicator calculation and trade execution logic.
    """
    def __init__(
        self,
        symbol,
        ema_length,
        atr_multiplier,
        volume_multiplier,
        start_hour,
        end_hour,
        max_trades,
        max_loss,
        stop_loss_pct,
        take_profit_pct,
        lookback=100,
    ):
        self.symbol = symbol
        self.ema_length = ema_length
        self.atr_multiplier = atr_multiplier
        self.volume_multiplier = volume_multiplier
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.max_trades = max_trades
        self.max_loss = max_loss
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.lookback = lookback

    def calculate_indicators(self, data):
        return calculate_indicators(
            data,
            self.ema_length,
            self.volume_multiplier,
            self.start_hour,
            self.end_hour,
        )

    def detect_fvg(self, data, bullish):
        return detect_fvg(data, self.lookback, bullish)

    def execute(self, data):
        if data is None or data.empty:
            logging.error(
                "Data is invalid or empty. Trading strategy cannot be executed."
            )
            return
        trade_count = 0
        daily_loss = 0
        mean_atr = data["atr"].mean() if "atr" in data.columns else 0
        for idx, row in data.iterrows():
            if daily_loss < -self.max_loss or trade_count >= self.max_trades:
                break
            if "atr" in row and row["atr"] <= self.atr_multiplier * mean_atr:
                continue
            bull_high, bull_low = self.detect_fvg(data.iloc[: idx + 1], True)
            bear_high, bear_low = self.detect_fvg(data.iloc[: idx + 1], False)
            long_cond = (
                not np.isnan(bull_high)
                and row["close"] < bull_low
                and row["close"] > row["ema"]
                and row["high_volume"]
                and row["within_trading_hours"]
            )
            short_cond = (
                not np.isnan(bear_high)
                and row["close"] > bear_high
                and row["close"] < row["ema"]
                and row["high_volume"]
                and row["within_trading_hours"]
            )
            if long_cond:
                trade_count += 1
                sl = row["close"] * (1 - self.stop_loss_pct / 100)
                tp = row["close"] * (1 + self.take_profit_pct / 100)
                place_order("buy", self.symbol, 0.001, row["close"], sl, tp)
            if short_cond:
                trade_count += 1
                sl = row["close"] * (1 + self.stop_loss_pct / 100)
                tp = row["close"] * (1 - self.take_profit_pct / 100)
                place_order("sell", self.symbol, 0.001, row["close"], sl, tp)

class TradingBot:
    """
    Main TradingBot class for orchestrating trading operations, status, and lifecycle.
    """
    def __init__(self, config_file='config.json'):
        # Load config and initialize state here if needed
        self.config_file = config_file
        self.running = False
        self.status = "initialized"
        # ... add more initialization as needed ...

    def start(self):
        self.running = True
        self.status = "running"
        # ... start trading loop or background tasks ...

    def stop(self):
        self.running = False
        self.status = "stopped"
        # ... stop trading loop or background tasks ...

    def get_status(self):
        return self.status

    def get_balance(self):
        # Implement balance fetching logic
        pass

    def get_ticker(self, symbol=None):
        # Implement ticker fetching logic
        pass
