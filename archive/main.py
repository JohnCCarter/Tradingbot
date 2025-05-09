"""
Huvudskript för Tradingbot
"""
import asyncio
import signal
from config import ConfigManager
from exchange import ExchangeClient
from db import SupabaseClient, LocalFallback
from logger import StructuredLogger
from api_server import app
#from metrics import start_metrics_server

async def main():
    config = ConfigManager().get()
    logger = StructuredLogger("Tradingbot", log_file="tradingbot.log")
    # Always use Bitfinex paper trading
    exchange = ExchangeClient(config.API_KEY, config.API_SECRET, exchange_name="bitfinex", paper=True)
    db = SupabaseClient(config.SUPABASE_URL, config.SUPABASE_KEY)
    fallback = LocalFallback()
    # Starta ENDAST Flask API-server för enklare test (Prometheus avkommenterad)
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(None, app.run, "0.0.0.0", 5000),
        # loop.run_in_executor(None, start_metrics_server, config.METRICS_PORT),
        # Lägg till realtidsloop och strategi här
    ]
    await asyncio.gather(*tasks)

def shutdown():
    print("Avslutar Tradingbot...")
    exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: shutdown())
    signal.signal(signal.SIGTERM, lambda s, f: shutdown())
    asyncio.run(main())
