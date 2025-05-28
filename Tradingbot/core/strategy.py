"""
Trading strategies for Tradingbot.
Contains the logic for executing trading strategies.
"""

import numpy as np
import logging
from Tradingbot.utils.indicators import detect_fvg
from Tradingbot.core.exchange import place_order


class TradingStrategy:
    """Trading strategy implementation"""
    
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

    def detect_fvg(self, data, bullish):
        """Detect Fair Value Gap"""
        return detect_fvg(data, self.lookback, bullish)

    def execute(self, data, exchange, logger):
        """
        Execute trading strategy on the given data
        
        Args:
            data: DataFrame with price data and indicators
            exchange: Exchange instance
            logger: Logger instance
        
        Returns:
            int: Number of trades executed
        """
        if data is None or data.empty:
            logging.error(
                "Data is invalid or empty. Trading strategy cannot be executed."
            )
            return 0
            
        # Initialize counters
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
                place_order(exchange, logger, "buy", self.symbol, 0.001, row["close"], sl, tp)
                
            if short_cond:
                trade_count += 1
                sl = row["close"] * (1 + self.stop_loss_pct / 100)
                tp = row["close"] * (1 - self.take_profit_pct / 100)
                place_order(exchange, logger, "sell", self.symbol, 0.001, row["close"], sl, tp)
                
        return trade_count


def execute_trading_strategy(
    data, max_trades_per_day, max_daily_loss, atr_multiplier, symbol,
    exchange, logger, lookback=100
):
    """
    Execute a trading strategy on the given data
    
    Args:
        data: DataFrame with price data and indicators
        max_trades_per_day: Maximum trades per day
        max_daily_loss: Maximum daily loss
        atr_multiplier: ATR multiplier for trade filtering
        symbol: Trading symbol
        exchange: Exchange instance
        logger: Logger instance
        lookback: Number of periods to look back for patterns
        
    Returns:
        int: Number of trades executed
    """
    try:
        if data is None or data.empty:
            logging.error(
                "Data is invalid or empty. Trading strategy cannot be executed."
            )
            return 0
            
        if "ema" not in data.columns or data["ema"].count() == 0:
            logging.critical(
                "EMA indicator is missing or not calculated correctly. Exiting strategy."
            )
            return 0
            
        if "high_volume" not in data.columns or data["high_volume"].count() == 0:
            logging.critical(
                "High volume indicator is missing or not calculated correctly. Exiting strategy."
            )
            return 0
            
        if "atr" not in data.columns or data["atr"].count() == 0:
            logging.critical(
                "ATR indicator is missing or not calculated correctly. Exiting strategy."
            )
            return 0
            
        mean_atr = data["atr"].mean()
        trade_count = 0
        daily_loss = 0
        
        for index, row in data.iterrows():
            if daily_loss < -max_daily_loss:
                logging.debug(
                    f"Stopping: daily_loss ({daily_loss}) < -max_daily_loss ({-max_daily_loss})"
                )
                break
                
            # ATR condition: only buy/sell if ATR is high enough
            if row["atr"] <= atr_multiplier * mean_atr:
                logging.debug(
                    f"Skipped row {index}: ATR {row['atr']} <= {atr_multiplier} * mean_ATR {mean_atr}"
                )
                continue
                
            bull_fvg_high, bull_fvg_low = detect_fvg(
                data.iloc[: index + 1], lookback, bullish=True
            )
            bear_fvg_high, bear_fvg_low = detect_fvg(
                data.iloc[: index + 1], lookback, bullish=False
            )
            
            long_condition = (
                not np.isnan(bull_fvg_high)
                and row["close"] < bull_fvg_low
                and row["close"] > row["ema"]
                and row["high_volume"]
                and row["within_trading_hours"]
            )
            
            short_condition = (
                not np.isnan(bear_fvg_high)
                and row["close"] > bear_fvg_high
                and row["close"] < row["ema"]
                and row["high_volume"]
                and row["within_trading_hours"]
            )
            
            logging.debug(
                f"Row {index}: ATR={row['atr']:.2f} vs {atr_multiplier}*{mean_atr:.2f}={atr_multiplier*mean_atr:.2f}"
            )
            
            # If conditions are met, place orders
            if long_condition and trade_count < max_trades_per_day:
                logging.info(f"Placing BUY order at row {index}")
                trade_count += 1
                place_order(exchange, logger, "buy", symbol, 0.001, row["close"])
                
            if short_condition and trade_count < max_trades_per_day:
                logging.info(f"Placing SELL order at row {index}")
                trade_count += 1
                place_order(exchange, logger, "sell", symbol, 0.001, row["close"])
            
        return trade_count
        
    except Exception as e:
        logging.error(f"Error executing trading strategy: {e}")
        return 0


def run_backtest(
    symbol,
    timeframe,
    limit,
    ema_length,
    volume_multiplier,
    trading_start_hour,
    trading_end_hour,
    max_trades_per_day,
    max_daily_loss,
    atr_multiplier,
    exchange,
    data_fetcher,
    indicator_calculator,
    lookback=100,
    print_orders=False,
    save_to_file=None,
):
    """
    Run backtest on historical data
    
    Args:
        symbol: Trading symbol
        timeframe: Timeframe ('1m', '5m', '1h', etc)
        limit: Maximum number of candles to fetch
        ema_length: EMA period length
        volume_multiplier: Multiplier for high volume threshold
        trading_start_hour: Hour of day to start trading (0-23)
        trading_end_hour: Hour of day to end trading (0-23)
        max_trades_per_day: Maximum trades per day
        max_daily_loss: Maximum daily loss
        atr_multiplier: ATR multiplier for trade filtering
        exchange: Exchange instance
        data_fetcher: Function to fetch market data
        indicator_calculator: Function to calculate indicators
        lookback: Number of periods to look back for patterns
        print_orders: Whether to print orders
        save_to_file: File to save results to
        
    Returns:
        list: List of trades
    """
    # Fetch historical data
    data = data_fetcher(exchange, symbol, timeframe, limit)
    if data is None or data.empty:
        logging.error("No historical data could be fetched for backtest.")
        return []
        
    # Calculate indicators
    data = indicator_calculator(
        data, ema_length, volume_multiplier, trading_start_hour, trading_end_hour
    )
    if data is None:
        logging.error("Could not calculate indicators for backtest.")
        return []
        
    trades = []
    trade_count = 0
    daily_loss = 0
    mean_atr = data["atr"].mean() if "atr" in data.columns else 0
    
    for index, row in data.iterrows():
        if daily_loss < -max_daily_loss:
            break
            
        if "atr" in row and row["atr"] <= atr_multiplier * mean_atr:
            continue
            
        bull_fvg_high, bull_fvg_low = detect_fvg(
            data.iloc[: index + 1], lookback, bullish=True
        )
        bear_fvg_high, bear_fvg_low = detect_fvg(
            data.iloc[: index + 1], lookback, bullish=False
        )
        
        long_condition = (
            not np.isnan(bull_fvg_high)
            and row["close"] < bull_fvg_low
            and row["close"] > row["ema"]
            and row["high_volume"]
            and row["within_trading_hours"]
        )
        
        short_condition = (
            not np.isnan(bear_fvg_high)
            and row["close"] > bear_fvg_high
            and row["close"] < row["ema"]
            and row["high_volume"]
            and row["within_trading_hours"]
        )
        
        if long_condition and trade_count < max_trades_per_day:
            trade_count += 1
            trade = {
                "type": "buy",
                "symbol": symbol,
                "price": row["close"],
                "timestamp": row.name,
                "datetime": row["datetime"],
            }
            trades.append(trade)
            
            if print_orders:
                print(f"\nBacktest: BUY at {row['close']} - {row['datetime']}")
                
        if short_condition and trade_count < max_trades_per_day:
            trade_count += 1
            trade = {
                "type": "sell",
                "symbol": symbol,
                "price": row["close"],
                "timestamp": row.name,
                "datetime": row["datetime"],
            }
            trades.append(trade)
            
            if print_orders:
                print(f"\nBacktest: SELL at {row['close']} - {row['datetime']}")
    
    # Save trades to file if requested
    if save_to_file and trades:
        import json
        
        try:
            with open(save_to_file, "w") as f:
                json.dump(trades, f, indent=2, default=str)
        except Exception as e:
            logging.error(f"Error saving trades to file {save_to_file}: {e}")
    
    return trades