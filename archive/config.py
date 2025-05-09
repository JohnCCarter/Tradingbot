"""
Konfigurationshantering för Tradingbot
"""
import json
import os
import pathlib
from dotenv import load_dotenv
from typing import Optional
from pydantic import BaseModel, ValidationError

# Ladda .env och miljövariabler
load_dotenv()

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
    EMAIL_PASSWORD: str = ""
    LOOKBACK: int
    TEST_BUY_ORDER: bool = True
    TEST_SELL_ORDER: bool = True
    TEST_LIMIT_ORDERS: bool = True
   # METRICS_PORT: int = 8000
    HEALTH_PORT: int = 5001
    API_KEY: str
    API_SECRET: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    CONFIG_VERSION: Optional[str] = "1.0"

class ConfigError(Exception):
    pass

class ConfigManager:
    def __init__(self, config_path=None, version="1.0"):
        # Sök alltid config.json relativt denna fil
        if config_path is None:
            base_dir = pathlib.Path(__file__).parent
            config_path = str(base_dir / "config.json")
        self.config_path = config_path
        self.version = version
        self.config = None
        self.load()

    def load(self):
        try:
            with open(self.config_path) as f:
                raw_config = json.load(f)
            if raw_config.get("CONFIG_VERSION") != self.version:
                print(f"[ConfigManager] Version mismatch: {raw_config.get('CONFIG_VERSION')} != {self.version}")
            # Always override secrets from environment
            env_secrets = {
                "API_KEY": os.getenv("API_KEY"),
                "API_SECRET": os.getenv("API_SECRET"),
                "SUPABASE_URL": os.getenv("SUPABASE_URL"),
                "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
            }
            for k, v in env_secrets.items():
                if v:
                    raw_config[k] = v
            self.config = BotConfig(**raw_config)
        except (FileNotFoundError, ValidationError, KeyError) as e:
            raise ConfigError(f"Fel vid laddning av konfiguration: {e}")

    def save(self):
        with open(self.config_path, "w") as f:
            json.dump(self.config.dict(), f, indent=2)

    def get(self):
        return self.config

# Funktion för att ladda config från miljövariabler och .env

def load_env_config():
    try:
        env_vars = {
            "API_KEY": os.getenv("API_KEY"),
            "API_SECRET": os.getenv("API_SECRET"),
            "SUPABASE_URL": os.getenv("SUPABASE_URL"),
            "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
        }
        # Kontrollera att alla är satta
        if not all(env_vars.values()):
            missing = [k for k, v in env_vars.items() if not v]
            raise ConfigError(f"Saknade miljövariabler: {', '.join(missing)}")
        return BotConfig(**env_vars)
    except ValidationError as e:
        raise ConfigError(f"Fel i miljökonfiguration: {e}")

def load_config(path="config.json"):
    with open(path) as f:
        raw_config = json.load(f)
    return BotConfig(**raw_config)
