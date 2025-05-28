"""
Performance Analysis Module

This module contains functions for analyzing the performance of trading strategies,
calculating statistics, and visualizing results.
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Dict, List, Optional, Tuple, Union, Any

# Set up logging
logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """Class for analyzing trading strategy performance"""
    
    def __init__(self, log_file="order_status_log.txt"):
        """
        Initialize the performance analyzer
        
        Parameters:
        log_file (str): Path to the order log file
        """
        self.log_file = log_file
        logger.info(f"Initialized PerformanceAnalyzer with log file: {log_file}")
    
    def load_trades(self, symbol=None, start_date=None, end_date=None) -> List[Dict]:
        """
        Load trades from the log file with optional filtering
        
        Parameters:
        symbol (str): Filter by trading symbol
        start_date (str): Filter trades after this date (YYYY-MM-DD)
        end_date (str): Filter trades before this date (YYYY-MM-DD)
        
        Returns:
        List[Dict]: List of trade data dictionaries
        """
        trades = []
        parse_errors = []
        
        if not os.path.exists(self.log_file):
            logger.error(f"Log file not found: {self.log_file}")
            return trades
        
        try:
            with open(self.log_file, "r") as f:
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
                        # Extract timestamp
                        date_match = line.split(": Order-ID:")
                        if not date_match or len(date_match) < 2:
                            parse_errors.append(
                                {"line": line, "error": "Could not split on 'Order-ID:'"}
                            )
                            continue
                        
                        date_part = date_match[0]  # YYYY-MM-DD HH:MM:SS
                        if not date_part or len(date_part) < 10:
                            parse_errors.append({"line": line, "error": "Invalid date format"})
                            continue
                        
                        # Parse date
                        trade_date = date_part.split(" ")[0]  # YYYY-MM-DD
                        
                        # Filter by date range
                        if start_date and trade_date < start_date:
                            continue
                        if end_date and trade_date > end_date:
                            continue
                        
                        # Extract order ID and status
                        rest = date_match[1].split(", Status:")
                        if not rest:
                            parse_errors.append(
                                {"line": line, "error": "Could not split on 'Status:'"}
                            )
                            continue
                        
                        order_id = rest[0].strip()
                        status_parts = rest[1].split(", Info:")
                        if not status_parts:
                            parse_errors.append(
                                {"line": line, "error": "Could not split on 'Info:'"}
                            )
                            continue
                        
                        status = status_parts[0].strip()
                        info = status_parts[1] if len(status_parts) > 1 else ""
                        
                        # Clean info string for JSON parsing
                        cleaned_info = info.replace("None", "null").replace("'", '"')
                        
                        # Parse order info
                        try:
                            arr = json.loads(cleaned_info)
                            if not arr or not isinstance(arr, list):
                                parse_errors.append(
                                    {"line": line, "error": "Could not parse JSON from info"}
                                )
                                continue
                            
                            # Extract trade data
                            trade_symbol = arr[3].upper() if len(arr) > 3 and arr[3] else "UNKNOWN"
                            
                            # Filter by symbol if provided
                            if symbol and symbol.upper() not in trade_symbol:
                                continue
                            
                            # Get trade details
                            side = "buy" if len(arr) > 6 and float(arr[6] or 0) > 0 else "sell"
                            price = float(arr[16]) if len(arr) > 16 and arr[16] else 0.0
                            amount = abs(float(arr[6])) if len(arr) > 6 and arr[6] else 0.0
                            order_type = arr[8] if len(arr) > 8 and arr[8] else "unknown"
                            
                            # Create trade object
                            trade = {
                                "date": trade_date,
                                "time": date_part,
                                "order_id": order_id,
                                "symbol": trade_symbol,
                                "side": side,
                                "type": order_type,
                                "price": price,
                                "amount": amount,
                                "value": price * amount,
                                "status": status,
                            }
                            
                            trades.append(trade)
                            
                        except json.JSONDecodeError:
                            parse_errors.append(
                                {"line": line, "error": "JSON parsing error in order info"}
                            )
                        except Exception as e:
                            parse_errors.append(
                                {"line": line, "error": f"Error processing order info: {str(e)}"}
                            )
                            
                    except Exception as e:
                        parse_errors.append({"line": line, "error": f"General parsing error: {str(e)}"})
            
            # Log parse errors
            if parse_errors:
                logger.warning(f"Encountered {len(parse_errors)} parsing errors")
                for error in parse_errors[:5]:  # Log first 5 errors
                    logger.debug(f"Parse error: {error}")
                if len(parse_errors) > 5:
                    logger.debug(f"... and {len(parse_errors) - 5} more errors")
            
            # Sort by date
            trades.sort(key=lambda x: x["time"])
            logger.info(f"Loaded {len(trades)} trades")
            
            return trades
            
        except Exception as e:
            logger.error(f"Error loading trades: {str(e)}")
            return []

    def match_trades(self, trades) -> List[Dict]:
        """
        Match buy and sell trades to calculate P&L
        
        Parameters:
        trades (List[Dict]): List of trade data
        
        Returns:
        List[Dict]: List of matched trade pairs
        """
        pairs = []
        open_positions = {}  # symbol -> list of buy trades
        
        for trade in trades:
            if trade["status"].upper() != "EXECUTED":
                continue
                
            symbol = trade["symbol"]
            side = trade["side"]
            
            # Initialize tracking for this symbol if needed
            if symbol not in open_positions:
                open_positions[symbol] = []
            
            if side == "buy":
                # Add to open positions
                open_positions[symbol].append(trade)
            elif side == "sell" and open_positions[symbol]:
                # Match with the oldest open position (FIFO)
                buy_trade = open_positions[symbol].pop(0)
                
                # Calculate P&L
                buy_price = buy_trade["price"]
                sell_price = trade["price"]
                amount = min(buy_trade["amount"], trade["amount"])
                profit_loss = (sell_price - buy_price) * amount
                
                # Calculate trade duration
                try:
                    buy_time = datetime.fromisoformat(buy_trade["time"].strip())
                    sell_time = datetime.fromisoformat(trade["time"].strip())
                    duration_seconds = (sell_time - buy_time).total_seconds()
                    duration_hours = duration_seconds / 3600
                except (ValueError, TypeError):
                    duration_seconds = 0
                    duration_hours = 0
                
                # Create trade pair record
                pair = {
                    "buy_order": buy_trade["order_id"],
                    "sell_order": trade["order_id"],
                    "symbol": symbol,
                    "buy_time": buy_trade["time"],
                    "sell_time": trade["time"],
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "amount": amount,
                    "profit_loss": profit_loss,
                    "profit_loss_percent": (profit_loss / (buy_price * amount)) * 100 if buy_price > 0 else 0,
                    "duration_hours": duration_hours,
                }
                
                pairs.append(pair)
        
        logger.info(f"Matched {len(pairs)} trade pairs")
        return pairs
    
    def calculate_performance_metrics(self, trades, pairs) -> Dict:
        """
        Calculate performance metrics from trades and pairs
        
        Parameters:
        trades (List[Dict]): List of trade data
        pairs (List[Dict]): List of matched trade pairs
        
        Returns:
        Dict: Performance metrics
        """
        # Initialize metrics
        metrics = {
            "total_trades": len(trades),
            "executed_trades": len([t for t in trades if t["status"].upper() == "EXECUTED"]),
            "cancelled_trades": len([t for t in trades if "CANCEL" in t["status"].upper()]),
            "buy_trades": len([t for t in trades if t["side"] == "buy"]),
            "sell_trades": len([t for t in trades if t["side"] == "sell"]),
            "matched_pairs": len(pairs),
            "total_volume": sum(t["value"] for t in trades if t["status"].upper() == "EXECUTED"),
            "profit_loss": sum(p["profit_loss"] for p in pairs),
            "profit_loss_percent": 0,
            "win_trades": len([p for p in pairs if p["profit_loss"] > 0]),
            "loss_trades": len([p for p in pairs if p["profit_loss"] < 0]),
            "break_even_trades": len([p for p in pairs if p["profit_loss"] == 0]),
            "win_rate": 0,
            "avg_profit_per_trade": 0,
            "avg_profit_percent": 0,
            "avg_loss_per_trade": 0,
            "avg_loss_percent": 0,
            "largest_profit": 0,
            "largest_profit_percent": 0,
            "largest_loss": 0,
            "largest_loss_percent": 0,
            "avg_trade_duration": 0,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
            "expectancy": 0,
            "profit_factor": 0,
            "risk_reward_ratio": 0,
            "recovery_factor": 0,
            "sharpe_ratio": 0,
            "sortino_ratio": 0
        }
        
        # Early return if no trades
        if not trades:
            return metrics
        
        # Extract profit/loss values
        profits = [p["profit_loss"] for p in pairs if p["profit_loss"] > 0]
        losses = [p["profit_loss"] for p in pairs if p["profit_loss"] < 0]
        
        # Calculate win rate
        if pairs:
            metrics["win_rate"] = metrics["win_trades"] / len(pairs) * 100
        
        # Calculate average profit/loss
        if profits:
            metrics["avg_profit_per_trade"] = sum(profits) / len(profits)
            profit_percents = [p["profit_loss_percent"] for p in pairs if p["profit_loss"] > 0]
            metrics["avg_profit_percent"] = sum(profit_percents) / len(profit_percents)
        
        if losses:
            metrics["avg_loss_per_trade"] = sum(losses) / len(losses)
            loss_percents = [p["profit_loss_percent"] for p in pairs if p["profit_loss"] < 0]
            metrics["avg_loss_percent"] = sum(loss_percents) / len(loss_percents)
        
        # Calculate total P&L percent
        total_investment = sum(p["buy_price"] * p["amount"] for p in pairs)
        if total_investment > 0:
            metrics["profit_loss_percent"] = (metrics["profit_loss"] / total_investment) * 100
        
        # Calculate largest profit/loss
        if profits:
            max_profit_pair = max(pairs, key=lambda p: p["profit_loss"] if p["profit_loss"] > 0 else -float('inf'))
            metrics["largest_profit"] = max_profit_pair["profit_loss"]
            metrics["largest_profit_percent"] = max_profit_pair["profit_loss_percent"]
        
        if losses:
            min_loss_pair = min(pairs, key=lambda p: p["profit_loss"] if p["profit_loss"] < 0 else float('inf'))
            metrics["largest_loss"] = min_loss_pair["profit_loss"]
            metrics["largest_loss_percent"] = min_loss_pair["profit_loss_percent"]
        
        # Calculate average trade duration
        if pairs:
            durations = [p["duration_hours"] for p in pairs]
            metrics["avg_trade_duration"] = sum(durations) / len(durations)
        
        # Calculate consecutive wins/losses
        if pairs:
            current_streak = 1
            max_win_streak = 0
            max_loss_streak = 0
            
            for i in range(1, len(pairs)):
                current = pairs[i]["profit_loss"] > 0
                previous = pairs[i-1]["profit_loss"] > 0
                
                if current == previous:
                    current_streak += 1
                else:
                    # Reset streak
                    if previous:
                        max_win_streak = max(max_win_streak, current_streak)
                    else:
                        max_loss_streak = max(max_loss_streak, current_streak)
                    current_streak = 1
            
            # Check final streak
            if pairs[-1]["profit_loss"] > 0:
                max_win_streak = max(max_win_streak, current_streak)
            else:
                max_loss_streak = max(max_loss_streak, current_streak)
                
            metrics["max_consecutive_wins"] = max_win_streak
            metrics["max_consecutive_losses"] = max_loss_streak
        
        # Calculate risk metrics
        if profits and losses:
            # Profit factor
            total_profits = sum(profits)
            total_losses = abs(sum(losses))
            if total_losses > 0:
                metrics["profit_factor"] = total_profits / total_losses
            
            # Risk/reward ratio
            avg_profit = metrics["avg_profit_per_trade"]
            avg_loss = abs(metrics["avg_loss_per_trade"])
            if avg_loss > 0:
                metrics["risk_reward_ratio"] = avg_profit / avg_loss
            
            # Expectancy
            win_probability = metrics["win_rate"] / 100
            loss_probability = 1 - win_probability
            metrics["expectancy"] = (win_probability * avg_profit) - (loss_probability * avg_loss)
            
            # Recovery factor
            max_drawdown = abs(metrics["largest_loss"])
            if max_drawdown > 0:
                metrics["recovery_factor"] = metrics["profit_loss"] / max_drawdown
        
        # Daily performance analysis
        daily_performance = {}
        for trade in trades:
            if trade["status"].upper() != "EXECUTED":
                continue
                
            date = trade["date"]
            if date not in daily_performance:
                daily_performance[date] = {
                    "trades": 0,
                    "buys": 0,
                    "sells": 0,
                    "volume": 0.0,
                }
            
            daily_performance[date]["trades"] += 1
            if trade["side"] == "buy":
                daily_performance[date]["buys"] += 1
            else:
                daily_performance[date]["sells"] += 1
            daily_performance[date]["volume"] += trade["value"]
        
        # Calculate daily P&L
        for pair in pairs:
            sell_date = pair["sell_time"].split(" ")[0]
            if sell_date in daily_performance:
                daily_performance[sell_date]["profit_loss"] = daily_performance.get(sell_date, {}).get("profit_loss", 0) + pair["profit_loss"]
        
        metrics["daily_performance"] = [
            {"date": date, **perf}
            for date, perf in sorted(daily_performance.items())
        ]
        
        # Symbol performance
        symbol_performance = {}
        for trade in trades:
            if trade["status"].upper() != "EXECUTED":
                continue
                
            symbol = trade["symbol"]
            if symbol not in symbol_performance:
                symbol_performance[symbol] = {
                    "trades": 0,
                    "buys": 0,
                    "sells": 0,
                    "volume": 0.0,
                    "profit_loss": 0.0,
                }
            
            symbol_performance[symbol]["trades"] += 1
            if trade["side"] == "buy":
                symbol_performance[symbol]["buys"] += 1
            else:
                symbol_performance[symbol]["sells"] += 1
            symbol_performance[symbol]["volume"] += trade["value"]
        
        # Calculate symbol P&L
        for pair in pairs:
            symbol = pair["symbol"]
            if symbol in symbol_performance:
                symbol_performance[symbol]["profit_loss"] += pair["profit_loss"]
                symbol_performance[symbol]["pairs"] = symbol_performance.get(symbol, {}).get("pairs", 0) + 1
        
        metrics["symbol_performance"] = [
            {"symbol": symbol, **perf}
            for symbol, perf in sorted(symbol_performance.items())
        ]
        
        # Hourly distribution
        hourly_distribution = {}
        for trade in trades:
            if trade["status"].upper() != "EXECUTED":
                continue
                
            # Extract hour
            try:
                time_parts = trade["time"].split(" ")
                if len(time_parts) > 1 and ":" in time_parts[1]:
                    hour = time_parts[1].split(":")[0]
                    
                    if hour not in hourly_distribution:
                        hourly_distribution[hour] = 0
                    hourly_distribution[hour] += 1
            except Exception:
                pass
        
        metrics["hourly_distribution"] = [
            {"hour": int(hour), "count": count}
            for hour, count in sorted(hourly_distribution.items())
        ]
        
        logger.info(f"Calculated performance metrics: PL={metrics['profit_loss']:.2f}, Win rate={metrics['win_rate']:.1f}%")
        return metrics
    
    def analyze(self, symbol=None, start_date=None, end_date=None) -> Dict:
        """
        Analyze performance for the given parameters
        
        Parameters:
        symbol (str): Filter by trading symbol
        start_date (str): Filter trades after this date (YYYY-MM-DD)
        end_date (str): Filter trades before this date (YYYY-MM-DD)
        
        Returns:
        Dict: Performance analysis results
        """
        logger.info(f"Analyzing performance: symbol={symbol}, start_date={start_date}, end_date={end_date}")
        
        # Load trades
        trades = self.load_trades(symbol, start_date, end_date)
        if not trades:
            return {
                "success": False,
                "error": "No trades found for the given parameters",
                "trades": [],
                "metrics": {}
            }
        
        # Match trades into pairs
        pairs = self.match_trades(trades)
        
        # Calculate metrics
        metrics = self.calculate_performance_metrics(trades, pairs)
        
        # Create result
        result = {
            "success": True,
            "trades_count": len(trades),
            "pairs_count": len(pairs),
            "metrics": metrics,
            "trades": trades[:100],  # Return only the first 100 trades to avoid large responses
            "pairs": pairs[:50]  # Return only the first 50 pairs
        }
        
        return result
    
    def export_to_csv(self, data, filepath) -> bool:
        """
        Export data to CSV file
        
        Parameters:
        data (Dict): Data to export
        filepath (str): Path to save the CSV file
        
        Returns:
        bool: True if successful, False otherwise
        """
        try:
            if "trades" in data and data["trades"]:
                trades_df = pd.DataFrame(data["trades"])
                trades_df.to_csv(f"{filepath}_trades.csv", index=False)
                logger.info(f"Exported {len(data['trades'])} trades to {filepath}_trades.csv")
            
            if "pairs" in data and data["pairs"]:
                pairs_df = pd.DataFrame(data["pairs"])
                pairs_df.to_csv(f"{filepath}_pairs.csv", index=False)
                logger.info(f"Exported {len(data['pairs'])} pairs to {filepath}_pairs.csv")
            
            if "metrics" in data and data["metrics"]:
                # Flatten metrics
                flat_metrics = {}
                for k, v in data["metrics"].items():
                    if isinstance(v, (int, float, str, bool)) or v is None:
                        flat_metrics[k] = v
                
                metrics_df = pd.DataFrame([flat_metrics])
                metrics_df.to_csv(f"{filepath}_metrics.csv", index=False)
                
                # Export daily performance
                if "daily_performance" in data["metrics"] and data["metrics"]["daily_performance"]:
                    daily_df = pd.DataFrame(data["metrics"]["daily_performance"])
                    daily_df.to_csv(f"{filepath}_daily.csv", index=False)
                
                # Export symbol performance
                if "symbol_performance" in data["metrics"] and data["metrics"]["symbol_performance"]:
                    symbol_df = pd.DataFrame(data["metrics"]["symbol_performance"])
                    symbol_df.to_csv(f"{filepath}_symbols.csv", index=False)
                
                logger.info(f"Exported metrics to {filepath}_*.csv files")
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            return False