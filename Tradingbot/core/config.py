"""
Configuration handling for Tradingbot.
Loads configuration from file or environment variables.
"""

import os
import json
import logging
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Config schema
class BotConfig(BaseModel):
    EXCHANGE: str
    SYMBOL: str
    TIMEFRAME: str
    LIMIT: int
    EMA_LENGTH: int
    ATR_MULTIPLIER: float
    VOLUME_MULTIPLIER: float
    TRADING_START_HOUR: int
    TRADING_END_HOUR: int
    MAX_DAILY_LOSS: float
    MAX_TRADES_PER_DAY: int
    STOP_LOSS_PERCENT: float = 2.0
    TAKE_PROFIT_PERCENT: float = 4.0
    EMAIL_NOTIFICATIONS: bool = False
    EMAIL_SMTP_SERVER: str = "smtp.gmail.com"
    EMAIL_SMTP_PORT: int = 465
    EMAIL_SENDER: str = ""
    EMAIL_RECEIVER: str = ""
    EMAIL_PASSWORD: str = ""  # Lösenord för e-postnotifikationer
    LOOKBACK: int
    TEST_BUY_ORDER: bool = True
    TEST_SELL_ORDER: bool = True
    TEST_LIMIT_ORDERS: bool = True
    METRICS_PORT: int = 8000
    HEALTH_PORT: int = 5001


def get_default_config():
    """Return a default config for development/testing if config.json is missing."""
    return dict(
        EXCHANGE="bitfinex",
        SYMBOL="BTC/USD",
        TIMEFRAME="1m",
        LIMIT=100,
        EMA_LENGTH=14,
        ATR_MULTIPLIER=1.5,
        VOLUME_MULTIPLIER=1.2,
        TRADING_START_HOUR=0,
        TRADING_END_HOUR=23,
        MAX_DAILY_LOSS=100.0,
        MAX_TRADES_PER_DAY=10,
        STOP_LOSS_PERCENT=2.0,
        TAKE_PROFIT_PERCENT=4.0,
        EMAIL_NOTIFICATIONS=False,
        EMAIL_SMTP_SERVER="smtp.gmail.com",
        EMAIL_SMTP_PORT=465,
        EMAIL_SENDER="",
        EMAIL_RECEIVER="",
        EMAIL_PASSWORD="",
        LOOKBACK=20,
        TEST_BUY_ORDER=True,
        TEST_SELL_ORDER=True,
        TEST_LIMIT_ORDERS=True,
        METRICS_PORT=8000,
        HEALTH_PORT=5001,
    )


def load_config(config_path="config.json", logger=None):
    """
    Load configuration from file or use default values.
    
    Args:
        config_path: Path to config.json
        logger: Logger instance for warnings
    
    Returns:
        BotConfig: Configuration object
    """
    log = logger or logging.getLogger()
    
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                raw_config = json.load(f)
            log.info(f"Configuration loaded from {config_path}")
        except Exception as e:
            log.error(f"Error loading config from {config_path}: {e}")
            log.warning("Using default configuration")
            raw_config = get_default_config()
    else:
        log.warning(f"Config file {config_path} not found. Using default configuration.")
        raw_config = get_default_config()
    
    # Create config object
    config = BotConfig(**raw_config)
    
    # Override from environment variables
    config.EMAIL_SENDER = os.getenv("EMAIL_SENDER", config.EMAIL_SENDER)
    config.EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", config.EMAIL_RECEIVER)
    config.EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", config.EMAIL_PASSWORD)
    
    return config


def validate_api_keys(api_key, api_secret, exchange_name=""):
    """
    Validate that API keys are properly set.
    
    Args:
        api_key: API key
        api_secret: API secret
        exchange_name: Optional exchange name for error message
        
    Raises:
        ValueError: If keys are missing or invalid
    """
    if (
        not api_key
        or not api_secret
        or api_key == "DUMMY_KEY"
        or api_secret == "DUMMY_SECRET"
    ):
        raise ValueError(
            f"API_KEY and API_SECRET are required{f' for {exchange_name}' if exchange_name else ''}. Please check your environment variables."
        )