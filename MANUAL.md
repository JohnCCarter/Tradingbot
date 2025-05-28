# Tradingbot - User Manual

## Introduction

Welcome to Tradingbot! This manual will guide you through the features and functionality of the trading system, helping you maximize your trading experience.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Setting Up Trading Strategies](#setting-up-trading-strategies)
4. [Analyzing Performance](#analyzing-performance)
5. [Advanced Features](#advanced-features)
6. [Troubleshooting](#troubleshooting)

## Getting Started

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/JohnCCarter/Tradingbot.git
   cd Tradingbot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your API keys:
   - Create a `.env` file in the root directory
   - Add your exchange API keys (see `.env.example` for format)

### Starting the Bot

1. Start the API server:
   ```bash
   python api.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000/dashboard
   ```

## Dashboard Overview

The dashboard provides a complete view of your trading activities:

- **Order Form**: Place new trades with specified parameters
- **Account Balance**: View your current balance across all assets
- **Recent Orders**: Track your most recent trading activity
- **Price Chart**: Monitor price movements in real-time
- **Strategy Performance**: Analyze the effectiveness of your trading strategy

## Setting Up Trading Strategies

Tradingbot now supports multiple trading strategies that can be configured to match your preferences.

### Available Strategies

#### 1. Fair Value Gap (FVG) Strategy

The default strategy that identifies price inefficiencies through Fair Value Gaps.

**Configuration:**
```json
{
  "strategy_type": "fvg",
  "lookback": 5,
  "atr_multiplier": 1.5,
  "volume_multiplier": 1.5,
  "use_support_resistance": true
}
```

#### 2. MACD Strategy

Uses Moving Average Convergence Divergence for trend identification and signal generation.

**Configuration:**
```json
{
  "strategy_type": "macd",
  "fast_period": 12,
  "slow_period": 26,
  "signal_period": 9,
  "volume_filter": true
}
```

#### 3. Bollinger Bands Strategy

Uses Bollinger Bands for identifying overbought and oversold conditions.

**Configuration:**
```json
{
  "strategy_type": "bollinger",
  "bb_window": 20,
  "bb_std": 2.0,
  "rsi_filter": true,
  "rsi_upper": 70,
  "rsi_lower": 30
}
```

#### 4. Combined Strategy

Uses multiple strategies together with weighted signals for more robust trading decisions.

**Configuration:**
```json
{
  "strategy_type": "combined",
  "weights": [0.4, 0.3, 0.3],
  "macd": {
    "fast_period": 12,
    "slow_period": 26
  },
  "bollinger": {
    "bb_window": 20,
    "bb_std": 2.0
  },
  "fvg": {
    "lookback": 5
  }
}
```

### Setting Your Strategy

To use one of the strategies, update your `config.json` file with the desired strategy parameters. Example:

```json
{
  "EXCHANGE": "bitfinex",
  "SYMBOL": "tTESTBTC:TESTUSD",
  "TIMEFRAME": "35m",
  "STRATEGY_TYPE": "combined",
  "STRATEGY_CONFIG": {
    "weights": [0.4, 0.3, 0.3],
    "macd": {
      "fast_period": 12,
      "slow_period": 26,
      "signal_period": 9
    },
    "bollinger": {
      "bb_window": 20,
      "bb_std": 2.0
    },
    "fvg": {
      "lookback": 5
    }
  },
  "STOP_LOSS_PERCENT": 2,
  "TAKE_PROFIT_PERCENT": 2
}
```

## Analyzing Performance

Tradingbot provides comprehensive performance analysis tools to evaluate your trading strategy's effectiveness.

### Performance Metrics

- **Profit & Loss**: Overall profit or loss from trading
- **Win Rate**: Percentage of trades that were profitable
- **Risk-Reward Ratio**: Ratio between average profit and average loss
- **Maximum Consecutive Wins/Losses**: Longest streak of winning or losing trades
- **Trade Frequency**: Average number of trades per day
- **Symbol Performance**: Breakdown of performance by trading pair

### Performance Charts

- **Cumulative P&L**: Shows the growth of your trading account over time
- **Daily P&L**: Visualizes profit and loss on a daily basis
- **Performance by Symbol**: Doughnut chart showing relative performance of different trading pairs
- **Hourly Trading Activity**: Bar chart showing trading frequency by hour of day

### Exporting Data

You can export your performance data for further analysis:

1. Go to the Strategy Performance page
2. Set the desired filters (symbol, date range)
3. Click the "Export Data" button
4. A ZIP file containing CSV files with trades, pairs, and metrics will be downloaded

## Advanced Features

### Enhanced Indicators

Tradingbot now includes advanced technical indicators:

- **MACD**: Moving Average Convergence Divergence
- **Bollinger Bands**: Volatility-based bands around price
- **Support and Resistance**: Automatic detection of key price levels
- **Enhanced Volume Analysis**: Identifies volume surges and trends

### Backtesting

Test your strategies against historical data:

```bash
python tradingbot.py --backtest --strategy combined --start-date 2023-01-01 --end-date 2023-12-31
```

Results will be saved to `backtest_result.json` and can be visualized in the dashboard.

## Troubleshooting

### Common Issues

- **Connection Errors**: Make sure your API keys are correct and have appropriate permissions.
- **Missing Data**: Verify that the exchange supports the selected symbol and timeframe.
- **No Trading Signals**: Adjust your strategy parameters or try a different strategy.

### Error Logs

Check the log files for detailed error information:
- `tradingbot.log`: Main application log
- `order_status_log.txt`: Order execution log

### Getting Help

If you encounter any issues, please create an issue on the [GitHub repository](https://github.com/JohnCCarter/Tradingbot/issues).

---

Thank you for using Tradingbot! Happy trading!