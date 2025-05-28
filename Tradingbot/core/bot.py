"""
Main Tradingbot implementation.
Contains the TradingBot class with core functionality.
"""

import os
import json
import time
import numpy as np
import logging
import traceback
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from Tradingbot.utils.indicators import calculate_indicators
from Tradingbot.data.market_data import fetch_market_data, get_current_price, ensure_paper_trading_symbol
from Tradingbot.core.exchange import place_order, fetch_balance, get_open_orders


class TradingBot:
    """Main trading bot implementation"""
    
    def __init__(self, config_file="config.json"):
        """
        Initialize trading bot with configuration from a JSON file.
        
        Args:
            config_file: Path to the configuration file
        """
        logger = logging.getLogger("TradingBot")
        logger.info("Initializing TradingBot")
        try:
            # Read configuration
            self.config_file = config_file
            with open(config_file, "r") as f:
                self.config = json.load(f)

            # Set API keys and secrets
            self.api_key = self.config.get("api_key", "")
            self.api_secret = self.config.get("api_secret", "")

            # Set default values
            self.base_url = self.config.get("base_url", "https://api.example.com")
            self.symbols = self.config.get("symbols", ["tTESTBTC:TESTUSD"])
            self.default_symbol = (
                self.symbols[0] if self.symbols else "tTESTBTC:TESTUSD"
            )
            self.running = False
            self.log_file = "order_status_log.txt"

            # Strategy parameters
            self.strategy_params = self.config.get("strategy", {})
            self.strategy_type = self.strategy_params.get("type", "simple")

            # Performance data
            self.performance_data = {}

            logger.info(f"TradingBot initialized with strategy: {self.strategy_type}")
        except Exception as e:
            logger.error(f"Error initializing TradingBot: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def start(self):
        """Start the trading bot"""
        logger = logging.getLogger("TradingBot")
        logger.info("Starting TradingBot")
        self.running = True
        return {"status": "started"}

    def stop(self):
        """Stop the trading bot"""
        logger = logging.getLogger("TradingBot")
        logger.info("Stopping TradingBot")
        self.running = False
        return {"status": "stopped"}

    def get_status(self):
        """Get current bot status"""
        status = "running" if self.running else "stopped"
        return {"status": status}

    def get_balance(self, exchange):
        """
        Get account balance from the exchange.
        
        Args:
            exchange: Exchange instance
        
        Returns:
            dict: Account balance or error message
        """
        logger = logging.getLogger("TradingBot")
        logger.info("Getting account balance")
        try:
            return fetch_balance(exchange)
        except Exception as e:
            logger.error(f"Error getting balance: {str(e)}")
            return {"error": str(e)}

    def get_ticker(self, exchange, symbol=None):
        """
        Get current price for a symbol.
        
        Args:
            exchange: Exchange instance
            symbol: Trading symbol (optional)
        
        Returns:
            dict: Ticker information
        """
        if symbol is None:
            symbol = self.default_symbol

        logger = logging.getLogger("TradingBot")
        logger.info(f"Getting ticker for {symbol}")

        try:
            # Simulate API call for ticker data
            # In a real implementation, this would call the exchange's API
            prices = {
                "tTESTBTC:TESTUSD": 50000 + np.random.normal(0, 500),
                "tTESTETH:TESTUSD": 3000 + np.random.normal(0, 50),
                "tTESTLTC:TESTUSD": 200 + np.random.normal(0, 5),
            }

            price = get_current_price(exchange, symbol)
            return {
                "symbol": symbol,
                "last_price": price,
                "bid": price - 10,
                "ask": price + 10,
                "daily_change": np.random.normal(0, 0.02),
                "volume": 1000 + np.random.normal(0, 100),
            }
        except Exception as e:
            logger.error(f"Error getting ticker for {symbol}: {str(e)}")
            return {"error": str(e)}

    def place_order(self, exchange, structured_logger, symbol=None, order_type=None, amount=None, price=None):
        """
        Place an order on the exchange.
        
        Args:
            exchange: Exchange instance
            structured_logger: Structured logger instance
            symbol: Trading symbol
            order_type: 'buy' or 'sell'
            amount: Amount to buy/sell
            price: Price (optional, for limit orders)
        
        Returns:
            dict: Order information or error message
        """
        logger = logging.getLogger("TradingBot")
        
        if symbol is None:
            symbol = self.default_symbol

        if order_type not in ["buy", "sell"]:
            return {"error": "Invalid order type. Use 'buy' or 'sell'."}

        if amount is None:
            return {"error": "Amount must be specified."}

        logger.info(
            f"Placing order: {order_type} {amount} {symbol} @ {price or 'market price'}"
        )

        try:
            # Place order using the exchange module
            order = place_order(exchange, structured_logger, order_type, symbol, amount, price)
            if order is None:
                return {"error": "Failed to place order"}
                
            return order

        except Exception as e:
            error_msg = f"Error placing order: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {"error": error_msg}

    def _log_order(self, order_info):
        """
        Log order information to a file.
        
        Args:
            order_info: Order information
        """
        logger = logging.getLogger("TradingBot")
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(order_info) + "\n")
        except Exception as e:
            logger.error(f"Error logging order: {str(e)}")

    def get_orders(self, symbol=None, start_date=None, end_date=None):
        """
        Get historical orders.
        
        Args:
            symbol: Filter by symbol
            start_date: Filter from this date (ISO format)
            end_date: Filter to this date (ISO format)
        
        Returns:
            list: List of orders
        """
        logger = logging.getLogger("TradingBot")
        logger.info(
            f"Getting orders with filter - symbol: {symbol}, start_date: {start_date}, end_date: {end_date}"
        )

        try:
            orders = []
            if os.path.exists(self.log_file):
                with open(self.log_file, "r") as f:
                    for line in f:
                        try:
                            order = json.loads(line.strip())

                            # Apply filters
                            if symbol and order.get("symbol") != symbol:
                                continue

                            order_date = datetime.fromisoformat(order.get("timestamp"))

                            if start_date:
                                start = datetime.fromisoformat(start_date)
                                if order_date < start:
                                    continue

                            if end_date:
                                end = datetime.fromisoformat(end_date)
                                if order_date > end:
                                    continue

                            orders.append(order)
                        except json.JSONDecodeError:
                            logger.warning(f"Could not parse order line: {line}")
                        except Exception as e:
                            logger.error(f"Error processing order line: {str(e)}")

            # Sort by timestamp (newest first)
            orders.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return orders

        except Exception as e:
            error_msg = f"Error getting orders: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_open_orders(self, exchange):
        """
        Get open orders from the exchange.
        
        Args:
            exchange: Exchange instance
        
        Returns:
            list: List of open orders or error message
        """
        logger = logging.getLogger("TradingBot")
        logger.info("Getting open orders")

        try:
            return get_open_orders(exchange, logger)
        except Exception as e:
            error_msg = f"Error getting open orders: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_logs(self, limit=10):
        """
        Get the latest logs.
        
        Args:
            limit: Number of log lines to get
        
        Returns:
            list: List of log messages
        """
        logger = logging.getLogger("TradingBot")
        logger.info(f"Getting latest {limit} logs")

        try:
            logs = []
            # In a real implementation, this would read from a log file
            logs.append(
                {"timestamp": datetime.now().isoformat(), "message": "Bot started"}
            )
            logs.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "message": "API connection established",
                }
            )
            return logs
        except Exception as e:
            error_msg = f"Error getting logs: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_config(self):
        """
        Get current configuration.
        
        Returns:
            dict: Configuration
        """
        logger = logging.getLogger("TradingBot")
        logger.info("Getting configuration")

        try:
            return self.config
        except Exception as e:
            error_msg = f"Error getting configuration: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def update_config(self, new_config):
        """
        Update configuration.
        
        Args:
            new_config: New configuration as a dictionary
        
        Returns:
            dict: Update status
        """
        logger = logging.getLogger("TradingBot")
        logger.info("Updating configuration")

        try:
            # Update configuration object
            self.config.update(new_config)

            # Save to file
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)

            return {"status": "success", "message": "Configuration updated"}
        except Exception as e:
            error_msg = f"Error updating configuration: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_price_history(self, exchange, symbol=None, timeframe="1h", limit=100):
        """
        Get historical price data.
        
        Args:
            exchange: Exchange instance
            symbol: Trading symbol
            timeframe: Timeframe ('1m', '5m', '15m', '30m', '1h', '3h', '6h', '12h', '1d', '1w')
            limit: Number of candles to fetch
        
        Returns:
            list: List of price data points
        """
        if symbol is None:
            symbol = self.default_symbol

        logger = logging.getLogger("TradingBot")
        logger.info(
            f"Getting price history for {symbol}, timeframe {timeframe}, limit {limit}"
        )

        try:
            # Fetch historical data using the market data module
            data = fetch_market_data(exchange, symbol, timeframe, limit)
            if data is None or data.empty:
                return {"error": "Failed to fetch historical data"}
                
            # Convert to list for API response
            result = data.reset_index().to_dict(orient="records")
            return result

        except Exception as e:
            error_msg = f"Error getting price history: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def analyze_strategy_performance(
        self, symbol=None, start_date=None, end_date=None, debug=False
    ):
        """
        Analyze strategy performance based on order history.
        
        Args:
            symbol: Filter by symbol
            start_date: Filter from this date
            end_date: Filter to this date
            debug: Include debug information
        
        Returns:
            dict: Performance analysis
        """
        logger = logging.getLogger("TradingBot")
        logger.info(
            f"Analyzing strategy performance with filter - symbol: {symbol}, start_date: {start_date}, end_date: {end_date}"
        )

        try:
            # Get order history
            orders = self.get_orders(symbol, start_date, end_date)
            if isinstance(orders, dict) and "error" in orders:
                return orders

            # Statistics object to store results
            stats = {
                "total_trades": len(orders),
                "total_buys": 0,
                "total_sells": 0,
                "executed": 0,
                "cancelled": 0,
                "profit_loss": 0.0,
                "symbols": {},
                "daily_performance": {},
                "hourly_distribution": {},
                "weekly_distribution": {
                    0: 0,
                    1: 0,
                    2: 0,
                    3: 0,
                    4: 0,
                    5: 0,
                    6: 0,
                },  # Mon-Sun
                "executed_orders": [],
                "cancelled_orders": [],
                "avg_buy_price": 0,
                "avg_sell_price": 0,
                "win_trades": 0,
                "loss_trades": 0,
                "break_even_trades": 0,
                "longest_win_streak": 0,
                "longest_loss_streak": 0,
                "current_streak_type": None,  # 'win' or 'loss'
                "current_streak_count": 0,
                "avg_profit_per_trade": 0,
                "max_profit_trade": 0,
                "max_loss_trade": 0,
                "total_volume": 0,
                "risk_reward_ratio": 0,
            }

            # Debug statistics
            debug_stats = {
                "total_lines_processed": len(orders),
                "lines_filtered": 0,
                "parse_errors": 0,
                "debug_messages": [],
            }

            if not orders:
                if debug:
                    return {"stats": stats, "debug": debug_stats}
                return stats

            buy_prices = []
            sell_prices = []
            daily_trades = {}
            daily_profit_loss = {}

            prev_pair = None  # To track pairs of buy-sell
            pairs = []  # To track complete pairs

            current_streak = 0
            current_streak_type = None
            max_win_streak = 0
            max_loss_streak = 0

            profits = []
            losses = []

            try:
                for order in orders:
                    # Basic statistics
                    order_type = order.get("type")
                    status = order.get("status")
                    symbol = order.get("symbol")
                    price = float(order.get("price", 0))
                    amount = float(order.get("amount", 0))
                    value = price * amount

                    # Update symbol statistics
                    if symbol not in stats["symbols"]:
                        stats["symbols"][symbol] = {
                            "trades": 0,
                            "buys": 0,
                            "sells": 0,
                            "executed": 0,
                            "cancelled": 0,
                            "volume": 0,
                            "profit_loss": 0,
                        }

                    stats["symbols"][symbol]["trades"] += 1
                    stats["symbols"][symbol]["volume"] += value
                    stats["total_volume"] += value

                    # Update type statistics
                    if order_type == "buy":
                        stats["total_buys"] += 1
                        stats["symbols"][symbol]["buys"] += 1
                        if status == "executed":
                            buy_prices.append(price)
                    elif order_type == "sell":
                        stats["total_sells"] += 1
                        stats["symbols"][symbol]["sells"] += 1
                        if status == "executed":
                            sell_prices.append(price)

                    # Update status statistics
                    if status == "executed":
                        stats["executed"] += 1
                        stats["symbols"][symbol]["executed"] += 1
                        stats["executed_orders"].append(order)
                    elif status == "cancelled":
                        stats["cancelled"] += 1
                        stats["symbols"][symbol]["cancelled"] += 1
                        stats["cancelled_orders"].append(order)

                    # Time distribution analysis
                    try:
                        timestamp = datetime.fromisoformat(order.get("timestamp"))

                        # Daily statistics
                        day_key = timestamp.strftime("%Y-%m-%d")
                        if day_key not in daily_trades:
                            daily_trades[day_key] = {
                                "buys": 0,
                                "sells": 0,
                                "executed": 0,
                                "cancelled": 0,
                            }
                            daily_profit_loss[day_key] = 0

                        daily_trades[day_key][order_type + "s"] += 1
                        if status == "executed":
                            daily_trades[day_key]["executed"] += 1
                        elif status == "cancelled":
                            daily_trades[day_key]["cancelled"] += 1

                        # Weekday analysis
                        weekday = timestamp.weekday()  # 0 = Monday, 6 = Sunday
                        stats["weekly_distribution"][weekday] += 1

                        # Hour analysis
                        hour = timestamp.hour
                        if hour not in stats["hourly_distribution"]:
                            stats["hourly_distribution"][hour] = 0
                        stats["hourly_distribution"][hour] += 1

                    except Exception as e:
                        error_msg = f"Error analyzing timestamp: {str(e)}"
                        logger.error(error_msg)
                        debug_stats["debug_messages"].append(error_msg)

                    # Track buy-sell pairs for P&L calculations
                    if status == "executed":
                        if not prev_pair:
                            prev_pair = order
                        else:
                            # We have a potential pair
                            if (
                                prev_pair.get("type") == "buy" and order_type == "sell"
                            ) or (
                                prev_pair.get("type") == "sell" and order_type == "buy"
                            ):
                                # Calculate P&L
                                if prev_pair.get("type") == "buy":
                                    buy_order = prev_pair
                                    sell_order = order
                                else:
                                    sell_order = prev_pair
                                    buy_order = order

                                buy_price = float(buy_order.get("price", 0))
                                sell_price = float(sell_order.get("price", 0))
                                trade_amount = min(
                                    float(buy_order.get("amount", 0)),
                                    float(sell_order.get("amount", 0)),
                                )

                                # P&L for this pair
                                pair_pl = (sell_price - buy_price) * trade_amount
                                stats["profit_loss"] += pair_pl
                                stats["symbols"][symbol]["profit_loss"] += pair_pl

                                # Update daily P&L
                                sell_day = datetime.fromisoformat(
                                    sell_order.get("timestamp")
                                ).strftime("%Y-%m-%d")
                                if sell_day in daily_profit_loss:
                                    daily_profit_loss[sell_day] += pair_pl

                                # Track win/loss and streaks
                                if pair_pl > 0:
                                    stats["win_trades"] += 1
                                    profits.append(pair_pl)

                                    if current_streak_type == "win":
                                        current_streak += 1
                                    else:
                                        current_streak = 1
                                        current_streak_type = "win"

                                    if current_streak > max_win_streak:
                                        max_win_streak = current_streak

                                elif pair_pl < 0:
                                    stats["loss_trades"] += 1
                                    losses.append(pair_pl)

                                    if current_streak_type == "loss":
                                        current_streak += 1
                                    else:
                                        current_streak = 1
                                        current_streak_type = "loss"

                                    if current_streak > max_loss_streak:
                                        max_loss_streak = current_streak

                                else:
                                    stats["break_even_trades"] += 1

                                # Save the pair
                                pairs.append(
                                    {
                                        "buy_order": buy_order,
                                        "sell_order": sell_order,
                                        "profit_loss": pair_pl,
                                        "trade_amount": trade_amount,
                                    }
                                )

                                # Reset for next pair
                                prev_pair = None
                            else:
                                # Same type in a row, replace previous
                                prev_pair = order

            except Exception as e:
                error_msg = f"Error during order analysis: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                debug_stats["debug_messages"].append(error_msg)

            # Calculate averages and more advanced statistics
            stats["avg_buy_price"] = (
                sum(buy_prices) / len(buy_prices) if buy_prices else 0
            )
            stats["avg_sell_price"] = (
                sum(sell_prices) / len(sell_prices) if sell_prices else 0
            )

            # Win statistics
            if stats["win_trades"] + stats["loss_trades"] > 0:
                stats["win_rate"] = stats["win_trades"] / (
                    stats["win_trades"] + stats["loss_trades"]
                )
            else:
                stats["win_rate"] = 0

            # Average profit per trade
            if len(pairs) > 0:
                stats["avg_profit_per_trade"] = stats["profit_loss"] / len(pairs)

            # Risk/reward ratio
            if profits and losses:
                avg_profit = sum(profits) / len(profits) if len(profits) > 0 else 0
                avg_loss = abs(sum(losses) / len(losses)) if len(losses) > 0 else 0
                stats["risk_reward_ratio"] = (
                    avg_profit / avg_loss if avg_loss > 0 else 0
                )
                stats["max_profit_trade"] = max(profits) if profits else 0
                stats["max_loss_trade"] = min(losses) if losses else 0

            # Execution rate
            stats["execution_rate"] = (
                stats["executed"] / stats["total_trades"]
                if stats["total_trades"] > 0
                else 0
            )
            stats["cancellation_rate"] = (
                stats["cancelled"] / stats["total_trades"]
                if stats["total_trades"] > 0
                else 0
            )

            # Buy/Sell ratio
            stats["buy_sell_ratio"] = (
                stats["total_buys"] / stats["total_sells"]
                if stats["total_sells"] > 0
                else 0
            )

            # Streak lengths
            stats["longest_win_streak"] = max_win_streak
            stats["longest_loss_streak"] = max_loss_streak
            stats["current_streak_type"] = current_streak_type
            stats["current_streak_count"] = current_streak

            # Format daily performance data
            stats["daily_performance"] = []
            for day, day_stats in daily_trades.items():
                stats["daily_performance"].append(
                    {
                        "date": day,
                        "trades": day_stats["buys"] + day_stats["sells"],
                        "buys": day_stats["buys"],
                        "sells": day_stats["sells"],
                        "executed": day_stats["executed"],
                        "cancelled": day_stats["cancelled"],
                        "profit_loss": daily_profit_loss.get(day, 0),
                    }
                )

            # Sort daily performance data by date
            stats["daily_performance"].sort(key=lambda x: x["date"])

            # Add recent trades
            stats["recent_trades"] = orders[: min(10, len(orders))]

            if debug:
                return {"stats": stats, "debug": debug_stats}
            return stats

        except Exception as e:
            error_msg = f"Error analyzing strategy performance: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())

            if debug:
                debug_stats["debug_messages"].append(error_msg)
                debug_stats["debug_messages"].append(traceback.format_exc())
                return {"error": error_msg, "debug": debug_stats}

            return {"error": error_msg}

    def execute_strategy(self, exchange, structured_logger):
        """
        Execute trading strategy based on configuration parameters.
        
        Args:
            exchange: Exchange instance
            structured_logger: Structured logger instance
        
        Returns:
            dict: Strategy execution result
        """
        if not self.running:
            return {"status": "stopped", "message": "Bot is not running"}

        strategy_type = self.strategy_params.get("type", "simple")

        if strategy_type == "simple":
            return self._execute_simple_strategy(exchange, structured_logger)
        elif strategy_type == "moving_average":
            return self._execute_ma_strategy(exchange, structured_logger)
        else:
            return {"error": f"Unknown strategy type: {strategy_type}"}

    def _execute_simple_strategy(self, exchange, structured_logger):
        """
        Execute simple trading strategy based on random price points.
        
        Args:
            exchange: Exchange instance
            structured_logger: Structured logger instance
        
        Returns:
            dict: Strategy execution result
        """
        logger = logging.getLogger("TradingBot")
        logger.info("Executing simple strategy")

        try:
            symbol = self.strategy_params.get("symbol", self.default_symbol)

            # Get current price
            ticker = self.get_ticker(exchange, symbol)
            if isinstance(ticker, dict) and "error" in ticker:
                return ticker

            current_price = ticker["last_price"]

            # Random decision for demonstration
            decision = np.random.choice(["buy", "sell", "hold"], p=[0.3, 0.3, 0.4])

            if decision == "hold":
                logger.info(f"Strategy decision: HOLD at {current_price}")
                return {
                    "action": "hold",
                    "price": current_price,
                    "reason": "Price level indicates we should hold the position",
                }

            # Determine amount
            amount = self.strategy_params.get("amount", 0.001)

            # Place order
            order_result = self.place_order(
                exchange, structured_logger, symbol=symbol, order_type=decision, amount=amount, price=current_price
            )

            return {
                "action": decision,
                "price": current_price,
                "amount": amount,
                "result": order_result,
                "reason": f"Executed {decision} based on current price level",
            }

        except Exception as e:
            error_msg = f"Error executing simple strategy: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {"error": error_msg}

    def _execute_ma_strategy(self, exchange, structured_logger):
        """
        Execute a moving average-based trading strategy.
        
        Args:
            exchange: Exchange instance
            structured_logger: Structured logger instance
        
        Returns:
            dict: Strategy execution result
        """
        logger = logging.getLogger("TradingBot")
        logger.info("Executing moving average strategy")

        try:
            symbol = self.strategy_params.get("symbol", self.default_symbol)
            short_period = self.strategy_params.get("short_ma", 10)
            long_period = self.strategy_params.get("long_ma", 30)

            # Get historical data
            history = self.get_price_history(exchange, symbol, timeframe="1h", limit=long_period + 10)
            if isinstance(history, dict) and "error" in history:
                return history

            # Extract prices from history
            prices = [candle["close"] for candle in history]

            if len(prices) < long_period:
                return {
                    "error": f"Insufficient price history for MA strategy. Need at least {long_period} points."
                }

            # Calculate moving averages
            short_ma = sum(prices[-short_period:]) / short_period
            long_ma = sum(prices[-long_period:]) / long_period

            current_price = prices[-1]

            # Decision logic
            if short_ma > long_ma:
                decision = "buy"
                reason = f"Short MA ({short_ma:.2f}) higher than long MA ({long_ma:.2f})"
            else:
                decision = "sell"
                reason = f"Short MA ({short_ma:.2f}) lower than long MA ({long_ma:.2f})"

            # Determine amount
            amount = self.strategy_params.get("amount", 0.001)

            # Random decision to execute or not for demo
            if np.random.random() < 0.7:  # 70% chance to execute
                # Place order
                order_result = self.place_order(
                    exchange, structured_logger, symbol=symbol, order_type=decision, amount=amount, price=current_price
                )

                executed = True
            else:
                order_result = {
                    "status": "simulated",
                    "message": "Order simulated but not executed",
                }
                executed = False

            return {
                "action": decision,
                "executed": executed,
                "price": current_price,
                "amount": amount,
                "short_ma": short_ma,
                "long_ma": long_ma,
                "result": order_result,
                "reason": reason,
            }

        except Exception as e:
            error_msg = f"Error executing MA strategy: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {"error": error_msg}

    def send_email_notification(self, subject, body):
        """
        Send email notification.
        
        Args:
            subject: Email subject
            body: Email body
        
        Returns:
            bool: Success or failure
        """
        logger = logging.getLogger("TradingBot")
        
        # Check if email notifications are enabled
        if not self.config.get("EMAIL_NOTIFICATIONS", False):
            logger.info("[EMAIL] Email notifications are disabled (EMAIL_NOTIFICATIONS=False).")
            return False
            
        # Get email settings
        smtp_server = self.config.get("EMAIL_SMTP_SERVER", "smtp.gmail.com")
        smtp_port = self.config.get("EMAIL_SMTP_PORT", 465)
        sender = self.config.get("EMAIL_SENDER", "")
        receiver = self.config.get("EMAIL_RECEIVER", "")
        password = self.config.get("EMAIL_PASSWORD", "")
        
        # Override from environment if set
        sender = os.getenv("EMAIL_SENDER", sender)
        receiver = os.getenv("EMAIL_RECEIVER", receiver)
        password = os.getenv("EMAIL_PASSWORD", password)
        
        # Check required fields
        required = [sender, receiver, password]
        if not all(required):
            logger.warning(
                "[EMAIL] Email settings missing (sender, receiver, or password). No email sent."
            )
            return False
            
        try:
            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = receiver
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            
            # Use SMTP_SSL for Gmail (port 465)
            with smtplib.SMTP_SSL(smtp_server, int(smtp_port)) as server:
                server.login(sender, password)
                server.send_message(msg)
                
            logger.info("[EMAIL] Email sent via Gmail SMTP_SSL!")
            return True
            
        except Exception as e:
            logger.error(f"[EMAIL] Failed to send email: {e}")
            return False