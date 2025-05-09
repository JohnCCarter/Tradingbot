"""
Orderhantering för Tradingbot
"""
from typing import Dict, Any, List
import time
import random

class OrderError(Exception):
    pass

def create_limit_order(symbol: str, amount: float, price: float, side: str) -> Dict[str, Any]:
    if side not in ("buy", "sell"):
        raise OrderError("Ogiltig ordertyp")
    return {
        "id": f"order-{int(time.time())}-{random.randint(1000,9999)}",
        "type": "limit",
        "side": side,
        "symbol": symbol,
        "amount": amount,
        "price": price,
        "status": "open"
    }

def create_market_order(symbol: str, amount: float, side: str) -> Dict[str, Any]:
    if side not in ("buy", "sell"):
        raise OrderError("Ogiltig ordertyp")
    return {
        "id": f"order-{int(time.time())}-{random.randint(1000,9999)}",
        "type": "market",
        "side": side,
        "symbol": symbol,
        "amount": amount,
        "status": "executed"
    }

def parse_order_data(raw: dict) -> Dict[str, Any]:
    # Normalisera inkommande orderdata till intern struktur
    return {
        "id": raw.get("id"),
        "type": raw.get("type"),
        "side": raw.get("side"),
        "symbol": raw.get("symbol"),
        "amount": raw.get("amount"),
        "price": raw.get("price"),
        "status": raw.get("status")
    }

def cancel_order(order_id: str) -> bool:
    # Dummy-implementation
    return True

def get_open_orders() -> List[Dict[str, Any]]:
    # Dummy-implementation
    return []
