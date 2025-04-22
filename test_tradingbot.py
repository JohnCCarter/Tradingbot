import pytest
from tradingbot import (
    place_order, get_current_price, calculate_indicators, execute_trading_strategy, convert_to_local_time,
    SYMBOL, EMA_LENGTH, VOLUME_MULTIPLIER, TRADING_START_HOUR, TRADING_END_HOUR, ATR_MULTIPLIER, MAX_TRADES_PER_DAY, MAX_DAILY_LOSS,
    fetch_market_data, TIMEFRAME, LIMIT, run_backtest
)
import pandas as pd
import logging
import ccxt
import os

# Lista på korrekta Bitfinex paper trading-symboler
PAPER_SYMBOLS = [
    "testxaut:testusd",
    "testeth:testusd",
    "testavax:testusd",
    "testdoge:testusd",
    "testxtz:testusd",
    "testalgo:testusd",
    "testnear:testusd",
    "testfil:testusd",
    "testada:testusd",
    "testltc:testusd",
    "testapt:testusd",
    "testeos:testusd",
    "testbtc:testusdt",
    "testmatic:testusd",
    "testmatic:testusdt",
    "testdot:testusd",
    "testsol:testusd",
]

import pytest

@pytest.mark.parametrize("symbol", PAPER_SYMBOLS)
def test_trading_operations(symbol):
    # Test buy order
    place_order('buy', symbol, 0.001)
    # Test sell order
    place_order('sell', symbol, 0.001)
    # Test limit orders
    current_price = get_current_price(symbol)
    if current_price is not None and isinstance(current_price, (int, float)):
        place_order('buy', symbol, 0.001, current_price - 10)
        place_order('sell', symbol, 0.001, current_price + 10)


def test_config_and_strategy():
    # Skapa en dummy-DataFrame för att testa strategin
    dummy_data = pd.DataFrame({
        'timestamp': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] * 10,
        'open': [100]*100,
        'high': [110]*100,
        'low': [90]*100,
        'close': [100 + i for i in range(100)],
        'volume': [1.0]*100,
        'datetime': pd.date_range('2025-04-16', periods=100, freq='h', tz='UTC')
    })
    dummy_data['local_datetime'] = dummy_data['datetime'].apply(convert_to_local_time)
    dummy_data = calculate_indicators(dummy_data, EMA_LENGTH, VOLUME_MULTIPLIER, TRADING_START_HOUR, TRADING_END_HOUR)
    execute_trading_strategy(
        dummy_data,
        MAX_TRADES_PER_DAY,
        MAX_DAILY_LOSS,
        ATR_MULTIPLIER,
        SYMBOL
    )


def test_execute_trading_strategy_with_live_data():
    logging.info("[TEST] Hämtar marknadsdata och kör strategi på riktigt (paper account)...")
    data = fetch_market_data(SYMBOL, TIMEFRAME, LIMIT)
    assert data is not None and not data.empty, "Kunde inte hämta marknadsdata."
    data = calculate_indicators(data, EMA_LENGTH, VOLUME_MULTIPLIER, TRADING_START_HOUR, TRADING_END_HOUR)
    assert data is not None, "Kunde inte beräkna indikatorer."
    logging.info("[TEST] Kör execute_trading_strategy (detta kan skapa köp/sälj på ditt paper account)...")
    execute_trading_strategy(
        data,
        MAX_TRADES_PER_DAY,
        MAX_DAILY_LOSS,
        ATR_MULTIPLIER,
        SYMBOL
    )
    logging.info("[TEST] Klart! Kontrollera ditt Bitfinex paper account för utförda ordrar.")


def test_run_backtest():
    logging.info("[TEST] Kör backtest på historisk data...")
    trades = run_backtest(
        SYMBOL, TIMEFRAME, LIMIT,
        EMA_LENGTH, VOLUME_MULTIPLIER, TRADING_START_HOUR, TRADING_END_HOUR,
        MAX_TRADES_PER_DAY, MAX_DAILY_LOSS, ATR_MULTIPLIER,
        print_orders=True
    )
    assert trades is not None, "Backtest misslyckades eller inga trades genererades."
    logging.info("[TEST] Backtest klart!")


def test_run_backtest_and_save():
    print("\n[TEST] Kör backtest och sparar resultat till backtest_result.json...")
    from tradingbot import run_backtest, SYMBOL, TIMEFRAME, LIMIT, EMA_LENGTH, VOLUME_MULTIPLIER, TRADING_START_HOUR, TRADING_END_HOUR, MAX_TRADES_PER_DAY, MAX_DAILY_LOSS, ATR_MULTIPLIER
    trades = run_backtest(
        SYMBOL, TIMEFRAME, LIMIT,
        EMA_LENGTH, VOLUME_MULTIPLIER, TRADING_START_HOUR, TRADING_END_HOUR,
        MAX_TRADES_PER_DAY, MAX_DAILY_LOSS, ATR_MULTIPLIER,
        print_orders=True, save_to_file="backtest_result.json"
    )
    assert trades is not None, "Backtest misslyckades eller inga trades genererades."
    print("[TEST] Backtest klart! Resultat sparat i backtest_result.json.")


def test_real_buy_order():
    print("\n[TEST] Försöker lägga en riktig test-köporder på Bitfinex (paper account)...")
    from tradingbot import place_order, SYMBOL
    # Testköp med liten mängd på paper account
    place_order('buy', SYMBOL, 0.001)
    print("[TEST] Om du ser ordern i ditt Bitfinex paper account fungerar API och orderläggning!")


def force_test_order(order_type='buy', symbol='tTESTBTC:TESTUSD', amount=0.001, price=None):
    """
    Lägger alltid en köp- eller säljorder på Bitfinex test-symbolen tTESTBTC:TESTUSD.
    Kan användas för att testa API och orderläggning. Sätt på standby vid behov.
    """
    from tradingbot import place_order
    print(f"[FORCE TEST ORDER] Försöker lägga en {order_type}-order på {symbol} (amount={amount}, price={price})")
    place_order(order_type, symbol, amount, price)

# Exempelanrop (avkommentera för att testa):
# force_test_order('buy')
# force_test_order('sell')

# Testa Coinbase Advanced Trade sandbox med custom header
@pytest.mark.skipif(not os.getenv("COINBASE_API_KEY_SANDBOX"), reason="Ingen sandbox-nyckel satt")
def test_coinbase_sandbox_order():
    api_key = os.getenv("COINBASE_API_KEY_SANDBOX")
    api_secret = os.getenv("COINBASE_API_SECRET_SANDBOX")
    assert api_key and api_secret, "Saknar sandbox-nycklar i .env"
    sandbox_url = "https://api-sandbox.coinbase.com/api/v3/brokerage"
    exchange = ccxt.coinbase({
        'apiKey': api_key,
        'secret': api_secret,
        'urls': {'api': sandbox_url},
        'headers': {'X-Sandbox': 'TRIGGER_ERROR'}  # Byt värde för att testa olika scenarier
    })
    # Exempel: testa att hämta balans eller marknadsdata
    try:
        balance = exchange.fetch_balance()
        print("[SANDBOX] Balans:", balance)
    except Exception as e:
        print(f"[SANDBOX] Fel vid fetch_balance: {e}")
    # Exempel: testa orderläggning (byt symbol till en som stöds i sandbox)
    try:
        # Byt till en giltig sandbox-symbol om nödvändigt
        order = exchange.create_market_buy_order('BTC-USD', 0.001)
        print("[SANDBOX] Orderresultat:", order)
    except Exception as e:
        print(f"[SANDBOX] Fel vid orderläggning: {e}")

if __name__ == "__main__":
    from tradingbot import run_backtest
    # Kör backtest med alla parametrar direkt i testfilen
    trades = run_backtest(
        symbol="tTESTBTC:TESTUSD",
        timeframe="1h",
        limit=240,
        ema_length=10,
        volume_multiplier=0.1,
        trading_start_hour=0,
        trading_end_hour=23,
        max_trades_per_day=100,
        max_daily_loss=10000,
        atr_multiplier=0.1,
        lookback=10,
        print_orders=True,
        save_to_file="backtest_result.json"
    )
