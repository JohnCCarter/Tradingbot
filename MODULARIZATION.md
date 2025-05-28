# Tradingbot Modularization Guide

This document explains the modular structure of the Tradingbot codebase and how to use it effectively.

## Overview

The Tradingbot codebase has been restructured into a modular, organized package structure to improve:

- **Maintainability**: Smaller, focused files are easier to understand and modify
- **Testability**: Components can be tested in isolation
- **Extensibility**: New features can be added without modifying existing components
- **Reusability**: Components can be reused in different contexts

## Package Structure

The codebase is now organized into the following structure:

```
Tradingbot/                # Main package
├── __init__.py           # Package exports
├── api/                  # API components
│   ├── __init__.py
│   ├── app.py            # Main Flask app setup
│   └── routes/           # Route handlers
│       ├── __init__.py
│       ├── bot_routes.py         # Bot control endpoints
│       ├── data_routes.py        # Market data endpoints
│       ├── order_routes.py       # Order management endpoints
│       ├── dashboard_routes.py   # Dashboard endpoints
│       └── performance_routes.py # Performance analysis endpoints
├── core/                 # Core bot functionality
│   ├── __init__.py
│   ├── bot.py            # TradingBot class
│   ├── config.py         # Configuration handling
│   ├── exchange.py       # Exchange interactions
│   └── strategy.py       # Trading strategies
├── utils/                # Utility functions
│   ├── __init__.py
│   ├── indicators.py     # Technical indicators
│   └── logging.py        # Structured logging
└── data/                 # Data handling
    ├── __init__.py
    └── market_data.py    # Market data fetching and processing
```

## Key Components

### Core Components

- **bot.py**: Contains the `TradingBot` class, which is the main entry point for trading operations. It handles bot initialization, trading strategies, and lifecycle management.
- **strategy.py**: Contains trading strategy implementations, including the `TradingStrategy` class and strategy execution functions.
- **exchange.py**: Provides functions for interacting with cryptocurrency exchanges, including placing orders and fetching balance information.
- **config.py**: Handles configuration loading, validation, and providing defaults.

### Data Components

- **market_data.py**: Functions for fetching and processing market data from exchanges, both historical and real-time.

### Utility Components

- **indicators.py**: Technical indicator calculations used by trading strategies.
- **logging.py**: Enhanced logging functionality with structured and colorized output.

### API Components

- **app.py**: Sets up the Flask application and registers routes.
- **routes/**: Contains route handlers organized by functionality:
  - **bot_routes.py**: Endpoints for controlling the trading bot (start/stop/status).
  - **data_routes.py**: Endpoints for accessing market data.
  - **order_routes.py**: Endpoints for managing orders.
  - **dashboard_routes.py**: Endpoints for the web dashboard.
  - **performance_routes.py**: Endpoints for strategy performance analysis.

## Entry Points

The codebase provides two main entry points:

1. **tradingbot_new.py**: Main script for running the trading bot.
2. **api_new.py**: Main script for running the API server.

## Backwards Compatibility

For backwards compatibility with existing code and tests, the following are provided:

- **tradingbot_compat.py**: A compatibility layer that imports from the new modules but exposes the same interface as the original `tradingbot.py`.

## Using the Modules

### Running the Trading Bot

```python
from Tradingbot.core.bot import TradingBot
from Tradingbot.core.config import load_config
from Tradingbot.utils.logging import setup_logging

# Set up logging
logger, structured_logger = setup_logging()

# Load configuration
config = load_config("config.json")

# Create and run the bot
bot = TradingBot("config.json")
bot.start()
```

### Using Trading Strategies

```python
from Tradingbot.core.strategy import TradingStrategy
from Tradingbot.data.market_data import fetch_market_data
from Tradingbot.utils.indicators import calculate_indicators

# Fetch market data
data = fetch_market_data(exchange, "BTC/USD", "1h", 100)

# Calculate indicators
data = calculate_indicators(data, 14, 1.2, 0, 23)

# Create strategy
strategy = TradingStrategy(
    symbol="BTC/USD",
    ema_length=14,
    atr_multiplier=1.5,
    volume_multiplier=1.2,
    start_hour=0,
    end_hour=23,
    max_trades=10,
    max_loss=100,
    stop_loss_pct=2,
    take_profit_pct=4
)

# Execute strategy
trade_count = strategy.execute(data, exchange, structured_logger)
```

### Working with the API

```python
from Tradingbot.api.app import create_app, run_app

# Create Flask app with all routes registered
app = create_app()

# Run the app
run_app(host="0.0.0.0", port=5000)
```

## Testing

The modular structure makes it easy to test individual components:

```python
# Test indicators
from Tradingbot.utils.indicators import calculate_indicators
import pandas as pd

def test_calculate_indicators():
    # Create sample data
    df = pd.DataFrame({
        "open": [1, 2, 3],
        "high": [2, 3, 4],
        "low": [0.5, 1.5, 2.5],
        "close": [1.5, 2.5, 3.5],
        "volume": [10, 20, 30],
        "datetime": pd.date_range("2021-01-01", periods=3)
    })
    
    # Calculate indicators
    result = calculate_indicators(df, 2, 1.2, 0, 23)
    
    # Assert indicators were calculated correctly
    assert "ema" in result.columns
    assert "high_volume" in result.columns
```

## Extending the Codebase

### Adding a New Strategy

1. Create a new class in `Tradingbot/core/strategy.py`:

```python
class MyNewStrategy(TradingStrategy):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Add custom parameters
        
    def execute(self, data, exchange, logger):
        # Custom strategy logic
        return trade_count
```

2. Import and use it:

```python
from Tradingbot.core.strategy import MyNewStrategy

strategy = MyNewStrategy(symbol="BTC/USD", ...)
```

### Adding a New API Endpoint

1. Add a new route function to the appropriate route module:

```python
# In Tradingbot/api/routes/data_routes.py
def register_routes(app):
    # ... existing routes
    
    @app.route("/my_new_endpoint", methods=["GET"])
    def my_new_endpoint():
        # Implementation
        return jsonify({"result": "success"})
```

## Conclusion

This modular structure makes the Tradingbot codebase more maintainable, testable, and extensible, while still providing backwards compatibility with existing code.