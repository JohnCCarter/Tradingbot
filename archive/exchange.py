"""
Exchange-relaterade funktioner för Tradingbot
"""
# Här placeras funktioner som fetch_market_data, fetch_balance, place_order etc.
import pandas as pd
import logging
import ccxt
import asyncio
from utils import ensure_paper_trading_symbol

class ExchangeClient:
    def __init__(self, api_key, api_secret, exchange_name="bitfinex", paper=True):
        exchange_args = {
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True
        }
        if exchange_name == "bitfinex" and paper:
            exchange_args['options'] = {'defaultType': 'spot', 'paper': True}
        self.exchange = getattr(ccxt, exchange_name)(exchange_args)
        self.exchange_name = exchange_name
        self.paper = paper

    def fetch_balance(self):
        try:
            return self.exchange.fetch_balance()
        except Exception as e:
            logging.error(f"Fel vid hämtning av balans: {e}")
            return {}

    def fetch_market_data(self, symbol, timeframe='1h', limit=100):
        try:
            symbol = ensure_paper_trading_symbol(symbol) if self.exchange_name == "bitfinex" and self.paper else symbol
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            return df
        except Exception as e:
            logging.error(f"Fel vid hämtning av marknadsdata: {e}")
            return pd.DataFrame()

    def fetch_historical_data(self, symbol, timeframe='1h', since=None, limit=100):
        try:
            symbol = ensure_paper_trading_symbol(symbol) if self.exchange_name == "bitfinex" and self.paper else symbol
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            return df
        except Exception as e:
            logging.error(f"Fel vid hämtning av historisk data: {e}")
            return pd.DataFrame()

    async def async_fetch_market_data(self, symbol, timeframe='1h', limit=100):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.fetch_market_data, symbol, timeframe, limit)

    def get_orderbook(self, symbol):
        try:
            symbol = ensure_paper_trading_symbol(symbol) if self.exchange_name == "bitfinex" and self.paper else symbol
            return self.exchange.fetch_order_book(symbol)
        except Exception as e:
            logging.error(f"Fel vid hämtning av orderbok: {e}")
            return {}

    def get_current_price(self, symbol):
        try:
            symbol = ensure_paper_trading_symbol(symbol) if self.exchange_name == "bitfinex" and self.paper else symbol
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker.get('last')
        except Exception as e:
            logging.error(f"Fel vid hämtning av aktuellt pris: {e}")
            return None

def fetch_market_data(exchange, symbol: str, timeframe: str = '1h', limit: int = 100) -> pd.DataFrame:
    """Hämtar marknadsdata från börs (dummy för test)
    Args:
        exchange: Exchange-instans (t.ex. ccxt)
        symbol (str): Symbol att hämta data för
        timeframe (str): Tidsintervall, t.ex. '1h'
        limit (int): Antal datapunkter
    Returns:
        pd.DataFrame: OHLCV-data
    """
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv or len(ohlcv) == 0:
            logging.error(f"Ingen marknadsdata hittades för {symbol} på {timeframe}")
            return pd.DataFrame()
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        return df
    except Exception as e:
        logging.error(f"Fel vid hämtning av marknadsdata: {e}")
        return pd.DataFrame()

def fetch_balance() -> dict:
    """Returnerar dummy-balans för test
    Returns:
        dict: Balans per valuta
    """
    return {"USD": 10000.0, "BTC": 0.5, "ETH": 5.0}

def place_order(order_type: str, symbol: str, amount: float, price: float = None, stop_loss: float = None, take_profit: float = None) -> dict:
    """Simulerar orderläggning och skriver ut orderinfo (för test och demo)
    Args:
        order_type (str): 'buy' eller 'sell'
        symbol (str): Symbol
        amount (float): Mängd
        price (float, optional): Limitpris
        stop_loss (float, optional): Stop loss-nivå
        take_profit (float, optional): Take profit-nivå
    Returns:
        dict: Orderinfo
    """
    print("\nOrder Information:")
    print(f"type: {order_type}")
    print(f"symbol: {symbol}")
    print(f"Amount: {amount}")
    if price is not None:
        print(f"price: {price}")
    if stop_loss is not None:
        print(f"Stop Loss: {stop_loss}")
    if take_profit is not None:
        print(f"Take Profit: {take_profit}")
    # Returnera dummy-order
    return {
        "id": "dummy-order",
        "type": order_type,
        "symbol": symbol,
        "amount": amount,
        "price": price,
        "status": "executed"
    }

def get_current_price(symbol: str, exchange=None) -> float:
    """Hämtar aktuellt pris för symbol från börs om exchange ges, annars dummyvärde.
    Args:
        symbol (str): Symbol
        exchange: Exchange-instans (valfri)
    Returns:
        float: Senaste pris
    """
    if exchange is not None:
        try:
            ticker = exchange.fetch_ticker(symbol)
            if "last" in ticker:
                return ticker["last"]
            else:
                logging.warning("'last' key not found in ticker data.")
                return None
        except Exception as e:
            logging.error(f"Error fetching current price: {e}")
            return None
    # Fallback för tester
    return 123.4

def run_backtest(*args, **kwargs) -> list:
    """Stub för backtest-funktion. Implementera riktig logik vid behov.
    Returns:
        list: Resultatlista
    """
    return []

def execute_trading_strategy(*args, **kwargs) -> None:
    """Stub för strategi-exekvering. Implementera riktig logik vid behov.
    Returns:
        None
    """
    pass
