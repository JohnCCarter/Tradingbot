"""
Order handling routes for Tradingbot API.
Handles order creation, history, and order management.
"""

import os
import logging
from flask import jsonify, request
import ccxt

logger = logging.getLogger(__name__)


def register_routes(app):
    """Register order-related routes with Flask app"""
    
    @app.route("/order", methods=["POST"])
    def create_order():
        """Create a new order"""
        data = request.json
        order_type = data.get("type")  # 'buy' or 'sell'
        symbol = data.get("symbol")
        amount = float(data.get("amount", 0.001))
        price = data.get("price")
        if price is not None:
            price = float(price)
        
        # Import required functions
        try:
            from tradingbot import place_order, ensure_paper_trading_symbol, EXCHANGE_NAME
            
            # Format symbol for paper trading
            if EXCHANGE_NAME == "bitfinex":
                symbol = ensure_paper_trading_symbol(symbol)
            
            # Place the order
            place_order(order_type, symbol, amount, price)
            
            return jsonify(
                {"success": True, "message": f"{order_type} order sent for {symbol}."}
            )
        except Exception:
            logger.exception("Error in create_order:")
            return jsonify({"success": False, "error": "Could not place order."}), 400
    
    @app.route("/orders", methods=["GET"])
    def get_orders():
        """Get recent order history"""
        log_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "order_status_log.txt")
        if not os.path.exists(log_path):
            return jsonify({"orders": []})
        
        orders = []
        with open(log_path, "r") as f:
            for line in f:
                if "EXECUTED" in line or "CANCELED" in line:
                    orders.append(line.strip())
        
        # Return most recent orders (limited to 20)
        return jsonify({"orders": orders[-20:]})
    
    @app.route("/orderhistory", methods=["GET"])
    def order_history():
        """Get detailed order history with filtering"""
        log_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "order_status_log.txt")
        if not os.path.exists(log_path):
            return jsonify({"orders": [], "status": "no_file"})
        
        symbol = request.args.get("symbol")
        date = request.args.get("date")  # format: 'YYYY-MM-DD'
        debug = request.args.get("debug") == "true"
        
        # Prepare a more detailed response
        response = {"orders": [], "status": "ok", "debug_info": {} if debug else None}
        
        # For debug mode, collect unique dates from log file
        unique_dates = set()
        total_lines = 0
        matched_order_count = 0
        
        with open(log_path, "r") as f:
            for line in f:
                total_lines += 1
                
                # Extract date from beginning of the line (if possible)
                try:
                    line_date = line.split(" ")[0]
                    if debug:
                        unique_dates.add(line_date)
                except:
                    pass
                
                # Filter for order events
                if (
                    "EXECUTED" not in line
                    and "CANCELED" not in line
                    and "CANCELLED" not in line
                ):
                    continue
                
                # Apply symbol filter if specified
                if symbol and symbol not in line:
                    continue
                
                # Apply date filter if specified
                if date:
                    if not line.startswith(date):
                        # Try more flexible matching if not exact match at start
                        if date not in line.split(" ")[0]:
                            continue
                
                matched_order_count += 1
                response["orders"].append(line.strip())
        
        # Limit to the most recent 20 entries
        response["orders"] = response["orders"][-20:]
        
        # Add debugging information if enabled
        if debug:
            response["debug_info"] = {
                "total_lines": total_lines,
                "matched_order_count": matched_order_count,
                "unique_dates": sorted(list(unique_dates)),
                "date_filter": date,
                "symbol_filter": symbol,
            }
        
        # Log summary
        logger.info(
            f"Found {matched_order_count} order history entries"
            + (f" for date {date}" if date else "")
            + (f" and symbol {symbol}" if symbol else "")
        )
        
        return jsonify(response)
    
    @app.route("/openorders", methods=["GET"])
    def get_open_orders():
        """Get open orders from the exchange"""
        try:
            from tradingbot import exchange, ensure_paper_trading_symbol, EXCHANGE_NAME
            
            # Check and convert symbol format if specified
            symbol_param = request.args.get("symbol")
            if symbol_param and EXCHANGE_NAME == "bitfinex":
                symbol_param = ensure_paper_trading_symbol(symbol_param)
            
            # Use CCXT fetch_open_orders to retrieve active orders
            open_orders = (
                exchange.fetch_open_orders(symbol_param)
                if symbol_param
                else exchange.fetch_open_orders()
            )
            
            # Log the response for debugging
            logger.info(f"Fetched open orders: {open_orders}")
            
            # Validate response structure
            if not isinstance(open_orders, list):
                logger.error("Invalid response format from fetch_open_orders")
                return (
                    jsonify(
                        {
                            "error": "InvalidResponse",
                            "message": "Expected a list of orders.",
                        }
                    ),
                    500,
                )
            
            # Format orders for response
            result = []
            for order in open_orders:
                result.append(
                    {
                        "id": order.get("id"),
                        "symbol": order.get("symbol"),
                        "type": order.get("type"),
                        "side": order.get("side"),
                        "price": order.get("price"),
                        "amount": order.get("amount"),
                        "status": order.get("status"),
                        "datetime": order.get("datetime"),
                    }
                )
            
            return jsonify({"open_orders": result})
            
        except ccxt.AuthenticationError as e:
            logger.error(f"Authentication error fetching open orders: {e}")
            return jsonify({"error": "AuthenticationError", "message": str(e)}), 401
        except ccxt.BaseError as e:
            logger.error(f"CCXT error fetching open orders: {e}")
            return jsonify({"error": "CCXTError", "message": str(e)}), 502
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return jsonify({"error": "Exception", "message": str(e)}), 500