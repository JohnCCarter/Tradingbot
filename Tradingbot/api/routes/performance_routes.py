"""
Performance analysis routes for Tradingbot API.
Handles strategy performance analysis and statistics.
"""

import os
import json
import logging
from datetime import datetime
from flask import jsonify, request

logger = logging.getLogger(__name__)


def register_routes(app):
    """Register performance-related routes with Flask app"""
    
    @app.route("/strategy_performance", methods=["GET"])
    def strategy_performance():
        """Get strategy performance statistics"""
        log_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "order_status_log.txt")
        if not os.path.exists(log_path):
            return jsonify({"performance": {}, "trades": [], "status": "no_file"})
        
        # Get filter parameters
        symbol = request.args.get("symbol")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        
        # Detail level parameter
        detail_level = request.args.get(
            "detail_level", "standard"
        )  # standard, extended, full
        
        # Initialize statistics objects
        performance = {
            "total_trades": 0,
            "buys": 0,
            "sells": 0,
            "executed": 0,
            "cancelled": 0,
            "profit_loss": 0.0,
            "win_rate": 0.0,
            "avg_profit_per_trade": 0.0,
            "symbols": {},
            "daily_performance": {},
            # Extended statistics fields
            "highest_profit_trade": None,
            "highest_loss_trade": None,
            "avg_trade_duration": 0,
            "trade_frequency": 0,  # Trades per day
            "consecutive_wins": 0,
            "consecutive_losses": 0,
            "current_streak": 0,
            "risk_reward_ratio": 0.0,
            "trade_success_by_hour": {},  # Success rate by hour of day
        }
        
        trades = []
        parse_errors = []
        
        # For calculating trade pairs
        paired_trades = {}  # key: symbol, value: list of buy and sell trades
        
        # For tracking trade activity by hour
        hourly_trades = {}
        
        with open(log_path, "r") as f:
            for line in f:
                # Filter for order events
                if (
                    "EXECUTED" not in line
                    and "CANCELED" not in line
                    and "CANCELLED" not in line
                ):
                    continue
                
                # Parse order data
                try:
                    # Expected format: "YYYY-MM-DD HH:MM:SS: Order-ID: 123, Status: EXECUTED, Info: [...]"
                    match = line.split(": Order-ID:")
                    if not match or len(match) < 2:
                        parse_errors.append(
                            {"line": line, "error": "Could not split on 'Order-ID:'"}
                        )
                        continue
                    
                    date_part = match[0]  # YYYY-MM-DD HH:MM:SS
                    if not date_part or len(date_part) < 10:
                        parse_errors.append({"line": line, "error": "Invalid date format"})
                        continue
                    
                    date = date_part.split(" ")[0]  # YYYY-MM-DD
                    time_parts = date_part.split(" ")
                    hour = "00"
                    if len(time_parts) > 1 and ":" in time_parts[1]:
                        hour = time_parts[1].split(":")[0]
                    
                    # Track trading activity by hour
                    if hour not in hourly_trades:
                        hourly_trades[hour] = {
                            "total": 0,
                            "executed": 0,
                            "cancelled": 0,
                            "buys": 0,
                            "sells": 0,
                        }
                    
                    hourly_trades[hour]["total"] += 1
                    
                    # Apply date filters
                    if start_date and date < start_date:
                        continue
                    if end_date and date > end_date:
                        continue
                    
                    # Extract order ID and status
                    rest = match[1].split(", Status: ")
                    if len(rest) < 2:
                        parse_errors.append(
                            {"line": line, "error": "Could not split on 'Status:'"}
                        )
                        continue
                    
                    order_id = rest[0].strip()
                    status_part = rest[1].split(", Info: ")
                    if not status_part:
                        parse_errors.append(
                            {"line": line, "error": "Could not split on 'Info:'"}
                        )
                        continue
                    
                    status = status_part[0]
                    info = status_part[1] if len(status_part) > 1 else ""
                    
                    # Clean Python None to JSON null, and single to double quotes
                    cleaned_info = info.replace("None", "null").replace("'", '"')
                    
                    # Try parsing order info
                    try:
                        # Bitfinex format: symbol at index 3, type at 8, side at 6, price at 16, amount at 6
                        arr = json.loads(cleaned_info)
                        if not arr or not isinstance(arr, list):
                            parse_errors.append(
                                {"line": line, "error": "Could not parse JSON from info"}
                            )
                            continue
                        
                        order_symbol = "unknown"
                        if len(arr) > 3 and arr[3]:
                            symbol_match = arr[3].upper()
                            order_symbol = symbol_match
                        
                        # Apply symbol filter
                        if symbol and symbol.upper() not in order_symbol:
                            continue
                        
                        # Extract trade data
                        side = "buy" if len(arr) > 6 and float(arr[6] or 0) > 0 else "sell"
                        price = float(arr[16]) if len(arr) > 16 and arr[16] else 0.0
                        amount = abs(float(arr[6])) if len(arr) > 6 and arr[6] else 0.0
                        
                        # Ensure 'type' key exists
                        if len(arr) <= 8:
                            parse_errors.append(
                                {"line": line, "error": "Missing 'type' field in trade data"}
                            )
                            continue
                        
                        # Extract order type
                        order_type = arr[8] if arr[8] else "unknown"
                        
                        # Update statistics
                        performance["total_trades"] += 1
                        
                        if side == "buy":
                            performance["buys"] += 1
                            hourly_trades[hour]["buys"] += 1
                        else:
                            performance["sells"] += 1
                            hourly_trades[hour]["sells"] += 1
                        
                        if "EXECUTED" in status.upper():
                            performance["executed"] += 1
                            hourly_trades[hour]["executed"] += 1
                        elif "CANCELED" in status.upper() or "CANCELLED" in status.upper():
                            performance["cancelled"] += 1
                            hourly_trades[hour]["cancelled"] += 1
                        
                        # Track performance by symbol
                        if order_symbol not in performance["symbols"]:
                            performance["symbols"][order_symbol] = {
                                "trades": 0,
                                "buys": 0,
                                "sells": 0,
                                "volume": 0.0,
                                "executed": 0,
                                "cancelled": 0,
                                "avg_buy_price": 0.0,
                                "avg_sell_price": 0.0,
                                "total_buy_value": 0.0,
                                "total_sell_value": 0.0,
                                "profit_loss": 0.0,
                            }
                        
                        symbol_stats = performance["symbols"][order_symbol]
                        symbol_stats["trades"] += 1
                        symbol_stats["volume"] += amount * price
                        
                        if side == "buy":
                            symbol_stats["buys"] += 1
                            if "EXECUTED" in status.upper():
                                symbol_stats["total_buy_value"] += amount * price
                                if symbol_stats["buys"] > 0:
                                    symbol_stats["avg_buy_price"] = (
                                        symbol_stats["total_buy_value"]
                                        / symbol_stats["buys"]
                                    )
                        else:
                            symbol_stats["sells"] += 1
                            if "EXECUTED" in status.upper():
                                symbol_stats["total_sell_value"] += amount * price
                                if symbol_stats["sells"] > 0:
                                    symbol_stats["avg_sell_price"] = (
                                        symbol_stats["total_sell_value"]
                                        / symbol_stats["sells"]
                                    )
                        
                        if "EXECUTED" in status.upper():
                            symbol_stats["executed"] += 1
                        elif "CANCELED" in status.upper() or "CANCELLED" in status.upper():
                            symbol_stats["cancelled"] += 1
                        
                        # Calculate profit/loss by symbol
                        if symbol_stats["buys"] > 0 and symbol_stats["sells"] > 0:
                            symbol_stats["profit_loss"] = (
                                symbol_stats["total_sell_value"]
                                - symbol_stats["total_buy_value"]
                            )
                        
                        # Track daily performance
                        if date not in performance["daily_performance"]:
                            performance["daily_performance"][date] = {
                                "trades": 0,
                                "buys": 0,
                                "sells": 0,
                                "volume": 0.0,
                                "executed": 0,
                                "cancelled": 0,
                            }
                        
                        daily_stats = performance["daily_performance"][date]
                        daily_stats["trades"] += 1
                        daily_stats["volume"] += amount * price
                        
                        if side == "buy":
                            daily_stats["buys"] += 1
                        else:
                            daily_stats["sells"] += 1
                        
                        if "EXECUTED" in status.upper():
                            daily_stats["executed"] += 1
                        elif "CANCELED" in status.upper() or "CANCELLED" in status.upper():
                            daily_stats["cancelled"] += 1
                        
                        # Track trade pairs for more accurate P&L analysis
                        if "EXECUTED" in status.upper():
                            if order_symbol not in paired_trades:
                                paired_trades[order_symbol] = []
                            
                            paired_trades[order_symbol].append(
                                {
                                    "time": date_part,
                                    "order_id": order_id,
                                    "side": side,
                                    "price": price,
                                    "amount": amount,
                                    "value": price * amount,
                                    "status": status,
                                }
                            )
                        
                        # Create trade object for frontend
                        trade = {
                            "date": date,
                            "time": date_part,
                            "order_id": order_id,
                            "symbol": order_symbol,
                            "side": side,
                            "type": order_type,
                            "price": price,
                            "amount": amount,
                            "value": price * amount,
                            "status": status,
                        }
                        
                        # Track highest profit/loss trades
                        if "EXECUTED" in status.upper():
                            if side == "sell" and (
                                not performance["highest_profit_trade"]
                                or trade["value"]
                                > performance["highest_profit_trade"]["value"]
                            ):
                                performance["highest_profit_trade"] = trade
                            
                            if side == "buy" and (
                                not performance["highest_loss_trade"]
                                or trade["value"]
                                > performance["highest_loss_trade"]["value"]
                            ):
                                performance["highest_loss_trade"] = trade
                        
                        # Validate parsed trade data
                        if not order_symbol or price <= 0 or amount <= 0:
                            logger.warning(
                                f"Invalid trade data: symbol={order_symbol}, price={price}, amount={amount}"
                            )
                            parse_errors.append(
                                {"line": line, "error": "Invalid trade data"}
                            )
                            continue
                        
                        # Add trade to list if valid
                        trades.append(trade)
                        
                    except Exception as e:
                        logger.error(f"Error parsing order info: {e}")
                        parse_errors.append(
                            {
                                "line": line,
                                "error": f"Error parsing order info: {str(e)}",
                            }
                        )
                        continue
                    
                except Exception as e:
                    logger.error(f"Error processing order line: {e}")
                    parse_errors.append(
                        {
                            "line": line,
                            "error": f"Error processing order line: {str(e)}",
                        }
                    )
                    continue
        
        # Calculate trading frequency
        if performance["daily_performance"]:
            num_days = len(performance["daily_performance"])
            if num_days > 0:
                performance["trade_frequency"] = performance["total_trades"] / num_days
        
        # Track trading success by hour
        for hour, stats in hourly_trades.items():
            if stats["total"] > 0:
                performance["trade_success_by_hour"][hour] = {
                    "total": stats["total"],
                    "executed": stats["executed"],
                    "cancelled": stats["cancelled"],
                    "buys": stats["buys"],
                    "sells": stats["sells"],
                    "success_rate": (
                        (stats["executed"] / stats["total"]) if stats["total"] > 0 else 0
                    ),
                }
        
        # Calculate profit/loss and win rate based on buy and sell pairs
        if performance["buys"] > 0 and performance["sells"] > 0:
            # Enhanced P&L calculation based on matched buy/sell pairs
            total_profit_loss = 0
            for symbol, symbol_trades in paired_trades.items():
                buy_trades = [t for t in symbol_trades if t["side"] == "buy"]
                sell_trades = [t for t in symbol_trades if t["side"] == "sell"]
                
                # Simple FIFO method to match buys and sells
                remaining_buys = buy_trades.copy()
                for sell in sell_trades:
                    sell_amount = sell["amount"]
                    sell_value = sell["value"]
                    
                    while sell_amount > 0 and remaining_buys:
                        buy = remaining_buys[0]
                        used_amount = min(buy["amount"], sell_amount)
                        buy_price_per_unit = buy["price"]
                        sell_price_per_unit = sell["price"]
                        
                        # Calculate P&L for this portion of transaction
                        pl_per_unit = sell_price_per_unit - buy_price_per_unit
                        pl_for_amount = pl_per_unit * used_amount
                        total_profit_loss += pl_for_amount
                        
                        # Update remaining amounts
                        sell_amount -= used_amount
                        buy["amount"] -= used_amount
                        
                        if buy["amount"] <= 0:
                            remaining_buys.pop(0)
            
            performance["profit_loss"] = total_profit_loss
            performance["win_rate"] = (
                total_profit_loss > 0
            ) * 100  # Simple win rate based on total P&L
            
            if performance["executed"] > 0:
                performance["avg_profit_per_trade"] = (
                    total_profit_loss / performance["executed"]
                )
        
        # Sort trades chronologically
        trades.sort(key=lambda x: x["time"])
        
        # Convert daily_performance from dict to list for easier frontend use
        daily_performance_list = []
        for date, stats in performance["daily_performance"].items():
            daily_performance_list.append(
                {
                    "date": date,
                    "trades": stats["trades"],
                    "buys": stats["buys"],
                    "sells": stats["sells"],
                    "volume": stats["volume"],
                    "executed": stats["executed"],
                    "cancelled": stats["cancelled"],
                }
            )
        
        # Sort daily_performance chronologically
        daily_performance_list.sort(key=lambda x: x["date"])
        performance["daily_performance"] = daily_performance_list
        
        # Prepare response based on detail level
        response_data = {"performance": performance, "status": "ok"}
        
        # Include trades based on detail level
        if detail_level in ["standard", "extended", "full"]:
            response_data["trades"] = trades[-100:]  # Limit to latest 100 trades for standard
        
        # Add debug data for more detailed levels
        if detail_level in ["extended", "full"]:
            response_data["hourly_stats"] = performance["trade_success_by_hour"]
            response_data["paired_trades_summary"] = {
                symbol: {
                    "buys": len([t for t in trades if t["side"] == "buy"]),
                    "sells": len([t for t in trades if t["side"] == "sell"]),
                }
                for symbol, trades in paired_trades.items()
            }
        
        # Add full debug data
        if detail_level == "full":
            response_data["parse_errors"] = parse_errors
            response_data["all_trades"] = trades  # All trades without limit
        
        # Return performance data
        return jsonify(response_data)