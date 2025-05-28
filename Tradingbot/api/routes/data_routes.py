"""
Market data routes for Tradingbot API.
Handles historical data, realtime data, and logs.
"""

import os
import logging
from flask import jsonify, request
import ccxt
from Tradingbot.data.market_data import fetch_market_data, ensure_paper_trading_symbol


logger = logging.getLogger(__name__)


def register_routes(app):
    """Register market data routes with Flask app"""
    
    @app.route("/historical", methods=["GET"])
    def get_historical_data():
        """Get historical market data"""
        try:
            from tradingbot import EXCHANGE
            
            symbol = request.args.get("symbol", "BTC/USD")
            timeframe = request.args.get("timeframe", "1h")
            limit = int(request.args.get("limit", "100"))
        
            # Format symbol for paper trading
            if EXCHANGE.id == "bitfinex" and EXCHANGE.options.get("paper", False):
                symbol = ensure_paper_trading_symbol(symbol)
                logger.info(f"Historical data using paper trading symbol: {symbol}")
        
            # Fetch historical data
            df = fetch_market_data(EXCHANGE, symbol, timeframe, limit)
            
            # Return formatted data
            return jsonify(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "data": df.reset_index().to_dict(orient="records"),
                }
            )
        except Exception as e:
            logger.exception(f"Error fetching historical data: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route("/realtimedata", methods=["GET"])
    def realtimatedata():
        """Get realtime market data"""
        try:
            from tradingbot import (
                get_current_price,
                SYMBOL,
                ensure_paper_trading_symbol,
                EXCHANGE_NAME,
            )
        
            symbol = request.args.get("symbol") or SYMBOL
        
            # Format symbol for paper trading
            if EXCHANGE_NAME == "bitfinex":
                symbol = ensure_paper_trading_symbol(symbol)
        
            # Get current price
            price = get_current_price(symbol)
            return jsonify({"symbol": symbol, "price": price})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/ticker", methods=["GET"])
    def ticker_endpoint():
        """Get current ticker data for a symbol"""
        try:
            from tradingbot import get_current_price, SYMBOL
        
            # Fetch the current price for the default symbol
            price = get_current_price(SYMBOL)
            return jsonify({"symbol": SYMBOL, "price": price})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/pricehistory", methods=["GET"])
    def pricehistory():
        """Fetch historical price data for a given symbol"""
        import time
        
        # Initialize exchange (example: Bitfinex)
        exchange = ccxt.bitfinex()
        
        # Ensure nonce is initialized
        if not hasattr(exchange, "nonce"):
            exchange.nonce = int(time.time() * 1000)
        
        # Get query parameters
        symbol = request.args.get("symbol")
        timeframe = request.args.get("timeframe", "1d")  # Default to daily candles
        limit = int(request.args.get("limit", 100))  # Default to 100 candles
        
        if not symbol:
            return jsonify({"error": "Missing 'symbol' parameter"}), 400
        
        try:
            # Fetch historical OHLCV data
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        except ccxt.BaseError as e:
            logger.error(f"CCXT error fetching OHLCV data: {e}")
            return jsonify({"error": "CCXTError", "message": str(e)}), 500
        except Exception as e:
            logger.exception("Unexpected error in /pricehistory:")
            return jsonify({"error": "UnexpectedError", "message": str(e)}), 500
        
        # Format the response
        data = [
            {
                "timestamp": candle[0],
                "open": candle[1],
                "high": candle[2],
                "low": candle[3],
                "close": candle[4],
                "volume": candle[5],
            }
            for candle in ohlcv
        ]
        
        return jsonify({"symbol": symbol, "timeframe": timeframe, "data": data})
    
    @app.route("/logs", methods=["GET"])
    def get_logs():
        """Get technical/system logs"""
        log_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "order_status_log.txt")
        if not os.path.exists(log_path):
            return jsonify({"logs": []})
        
        logs = []
        with open(log_path, "r") as f:
            for line in f:
                # Only show technical/system logs, filter out order events
                if "EXECUTED" not in line and "CANCELED" not in line:
                    logs.append(line.strip())
        
        # Return the most recent logs (limited to 100)
        return jsonify({"logs": logs[-100:]})
    
    @app.route("/frontend_error_log", methods=["POST"])
    def frontend_error_log():
        """Log frontend errors to a file"""
        import json
        import time
        
        try:
            error_data = request.get_json(force=True)
            log_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend_errors.log")
            
            with open(log_path, "a") as f:
                log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {json.dumps(error_data, ensure_ascii=False)}\n"
                f.write(log_entry)
            
            return jsonify({"logged": True})
        except Exception as e:
            logger.error(f"Failed to log frontend error: {e}")
            return jsonify({"logged": False, "error": str(e)}), 500