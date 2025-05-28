"""
Exchange interaction module for Tradingbot.
Handles communication with cryptocurrency exchanges.
"""

import os
import json
import hmac
import hashlib
import logging
import ccxt
import datetime
from Tradingbot.utils.logging import StructuredLogger
from Tradingbot.core.config import validate_api_keys
from Tradingbot.data.market_data import ensure_paper_trading_symbol

# Persistent nonce storage
NONCE_FILE = "nonce_store.json"


def get_next_nonce():
    """
    Generates a monotonic nonce value and persists it.
    
    Returns:
        int: Next nonce value
    """
    try:
        if os.path.exists(NONCE_FILE):
            with open(NONCE_FILE, "r") as f:
                last_nonce = json.load(f).get("last_nonce", 0)
        else:
            last_nonce = 0

        current_nonce = max(last_nonce + 1, int(datetime.datetime.now().timestamp() * 1_000))

        with open(NONCE_FILE, "w") as f:
            json.dump({"last_nonce": current_nonce}, f)

        return current_nonce
    except Exception as e:
        logging.error(f"Error generating nonce: {e}")
        raise


def build_auth_message(api_key, api_secret):
    """
    Build authentication message for WebSocket
    
    Args:
        api_key: API key
        api_secret: API secret
    
    Returns:
        str: JSON authentication message
    """
    nonce = get_next_nonce()
    payload = f"AUTH{nonce}"
    signature = hmac.new(
        api_secret.encode(), payload.encode(), hashlib.sha384
    ).hexdigest()
    return json.dumps(
        {
            "event": "auth",
            "apiKey": api_key,
            "authNonce": nonce,
            "authPayload": payload,
            "authSig": signature,
        }
    )


def create_exchange(exchange_name, api_key, api_secret):
    """
    Create exchange instance
    
    Args:
        exchange_name: Name of the exchange ('bitfinex', 'binance', etc)
        api_key: API key
        api_secret: API secret
    
    Returns:
        Exchange: Exchange instance
    """
    try:
        exchange_class = getattr(ccxt, exchange_name)
    except AttributeError:
        raise ValueError(f"Unsupported exchange: {exchange_name}")
    
    # Validate API keys
    validate_api_keys(api_key, api_secret, exchange_name)
    
    # Create exchange instance
    exchange = exchange_class(
        {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}
    )
    
    # Load markets
    exchange.load_markets()
    
    return exchange


def fetch_balance(exchange):
    """
    Fetch account balance from exchange
    
    Args:
        exchange: Exchange instance
    
    Returns:
        dict: Account balance or None if failed
    """
    try:
        return exchange.fetch_balance()
    except ccxt.AuthenticationError:
        # Propagate authentication errors
        raise
    except Exception as e:
        logging.error(f"Error fetching balance: {e}")
        return None


def place_order(
    exchange, logger, order_type, symbol, amount, price=None, stop_loss=None, take_profit=None,
    test_buy_order=True, test_sell_order=True, test_limit_orders=True
):
    """
    Place order on the exchange
    
    Args:
        exchange: Exchange instance
        logger: Logger instance
        order_type: 'buy' or 'sell'
        symbol: Trading symbol
        amount: Amount to buy/sell
        price: Price for limit orders, None for market orders
        stop_loss: Stop loss price
        take_profit: Take profit price
        test_buy_order: Whether to allow buy orders
        test_sell_order: Whether to allow sell orders
        test_limit_orders: Whether to allow limit orders
    
    Returns:
        dict: Order result or None if failed
    """
    logger.order(
        f"Attempting to place {order_type} order: symbol: {symbol}, amount: {amount}, price: {price}"
    )

    # Respect test mode flags
    if order_type == "buy" and not test_buy_order:
        logger.info("Buy orders are disabled, skipping.", "TEST")
        return
    if order_type == "sell" and not test_sell_order:
        logger.info("Sell orders are disabled, skipping.", "TEST")
        return
    # If limit orders are disabled, convert to market
    if price and not test_limit_orders:
        logger.info("Limit orders are disabled, placing market order instead.", "TEST")
        price = None
    if amount <= 0:
        logger.error(f"Invalid order amount: {amount}. Amount must be positive.")
        return
    
    try:
        params = {}

        # Specific handling for Bitfinex paper trading
        if exchange.id == "bitfinex":
            # For paper trading on Bitfinex, we need to use the right order type
            # and ensure the symbol is handled correctly

            # Check if using a paper trading symbol
            is_paper_trading = "TEST" in symbol

            # Always use EXCHANGE orders for paper trading on Bitfinex
            if is_paper_trading:
                if price:
                    params["type"] = "EXCHANGE LIMIT"
                else:
                    params["type"] = "EXCHANGE MARKET"

                logger.debug(f"Using paper trading parameters for symbol {symbol}")

        logger.debug(f"Calling {'limit' if price else 'market'} {order_type} order...")
        logger.debug(f"Params: {params}")

        if order_type == "buy":
            order = (
                exchange.create_limit_buy_order(symbol, amount, price, params)
                if price
                else exchange.create_market_buy_order(symbol, amount, params)
            )
        elif order_type == "sell":
            order = (
                exchange.create_limit_sell_order(symbol, amount, price, params)
                if price
                else exchange.create_market_sell_order(symbol, amount, params)
            )
        else:
            logger.error(f"Unknown order type: {order_type}")
            return

        # Backwards compatibility prints for tests - MATCHING EXACT CASE FROM TESTS
        print("\nOrder Information:")
        print(f"type: {order_type}")
        print(f"symbol: {symbol}")
        print(f"Amount: {amount}")
        if price:
            print(f"price: {price}")  # lowercase 'price' to match test expectation
        if stop_loss:
            print(f"Stop Loss: {stop_loss}")
        if take_profit:
            print(f"Take Profit: {take_profit}")

        # Create common order info string
        order_info = []
        order_info.append(f"Type: {order_type.capitalize()}")
        order_info.append(f"Symbol: {symbol}")
        order_info.append(f"Amount: {amount}")
        if price:
            order_info.append(f"Price: {price}")
        if stop_loss:
            order_info.append(f"Stop Loss: {stop_loss}")
        if take_profit:
            order_info.append(f"Take Profit: {take_profit}")

        # Format for separate log output
        order_info_str = ", ".join(order_info)
        logger.trade(f"Order created: {order_info_str}")

        # Create order details for logging
        relevant_details = {
            "Order-ID": order.get("id", "N/A") if order else "N/A",
            "Status": order.get("status", "N/A") if order else "N/A",
            "Price": order.get("price", "N/A") if order else "N/A",
            "Amount": order.get("amount", "N/A") if order else "N/A",
            "Filled": order.get("filled", "N/A") if order else "N/A",
            "Order type": order.get("type", "N/A") if order else "N/A",
            "Timestamp": order.get("datetime", "N/A") if order else "N/A",
        }

        # Print details with nice formatting
        logger.separator("-", 40)
        logger.order("Order details:")
        for key, value in relevant_details.items():
            logger.order(f"  {key}: {value}")
        logger.separator("-", 40)

        # Print for backward compatibility with tests
        print("\nOrderdetaljer (simplified):")
        for key, value in relevant_details.items():
            print(f"{key}: {value}")

        # Log to order status file
        with open("order_status_log.txt", "a") as f:
            f.write(
                f"{datetime.datetime.now()}: Order-ID: {order.get('id', 'N/A')}, "
                f"Status: {order.get('status', 'N/A')}, "
                f"Info: {json.dumps([symbol, order_type, amount, price])}\n"
            )

        return order

    except Exception as e:
        logger.error(f"Error placing order: {str(e)}")
        logger.debug(f"Detailed error for {order_type} order: {repr(e)}")
        return None


def create_limit_order(exchange, logger, symbol, side, amount, price):
    """
    Create a limit order
    
    Args:
        exchange: Exchange instance
        logger: Logger instance
        symbol: Trading symbol
        side: 'buy' or 'sell'
        amount: Amount
        price: Price
    
    Returns:
        dict: Order result or None if failed
    """
    try:
        # Ensure correct symbol format for paper trading
        if exchange.id == "bitfinex":
            symbol = ensure_paper_trading_symbol(symbol)

        order = exchange.create_limit_order(symbol, side, amount, price)
        logger.info(f"Limit order: {order}")
        return order
    except Exception as e:
        logger.error(f"Error creating limit order: {e}")
        return None


def create_market_order(exchange, logger, symbol, side, amount):
    """
    Create a market order
    
    Args:
        exchange: Exchange instance
        logger: Logger instance
        symbol: Trading symbol
        side: 'buy' or 'sell'
        amount: Amount
    
    Returns:
        dict: Order result or None if failed
    """
    try:
        # Ensure correct symbol format for paper trading
        if exchange.id == "bitfinex":
            symbol = ensure_paper_trading_symbol(symbol)

        order = exchange.create_market_order(symbol, side, amount)
        logger.info(f"Market order: {order}")
        return order
    except Exception as e:
        logger.error(f"Error creating market order: {e}")
        return None


def get_open_orders(exchange, logger, symbol=None):
    """
    Get open orders from exchange
    
    Args:
        exchange: Exchange instance
        logger: Logger instance
        symbol: Trading symbol (optional)
    
    Returns:
        list: List of open orders
    """
    try:
        # Ensure correct symbol format for paper trading
        if symbol and exchange.id == "bitfinex":
            symbol = ensure_paper_trading_symbol(symbol)

        open_orders = exchange.fetch_open_orders(symbol)
        for order in open_orders:
            if symbol and order.get("symbol") != symbol:
                continue
        return open_orders
    except Exception as e:
        logger.error(f"Error fetching open orders: {e}")
        return []


def cancel_order(exchange, logger, order_id, symbol=None):
    """
    Cancel an order
    
    Args:
        exchange: Exchange instance
        logger: Logger instance
        order_id: Order ID
        symbol: Trading symbol (optional)
    
    Returns:
        dict: Result or None if failed
    """
    try:
        # Ensure correct symbol format for paper trading
        if symbol and exchange.id == "bitfinex":
            symbol = ensure_paper_trading_symbol(symbol)

        result = exchange.cancel_order(order_id, symbol)
        logger.info(f"Canceled order: {result}")
        return result
    except Exception as e:
        logger.error(f"Error canceling order: {e}")
        return None