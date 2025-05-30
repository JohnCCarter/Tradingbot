import json
import time
import ccxt
from flask import (
    Flask,
    jsonify,
    request,
    send_file,
    redirect,
    url_for,
    Response,
    send_from_directory,
)
import subprocess
import os
import logging
from dotenv import load_dotenv

app = Flask(__name__)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


@app.after_request
def add_cors_headers(response):
    for k, v in CORS_HEADERS.items():
        response.headers[k] = v
    return response


# Handle CORS preflight globally
@app.route("/<path:path>", methods=["OPTIONS"])
def handle_options(path):
    return Response(status=200)


# Path to your tradingbot.py
BOT_PATH = os.path.join(os.path.dirname(__file__), "tradingbot.py")

# Global variable to keep track of the bot process
bot_process = None

logger = logging.getLogger(__name__)


@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception("Unhandled exception in API:")
    return jsonify({"error": "Internal server error"}), 500


@app.route("/status", methods=["GET"])
def status():
    global bot_process
    running = bot_process is not None and bot_process.poll() is None
    return jsonify({"bot_running": running})


@app.route("/start", methods=["POST"])
def start_bot():
    global bot_process
    logger.info("API /start called, bot_process=%s", bot_process)
    if bot_process is None or bot_process.poll() is not None:
        bot_process = subprocess.Popen(["python3", BOT_PATH])
        return jsonify({"started": True})
    else:
        return jsonify({"started": False, "reason": "Bot already running"}), 400


@app.route("/stop", methods=["POST"])
def stop_bot():
    global bot_process
    logger.info("API /stop called, bot_process=%s", bot_process)
    if bot_process is not None and bot_process.poll() is None:
        bot_process.terminate()
        # Also kill any stray tradingbot.py processes
        try:
            subprocess.run(["pkill", "-f", "tradingbot.py"], check=False)
        except Exception as e:
            logger.warning(f"Failed to pkill tradingbot processes: {e}")
        bot_process = None
        return jsonify({"stopped": True})
    else:
        return jsonify({"stopped": False, "reason": "Bot not running"}), 400


@app.route("/balance", methods=["GET"])
def get_balance():
    from tradingbot import fetch_balance

    try:
        balance = fetch_balance()
        return jsonify(balance)
    except ccxt.AuthenticationError as e:
        logger.error(f"Authentication error fetching balance: {e}")
        return jsonify({"error": "AuthenticationError", "message": str(e)}), 401
    except Exception:
        logger.exception("Error in /balance:")
        return jsonify({"error": "Unable to fetch balance."}), 500


@app.route("/logs", methods=["GET"])
def get_logs():
    log_path = os.path.join(os.path.dirname(__file__), "order_status_log.txt")
    if not os.path.exists(log_path):
        return jsonify({"logs": []})
    logs = []
    with open(log_path, "r") as f:
        for line in f:
            # Visa endast tekniska/systemloggar, filtrera bort orderhändelser
            if "EXECUTED" not in line and "CANCELED" not in line:
                logs.append(line.strip())
    return jsonify({"logs": logs[-100:]})


@app.route("/orders", methods=["GET"])
def get_orders():
    log_path = os.path.join(os.path.dirname(__file__), "order_status_log.txt")
    if not os.path.exists(log_path):
        return jsonify({"orders": []})
    orders = []
    with open(log_path, "r") as f:
        for line in f:
            if "EXECUTED" in line or "CANCELED" in line:
                orders.append(line.strip())
    return jsonify({"orders": orders[-20:]})  # Endast utförda/avbrutna ordrar, nu 20


@app.route("/orderhistory", methods=["GET"])
def order_history():
    log_path = os.path.join(os.path.dirname(__file__), "order_status_log.txt")
    if not os.path.exists(log_path):
        return jsonify({"orders": [], "status": "no_file"})

    symbol = request.args.get("symbol")
    date = request.args.get("date")  # format: 'YYYY-MM-DD'
    debug = request.args.get("debug") == "true"

    # Förbered ett mer detaljerat svar
    response = {"orders": [], "status": "ok", "debug_info": {} if debug else None}

    # För debugläge, samla alla unika datum vi ser i loggfilen
    unique_dates = set()
    total_lines = 0
    matched_order_count = 0

    with open(log_path, "r") as f:
        for line in f:
            total_lines += 1

            # Extrahera datum från början av raden (om möjligt)
            try:
                line_date = line.split(" ")[0]
                if debug:
                    unique_dates.add(line_date)
            except (IndexError, ValueError):
                pass

            # Filtrera för orderhändelser
            if (
                "EXECUTED" not in line
                and "CANCELED" not in line
                and "CANCELLED" not in line
            ):
                continue

            # Använd symbol-filter om angivet
            if symbol and symbol not in line:
                continue

            # Använd datumfilter om angivet - jämför med början av raden
            if date:
                if not line.startswith(date):
                    # Om inte exakt match i början, prova lite mer flexibelt
                    if date not in line.split(" ")[0]:
                        continue

            matched_order_count += 1
            response["orders"].append(line.strip())

    # Begränsa till de senaste 20 posterna
    response["orders"] = response["orders"][-20:]

    # Lägg till debugging-information om det är aktiverat
    if debug:
        response["debug_info"] = {
            "total_lines": total_lines,
            "matched_order_count": matched_order_count,
            "unique_dates": sorted(list(unique_dates)),
            "date_filter": date,
            "symbol_filter": symbol,
        }

    # Logga sammanfattning
    logger.info(
        f"Hittade {matched_order_count} orderhistorik-poster"
        + (f" för datum {date}" if date else "")
        + (f" och symbol {symbol}" if symbol else "")
    )

    return jsonify(response)


@app.route("/order", methods=["POST"])
def create_order():
    data = request.json
    order_type = data.get("type")  # 'buy' eller 'sell'
    symbol = data.get("symbol")
    amount = float(data.get("amount", 0.001))
    price = data.get("price")
    if price is not None:
        price = float(price)

    # Importera funktionerna för att hantera orders
    from tradingbot import place_order, ensure_paper_trading_symbol, EXCHANGE_NAME

    try:
        # Säkerställ rätt symbolformat för Bitfinex paper trading
        if EXCHANGE_NAME == "bitfinex":
            symbol = ensure_paper_trading_symbol(symbol)

        place_order(order_type, symbol, amount, price)
        return jsonify(
            {"success": True, "message": f"{order_type} order sent for {symbol}."}
        )
    except Exception:
        logger.exception("Error in create_order:")
        return jsonify({"success": False, "error": "Could not place order."}), 400


@app.route("/realtimedata", methods=["GET"])
def realtimatedata():
    from tradingbot import (
        get_current_price,
        SYMBOL,
        ensure_paper_trading_symbol,
        EXCHANGE_NAME,
    )

    symbol = request.args.get("symbol") or SYMBOL

    try:
        # Säkerställ rätt symbolformat för Bitfinex paper trading
        if EXCHANGE_NAME == "bitfinex":
            symbol = ensure_paper_trading_symbol(symbol)

        price = get_current_price(symbol)
        return jsonify({"symbol": symbol, "price": price})
    except Exception as e:
        return jsonify({"error": str(e)}), 150


@app.route("/config", methods=["GET", "POST"])
def config_endpoint():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if request.method == "GET":
        with open(config_path, "r") as f:
            config = f.read()
        return jsonify({"config": config})
    elif request.method == "POST":
        new_config = request.json
        with open(config_path, "w") as f:
            import json

            json.dump(new_config, f, indent=2)
        return jsonify({"updated": True})


@app.route("/")
def root():
    return redirect(url_for("serve_dashboard"))


@app.route("/dashboard")
def serve_dashboard():
    dashboard_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "dashboard.html"
    )
    return send_file(dashboard_path)


@app.route("/openorders", methods=["GET"])
def get_open_orders():
    from tradingbot import exchange, ensure_paper_trading_symbol, EXCHANGE_NAME

    try:
        # Om symbol anges i request, kontrollera och konvertera formatet
        symbol_param = request.args.get("symbol")
        if symbol_param and EXCHANGE_NAME == "bitfinex":
            symbol_param = ensure_paper_trading_symbol(symbol_param)

        # Use CCXT fetch_open_orders to retrieve active orders
        open_orders = (
            exchange.fetch_open_orders(symbol_param)
            if symbol_param
            else exchange.fetch_open_orders()
        )

        # Log the response from fetch_open_orders for debugging
        logger.info(f"Fetched open orders: {open_orders}")

        # Validate the response structure
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


@app.route("/strategy_performance", methods=["GET"])
def strategy_performance():
    import json

    log_path = os.path.join(os.path.dirname(__file__), "order_status_log.txt")
    if not os.path.exists(log_path):
        return jsonify({"performance": {}, "trades": [], "status": "no_file"})

    # Hämta parametrar för filtrering
    symbol = request.args.get("symbol")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    # Ny parameter för att välja detaljnivå
    detail_level = request.args.get(
        "detail_level", "standard"
    )  # standard, extended, full

    # Statistikvariabler
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
        # Utökade statistikfält
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

    # För att beräkna handelspar
    paired_trades = {}  # key: symbol, value: list of buy and sell trades

    # För att spåra handelsaktivitet per timme
    hourly_trades = {}

    with open(log_path, "r") as f:
        for line in f:
            # Filtrera för orderhändelser
            if (
                "EXECUTED" not in line
                and "CANCELED" not in line
                and "CANCELLED" not in line
            ):
                continue

            # Parsad orderdata
            try:
                # Använd samma funktion som i frontend för parsning
                # Förväntat format: "YYYY-MM-DD HH:MM:SS: Order-ID: 123, Status: EXECUTED, Info: [...]"
                match = line.split(": Order-ID:")
                if not match or len(match) < 2:
                    parse_errors.append(
                        {"line": line, "error": "Kunde inte dela på 'Order-ID:'"}
                    )
                    continue

                date_part = match[0]  # YYYY-MM-DD HH:MM:SS
                if not date_part or len(date_part) < 10:
                    parse_errors.append({"line": line, "error": "Ogiltigt datumformat"})
                    continue

                date = date_part.split(" ")[0]  # YYYY-MM-DD
                time_parts = date_part.split(" ")
                hour = "00"
                if len(time_parts) > 1 and ":" in time_parts[1]:
                    hour = time_parts[1].split(":")[0]

                # Spåra handelsaktivitet per timme
                if hour not in hourly_trades:
                    hourly_trades[hour] = {
                        "total": 0,
                        "executed": 0,
                        "cancelled": 0,
                        "buys": 0,
                        "sells": 0,
                    }

                hourly_trades[hour]["total"] += 1

                # Filtrera på datum om angivet
                if start_date and date < start_date:
                    continue
                if end_date and date > end_date:
                    continue

                # Extrahera order-ID och status
                rest = match[1].split(", Status: ")
                if len(rest) < 2:
                    parse_errors.append(
                        {"line": line, "error": "Kunde inte dela på 'Status:'"}
                    )
                    continue

                order_id = rest[0].strip()
                status_part = rest[1].split(", Info: ")
                if not status_part:
                    parse_errors.append(
                        {"line": line, "error": "Kunde inte dela på 'Info:'"}
                    )
                    continue

                status = status_part[0]
                info = status_part[1] if len(status_part) > 1 else ""

                # Rensa Python None till JSON null, och enkla till dubbla citat
                cleaned_info = info.replace("None", "null").replace("'", '"')

                # Försök parsa order-info
                try:
                    # Bitfinex-format: symbol på index 3, typ på 8, side på 6, pris på 16, mängd på 6
                    arr = json.loads(cleaned_info)
                    if not arr or not isinstance(arr, list):
                        parse_errors.append(
                            {"line": line, "error": "Kunde inte parsa JSON från info"}
                        )
                        continue

                    order_symbol = "unknown"
                    if len(arr) > 3 and arr[3]:
                        symbol_match = arr[3].upper()
                        order_symbol = symbol_match

                    # Filtrera på symbol om angivet
                    if symbol and symbol.upper() not in order_symbol:
                        continue

                    # Samla trade-data
                    side = "buy" if len(arr) > 6 and float(arr[6] or 0) > 0 else "sell"
                    price = float(arr[16]) if len(arr) > 16 and arr[16] else 0.0
                    amount = abs(float(arr[6])) if len(arr) > 6 and arr[6] else 0.0

                    # Accept Bitfinex-format: type is at index 8 (e.g. 'EXCHANGE LIMIT', 'EXCHANGE MARKET')
                    order_type = arr[8] if len(arr) > 8 and arr[8] else "unknown"
                    # Remove strict 'type' key check, just use order_type as string
                    # Do not append parse_errors for missing 'type' key or unknown order_type if Bitfinex format
                    # Only log error if order_type is still completely missing (empty string)
                    if order_type == "unknown" or not isinstance(order_type, str):
                        order_type = "unknown"

                    # Uppdatera statistik
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

                    # Spåra prestanda per symbol
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

                    # Beräkna vinst/förlust per symbol
                    if symbol_stats["buys"] > 0 and symbol_stats["sells"] > 0:
                        symbol_stats["profit_loss"] = (
                            symbol_stats["total_sell_value"]
                            - symbol_stats["total_buy_value"]
                        )

                    # Spåra daglig prestanda
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

                    # För att spåra handelspar för mer exakt P&L-analys
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

                    # Skapa trade-objekt för frontend
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

                    # Spåra högsta vinst/förlust per trade
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

                    # Add debug logs to trace trade extraction and ensure proper parsing
                    logger.debug(f"Processing line: {line.strip()}")
                    logger.debug(
                        f"Parsed order details: symbol={order_symbol}, side={side}, price={price}, amount={amount}"
                    )

                    # Validate parsed trade data
                    if not order_symbol or price <= 0 or amount <= 0:
                        logger.warning(
                            f"Invalid trade data: symbol={order_symbol}, price={price}, amount={amount}"
                        )
                        parse_errors.append(
                            {"line": line, "error": "Invalid trade data"}
                        )
                        continue

                    # Ensure trade is appended only if valid
                    trades.append(trade)
                    logger.debug(f"Trade added: {trade}")

                except Exception as e:
                    logger.error(f"Error parsing order info: {e}")
                    parse_errors.append(
                        {
                            "line": line,
                            "error": f"Fel vid parsning av orderinfo: {str(e)}",
                        }
                    )
                    continue

            except Exception as e:
                logger.error(f"Error processing order line: {e}")
                parse_errors.append(
                    {
                        "line": line,
                        "error": f"Fel vid bearbetning av orderrad: {str(e)}",
                    }
                )
                continue

            # Complete the parsing logic
            try:
                # Adjust filtering logic to match log file format
                if (
                    "EXECUTED" not in line
                    and "CANCELED" not in line
                    and "CANCELLED" not in line
                ):
                    continue

                # Ensure proper parsing of log lines
                match = line.split(": Order-ID:")
                if not match or len(match) < 2:
                    parse_errors.append(
                        {"line": line, "error": "Could not split on 'Order-ID:'"}
                    )
                    continue

                date_part = match[0].strip()  # Extract date and time
                if not date_part or len(date_part) < 10:
                    parse_errors.append({"line": line, "error": "Invalid date format"})
                    continue

                # Extract order details
                rest = match[1].split(", Status: ")
                if len(rest) < 2:
                    parse_errors.append(
                        {"line": line, "error": "Could not split on 'Status:'"}
                    )
                    continue

                order_id = rest[0].strip()
                status_info = rest[1].split(", Info: ")
                status = status_info[0].strip()
                info = status_info[1].strip() if len(status_info) > 1 else ""

                # Update performance metrics
                performance["total_trades"] += 1
                if status == "EXECUTED":
                    performance["executed"] += 1
                elif status in ["CANCELLED", "CANCELED"]:
                    performance["cancelled"] += 1

                # Track hourly trades
                hour = (
                    date_part.split(" ")[1].split(":")[0] if " " in date_part else "00"
                )
                if hour not in hourly_trades:
                    hourly_trades[hour] = {
                        "total": 0,
                        "executed": 0,
                        "cancelled": 0,
                        "buys": 0,
                        "sells": 0,
                    }
                hourly_trades[hour]["total"] += 1
                hourly_trades[hour][
                    "executed" if status == "EXECUTED" else "cancelled"
                ] += 1

            except Exception as e:
                parse_errors.append({"line": line, "error": str(e)})
            finally:
                # Ensure any necessary cleanup or logging
                pass

    # Beräkna handelsfrekvens
    if performance["daily_performance"]:
        num_days = len(performance["daily_performance"])
        if num_days > 0:
            performance["trade_frequency"] = performance["total_trades"] / num_days

    # Spåra handelsframgång per timme
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

    # Beräkna vinst/förlust och win rate baserat på köp och sälj
    if performance["buys"] > 0 and performance["sells"] > 0:
        # Förbättrad P&L-beräkning baserat på matchade köp/sälj-par
        total_profit_loss = 0
        for symbol, symbol_trades in paired_trades.items():
            buy_trades = [t for t in symbol_trades if t["side"] == "buy"]
            sell_trades = [t for t in symbol_trades if t["side"] == "sell"]

            # Enkel FIFO-metod för att matcha köp och sälj
            remaining_buys = buy_trades.copy()
            for sell in sell_trades:
                sell_amount = sell["amount"]
                sell_value = sell["value"]

                while sell_amount > 0 and remaining_buys:
                    buy = remaining_buys[0]
                    used_amount = min(buy["amount"], sell_amount)
                    buy_price_per_unit = buy["price"]
                    sell_price_per_unit = sell["price"]

                    # Beräkna P&L för denna del av transaktionen
                    pl_per_unit = sell_price_per_unit - buy_price_per_unit
                    pl_for_amount = pl_per_unit * used_amount
                    total_profit_loss += pl_for_amount

                    # Uppdatera återstående mängder
                    sell_amount -= used_amount
                    buy["amount"] -= used_amount

                    if buy["amount"] <= 0:
                        remaining_buys.pop(0)

        performance["profit_loss"] = total_profit_loss
        performance["win_rate"] = (
            total_profit_loss > 0
        ) * 100  # Enkel win rate baserad på total P&L

        if performance["executed"] > 0:
            performance["avg_profit_per_trade"] = (
                total_profit_loss / performance["executed"]
            )

    # Sortera trades kronologiskt
    trades.sort(key=lambda x: x["time"])

    # Konvertera daily_performance från dict till lista för enklare användning i frontend
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

    # Sortera daily_performance kronologiskt
    daily_performance_list.sort(key=lambda x: x["date"])
    performance["daily_performance"] = daily_performance_list

    # Förbered respons baserat på önskad detaljnivå
    response_data = {"performance": performance, "status": "ok"}

    # Inkludera trades baserat på detaljnivå
    if detail_level in ["standard", "extended", "full"]:
        response_data["trades"] = trades[
            -100:
        ]  # Begränsa till senaste 100 trades för standard

    # Lägg till debugdata för mer detaljerade nivåer
    if detail_level in ["extended", "full"]:
        response_data["hourly_stats"] = performance["trade_success_by_hour"]
        response_data["paired_trades_summary"] = {
            symbol: {
                "buys": len([t for t in trades if t["side"] == "buy"]),
                "sells": len([t for t in trades if t["side"] == "sell"]),
            }
            for symbol, trades in paired_trades.items()
        }

    # Lägg till full debugdata
    if detail_level == "full":
        response_data["parse_errors"] = parse_errors
        response_data["all_trades"] = trades  # Alla trades utan begränsning

    # Initialize variables for pairing trades
    remaining_buys = []
    num_days = len(performance["daily_performance"])

    if num_days > 0:
        performance["trade_frequency"] = performance["total_trades"] / num_days

    # Logic for pairing buy and sell trades
    for symbol, symbol_trades in paired_trades.items():
        buy_trades = [trade for trade in symbol_trades if trade["type"] == "buy"]
        sell_trades = [trade for trade in symbol_trades if trade["type"] == "sell"]
        remaining_buys = buy_trades.copy()

        for sell in sell_trades:
            sell_amount = sell["amount"]
            while sell_amount > 0 and remaining_buys:
                buy = remaining_buys[0]
                # Pairing logic here
                remaining_buys.pop(0)

    # Return the performance data
    return jsonify(
        {
            "performance": performance,
            "trades": trades,
            "status": "success" if not parse_errors else "partial_success",
            "errors": parse_errors,
        }
    )


@app.route("/debug_log", methods=["GET"])
def debug_log():
    """Hämtar loggfiler och systemstatus för debug"""

    # Systemstatistik
    import psutil

    system_stats = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "api_uptime_seconds": 0,  # Placeholder
    }

    # Loggfiler
    log_files = {}
    log_path = os.path.join(os.path.dirname(__file__), "order_status_log.txt")

    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            log_content = f.readlines()
            log_files["order_status_log"] = {
                "size_bytes": os.path.getsize(log_path),
                "lines": len(log_content),
                "last_modified": os.path.getmtime(log_path),
                "last_lines": log_content[-20:] if len(log_content) > 0 else [],
            }

    # Bot-status
    global bot_process
    bot_status = {
        "running": bot_process is not None and bot_process.poll() is None,
        "pid": (
            bot_process.pid
            if bot_process is not None and bot_process.poll() is None
            else None
        ),
        "returncode": bot_process.poll() if bot_process is not None else None,
    }

    # Konfigurations-information (saniterad)
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    config_info = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                import json

                config = json.load(f)

                # Visa endast icke-känsliga delar av konfigurationen
                safe_keys = [
                    "symbol",
                    "strategy",
                    "time_frame",
                    "log_level",
                    "backtest",
                ]
                for key in safe_keys:
                    if key in config:
                        config_info[key] = config[key]

                config_info["config_file_size"] = os.path.getsize(config_path)
                config_info["last_modified"] = os.path.getmtime(config_path)
        except Exception as e:
            config_info["error"] = str(e)

    # Returnera all debug-information
    return jsonify(
        {
            "system_stats": system_stats,
            "log_files": log_files,
            "bot_status": bot_status,
            "config_info": config_info,
            "timestamp": time.time(),
        }
    )


@app.route("/historical", methods=["GET"])
def get_historical_data():
    from tradingbot import fetch_market_data, EXCHANGE, ensure_paper_trading_symbol

    symbol = request.args.get("symbol", "BTC/USD")
    timeframe = request.args.get("timeframe", "1h")
    limit = int(request.args.get("limit", "100"))

    # Konvertera symbol till rätt format för Bitfinex paper trading
    if EXCHANGE.id == "bitfinex" and EXCHANGE.options.get("paper", False):
        symbol = ensure_paper_trading_symbol(symbol)
        logger.info(f"Historical data using paper trading symbol: {symbol}")

    try:
        df = fetch_market_data(EXCHANGE, symbol, timeframe, limit)
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


@app.route("/ticker", methods=["GET"])
def ticker_endpoint():
    try:
        from tradingbot import get_current_price, SYMBOL

        # Fetch the current price for the default symbol
        price = get_current_price(SYMBOL)
        return jsonify({"symbol": SYMBOL, "price": price})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/pricehistory", methods=["GET"])
def pricehistory():
    """Fetch historical price data for a given symbol."""
    import ccxt
    from flask import jsonify, request

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


@app.route("/<path:filename>")
def serve_static(filename):
    """Serve static files (JS, CSS) from the Tradingbot directory."""
    # Generated by Copilot
    static_dir = os.path.dirname(os.path.abspath(__file__))
    if filename.endswith(".js") or filename.endswith(".css"):
        return send_from_directory(static_dir, filename)
    # Fallback: 404
    return "Not found", 404


@app.route("/frontend_error_log", methods=["POST"])
def frontend_error_log():
    """Tar emot felrapporter från frontend och sparar dem i en loggfil."""
    try:
        error_data = request.get_json(force=True)
        log_path = os.path.join(os.path.dirname(__file__), "frontend_errors.log")
        with open(log_path, "a") as f:
            log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {json.dumps(error_data, ensure_ascii=False)}\n"
            f.write(log_entry)
        return jsonify({"logged": True})
    except Exception as e:
        logger.error(f"Failed to log frontend error: {e}")
        return jsonify({"logged": False, "error": str(e)}), 500


if __name__ == "__main__":
    import os

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    # Load environment variables (including API_PORT)
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
    # Use API_PORT env var or default to 5000
    api_port = int(os.getenv("API_PORT", "5000"))
    app.run(host="0.0.0.0", port=api_port)
