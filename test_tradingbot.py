import pytest
import pandas as pd
from tradingbot import (
    place_order,
    get_current_price,
    calculate_indicators,
    execute_trading_strategy,
    SYMBOL,
    EMA_LENGTH,
    VOLUME_MULTIPLIER,
    TRADING_START_HOUR,
    TRADING_END_HOUR,
    ATR_MULTIPLIER,
    MAX_TRADES_PER_DAY,
    MAX_DAILY_LOSS,
    fetch_market_data,
    TIMEFRAME,
    LIMIT,
    run_backtest,
    detect_fvg
)
import logging
import os
import json

try:
    import ccxt
except ImportError:
    ccxt = None

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


@pytest.mark.parametrize("symbol", PAPER_SYMBOLS)
def test_trading_operations(symbol):
    place_order('buy', symbol, 0.001)
    place_order('sell', symbol, 0.001)
    current_price = get_current_price(symbol)
    if current_price is not None and isinstance(current_price, (int, float)):
        place_order('buy', symbol, 0.001, current_price - 10)
        place_order('sell', symbol, 0.001, current_price + 10)


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
    trades = run_backtest(
        SYMBOL, TIMEFRAME, LIMIT,
        EMA_LENGTH, VOLUME_MULTIPLIER, TRADING_START_HOUR, TRADING_END_HOUR,
        MAX_TRADES_PER_DAY, MAX_DAILY_LOSS, ATR_MULTIPLIER,
        print_orders=True, save_to_file="backtest_result.json"
    )
    assert trades is not None, "Backtest misslyckades eller inga trades genererades."
    print("[TEST] Backtest klart! Resultat sparat i backtest_result.json.")


def test_real_buy_order():
    print("\n[TEST] Lägger en riktig test-köporder på Bitfinex (paper account)...")
    place_order('buy', SYMBOL, 0.001)
    print("[TEST] Kontrollera ditt Bitfinex paper account för utförd köporder!")


def test_real_sell_order():
    print("\n[TEST] Lägger en riktig test-säljorder på Bitfinex (paper account)...")
    place_order('sell', SYMBOL, 0.001)
    print("[TEST] Kontrollera ditt Bitfinex paper account för utförd säljorder!")


def test_real_limit_orders():
    print("\n[TEST] Lägger riktiga limit orders på Bitfinex (paper account)...")
    current_price = get_current_price(SYMBOL)
    if current_price is not None and isinstance(current_price, (int, float)):
        place_order('buy', SYMBOL, 0.001, current_price - 10)
        place_order('sell', SYMBOL, 0.001, current_price + 10)
        print("[TEST] Kontrollera ditt Bitfinex paper account för utförda limit orders!")
    else:
        print("[TEST] Kunde inte hämta aktuellt pris, limit orders testades ej.")


def force_test_order(order_type='buy', symbol='tTESTBTC:TESTUSD', amount=0.001, price=None):
    """
    Lägger alltid en köp- eller säljorder på Bitfinex test-symbolen tTESTBTC:TESTUSD.
    Kan användas för att testa API och orderläggning. Sätt på standby vid behov.
    """
    print(f"[FORCE TEST ORDER] Försöker lägga en {order_type}-order på {symbol} (amount={amount}, price={price})")
    place_order(order_type, symbol, amount, price)


# Exempelanrop (avkommentera för att testa):
# force_test_order('buy')
# force_test_order('sell')


@pytest.mark.skipif(ccxt is None or not os.getenv("COINBASE_API_KEY_SANDBOX"), reason="ccxt saknas eller ingen sandbox-nyckel satt")
def test_coinbase_sandbox_order():
    api_key = os.getenv("COINBASE_API_KEY_SANDBOX")
    api_secret = os.getenv("COINBASE_API_SECRET_SANDBOX")
    assert api_key and api_secret, "Saknar sandbox-nycklar i .env"
    sandbox_url = "https://api-sandbox.coinbase.com/api/v3/brokerage"
    exchange = ccxt.coinbase({
        'apiKey': api_key,
        'secret': api_secret,
        'urls': {'api': sandbox_url},
        'headers': {'X-Sandbox': 'TRIGGER_ERROR'}
    })
    try:
        balance = exchange.fetch_balance()
        print("[SANDBOX] Balans:", balance)
    except Exception as e:
        print(f"[SANDBOX] Fel vid fetch_balance: {e}")
    try:
        order = exchange.create_market_buy_order('BTC-USD', 0.001)
        print("[SANDBOX] Orderresultat:", order)
    except Exception as e:
        print(f"[SANDBOX] Fel vid orderläggning: {e}")


def load_config():
    with open("config.json") as f:
        return json.load(f)


def execute_trading_strategy_with_debug(
    data,
    max_trades_per_day,
    max_daily_loss,
    atr_multiplier,
    symbol,
    lookback=100
):
    import numpy as np
    import logging
    if data is None or data.empty:
        logging.error("Data is invalid or empty. Trading strategy cannot be executed.")
        return
    if 'ema' not in data.columns or data['ema'].count() == 0:
        logging.critical("EMA indicator is missing or not calculated correctly. Exiting strategy.")
        return
    if 'high_volume' not in data.columns or data['high_volume'].count() == 0:
        logging.critical("High volume indicator is missing or not calculated correctly. Exiting strategy.")
        return
    if 'atr' not in data.columns or data['atr'].count() == 0:
        logging.critical("ATR indicator is missing or not calculated correctly. Exiting strategy.")
        return
    mean_atr = data['atr'].mean()
    trade_count = 0
    daily_loss = 0
    for index, row in data.iterrows():
        if daily_loss < -max_daily_loss:
            logging.debug(f"Avbryter: daily_loss ({daily_loss}) < -max_daily_loss ({-max_daily_loss})")
            break
        atr_condition = row['atr'] > atr_multiplier * mean_atr
        bull_fvg_high, bull_fvg_low = get_fvg(data.iloc[:index+1], lookback, bullish=True)
        bear_fvg_high, bear_fvg_low = get_fvg(data.iloc[:index+1], lookback, bullish=False)
        bull_fvg_high_ok = not np.isnan(bull_fvg_high)
        bear_fvg_high_ok = not np.isnan(bear_fvg_high)
        long_condition = (
            bull_fvg_high_ok and
            row['close'] < bull_fvg_low and
            row['close'] > row['ema'] and
            row['high_volume'] and
            row['within_trading_hours']
        )
        short_condition = (
            bear_fvg_high_ok and
            row['close'] > bear_fvg_high and
            row['close'] < row['ema'] and
            row['high_volume'] and
            row['within_trading_hours']
        )
        # Logga vilka villkor som inte uppfylldes
        if not (atr_condition and long_condition):
            reasons = []
            if not atr_condition:
                reasons.append("ATR-villkor")
            if not bull_fvg_high_ok:
                reasons.append("bull_fvg_high")
            if not (row['close'] < bull_fvg_low):
                reasons.append("close < bull_fvg_low")
            if not (row['close'] > row['ema']):
                reasons.append("close > ema")
            if not row['high_volume']:
                reasons.append("high_volume")
            if not row['within_trading_hours']:
                reasons.append("within_trading_hours")
            if reasons:
                print(f"[LONG] Rad {index}: Order EJ lagd. Ej uppfyllda villkor: {', '.join(reasons)}")
        if not (atr_condition and short_condition):
            reasons = []
            if not atr_condition:
                reasons.append("ATR-villkor")
            if not bear_fvg_high_ok:
                reasons.append("bear_fvg_high")
            if not (row['close'] > bear_fvg_high):
                reasons.append("close > bear_fvg_high")
            if not (row['close'] < row['ema']):
                reasons.append("close < ema")
            if not row['high_volume']:
                reasons.append("high_volume")
            if not row['within_trading_hours']:
                reasons.append("within_trading_hours")
            if reasons:
                print(f"[SHORT] Rad {index}: Order EJ lagd. Ej uppfyllda villkor: {', '.join(reasons)}")
        if atr_condition and long_condition and trade_count < max_trades_per_day:
            print(f"Lägger KÖP-order på rad {index}")
            trade_count += 1
            place_order('buy', symbol, 0.001, row['close'])
        if atr_condition and short_condition and trade_count < max_trades_per_day:
            print(f"Lägger SÄLJ-order på rad {index}")
            trade_count += 1
            place_order('sell', symbol, 0.001, row['close'])


def get_fvg(data, lookback, bullish=True):
    # Kopia av detect_fvg från tradingbot.py
    import numpy as np
    if len(data) < 2:
        return np.nan, np.nan
    if bullish:
        return data['high'].iloc[-2], data['low'].iloc[-1]
    else:
        return data['high'].iloc[-1], data['low'].iloc[-2]


if __name__ == "__main__":
    config = load_config()
    import pprint
    print("\n[LOGG] Aktiva parametrar vid körning:")
    pprint.pprint(config)
    # Ta bort testflaggor och testlogik
    # Endast strategi och backtest körs
    trades = run_backtest(
        symbol=config["SYMBOL"],
        timeframe=config["TIMEFRAME"],
        limit=config["LIMIT"],
        ema_length=config["EMA_LENGTH"],
        volume_multiplier=config["VOLUME_MULTIPLIER"],
        trading_start_hour=config["TRADING_START_HOUR"],
        trading_end_hour=config["TRADING_END_HOUR"],
        max_trades_per_day=config["MAX_TRADES_PER_DAY"],
        max_daily_loss=config["MAX_DAILY_LOSS"],
        atr_multiplier=config["ATR_MULTIPLIER"],
        lookback=config.get("LOOKBACK", 100),
        print_orders=True,
        save_to_file="backtest_result.json"
    )


class DummyExchange:
    def fetch_ohlcv(self, symbol, timeframe, limit):
        return [[1, 10, 15, 5, 12, 100], [2, 11, 16, 6, 13, 200]]
    def fetch_ticker(self, symbol):
        return {'last': 123.4}
    def create_market_buy_order(self, symbol, amount, params=None):
        return {'id': 'm1', 'status': 'open', 'price': None, 'amount': amount, 'filled': 0, 'type': 'market'}
    def create_limit_buy_order(self, symbol, amount, price, params=None):
        return {'id': 'l1', 'status': 'open', 'price': price, 'amount': amount, 'filled': 0, 'type': 'limit'}
    def create_market_sell_order(self, symbol, amount, params=None):
        return {'id': 'm2', 'status': 'open', 'price': None, 'amount': amount, 'filled': 0, 'type': 'market'}
    def create_limit_sell_order(self, symbol, amount, price, params=None):
        return {'id': 'l2', 'status': 'open', 'price': price, 'amount': amount, 'filled': 0, 'type': 'limit'}

@pytest.fixture(autouse=True)
def patch_exchange(monkeypatch):
    dummy = DummyExchange()
    monkeypatch.setattr('tradingbot.exchange', dummy)
    return dummy

def test_fetch_market_data_returns_dataframe():
    df = fetch_market_data('SYM', '1m', 2)
    assert isinstance(df, pd.DataFrame)
    assert set(['timestamp', 'open', 'high', 'low', 'close', 'volume', 'datetime']).issubset(df.columns)

def test_get_current_price_returns_last():
    price = get_current_price('SYM')
    assert price == 123.4

def test_calculate_indicators_adds_columns():
    df = fetch_market_data('SYM', '1m', 2)
    df2 = calculate_indicators(df, ema_length=2, volume_multiplier=1.0, trading_start_hour=0, trading_end_hour=23)
    for col in ['ema', 'atr', 'high_volume', 'rsi', 'adx', 'within_trading_hours']:
        assert col in df2.columns

def test_place_order_prints_information(capsys):
    place_order('buy', 'tTESTSYM', 0.5)
    captured = capsys.readouterr()
    assert 'type: buy' in captured.out.lower()
    assert 'symbol: tTESTSYM' in captured.out
    # Test limit order
    place_order('sell', 'tTESTSYM', 0.5, price=10)
    captured = capsys.readouterr()
    assert 'type: sell' in captured.out.lower()
    assert 'price: 10' in captured.out


@pytest.fixture
def sample_data():
    timestamps = pd.date_range('2021-01-01', periods=5, freq='H', tz='UTC')
    df = pd.DataFrame({
        'timestamp': [int(ts.value/1e6) for ts in timestamps],
        'open': [1, 2, 3, 4, 5],
        'high': [2, 3, 4, 5, 6],
        'low': [0.5, 1.5, 2.5, 3.5, 4.5],
        'close': [1.5, 2.5, 3.5, 4.5, 5.5],
        'volume': [10, 20, 30, 40, 50]
    })
    df['datetime'] = timestamps
    return df

def test_calculate_indicators_columns(sample_data):
    df = calculate_indicators(sample_data.copy(), ema_length=3, volume_multiplier=1.5, trading_start_hour=0, trading_end_hour=23)
    assert 'ema' in df.columns and df['ema'].notnull().any()
    assert 'atr' in df.columns and df['atr'].notnull().any()
    assert 'avg_volume' in df.columns and df['avg_volume'].notnull().any()
    assert 'high_volume' in df.columns
    assert 'rsi' in df.columns and df['rsi'].notnull().any()
    assert 'adx' in df.columns and df['adx'].notnull().any()
    assert 'within_trading_hours' in df.columns and df['within_trading_hours'].all()

def test_detect_fvg(sample_data):
    # bullish: previous high and last low
    high, low = detect_fvg(sample_data, lookback=2, bullish=True)
    assert high == sample_data['high'].iloc[-2]
    assert low == sample_data['low'].iloc[-1]
    # bearish: last high and previous low
    high_b, low_b = detect_fvg(sample_data, lookback=2, bullish=False)
    assert high_b == sample_data['high'].iloc[-1]
    assert low_b == sample_data['low'].iloc[-2]