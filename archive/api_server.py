"""
API-server för Tradingbot
"""
from flask import Flask, request, jsonify, send_from_directory, redirect, url_for
from flask_cors import CORS
from flasgger import Swagger
from health import health_bp
import os
from orders import create_market_order, create_limit_order, get_open_orders, cancel_order
from exchange import ExchangeClient
from db import SupabaseClient
from performance import compute_summary_statistics
from config import ConfigManager
from strategy import TradingStrategy
from logger import StructuredLogger
import signal
import sys

app = Flask(__name__, static_folder="static")
CORS(app)
Swagger(app)

app.register_blueprint(health_bp)

# Instansiera nödvändiga objekt
config_manager = ConfigManager()
config = config_manager.get()
logger = StructuredLogger("TradingbotAPI")
exchange = ExchangeClient(config.API_KEY, config.API_SECRET)
db = SupabaseClient(config.SUPABASE_URL, config.SUPABASE_KEY)

def shutdown_handler(signum, frame):
    print("Avslutar Tradingbot API-server...")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

@app.route("/start", methods=["POST"])
def start_bot():
    # Placeholder: Starta boten (implementera om du har processhantering)
    return jsonify({"status": "started"})

@app.route("/stop", methods=["POST"])
def stop_bot():
    # Placeholder: Stoppa boten (implementera om du har processhantering)
    return jsonify({"status": "stopped"})

@app.route("/status", methods=["GET"])
def status():
    # Placeholder: Returnera status (implementera om du har processhantering)
    return jsonify({"status": "running"})

@app.route("/balance", methods=["GET"])
def get_balance():
    try:
        balance = exchange.fetch_balance()
        return jsonify(balance)
    except Exception as e:
        logger.error(f"Error fetching balance: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/order", methods=["POST"])
def create_order():
    data = request.json
    order_type = data.get("type")  # 'buy' eller 'sell'
    symbol = data.get("symbol")
    amount = float(data.get("amount", 0.001))
    price = data.get("price")
    if price is not None:
        price = float(price)
    try:
        if price:
            order = create_limit_order(symbol, order_type, amount, price)
        else:
            order = create_market_order(symbol, order_type, amount)
        return jsonify({"success": True, "order": order})
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/orderhistory", methods=["GET"])
def order_history():
    try:
        history = db.get_order_history()
        return jsonify(history)
    except Exception as e:
        logger.error(f"Error fetching order history: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/orders", methods=["GET"])
def get_orders():
    try:
        orders = db.get_order_history()
        return jsonify(orders)
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/openorders", methods=["GET"])
def open_orders():
    try:
        open_orders = get_open_orders()
        return jsonify(open_orders)
    except Exception as e:
        logger.error(f"Error fetching open orders: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/realtimedata", methods=["GET"])
def realtimatedata():
    # Placeholder: Returnera realtidsdata (implementera om du har WebSocket/dataflöde)
    return jsonify({"message": "Realtime data endpoint not yet implemented."})

@app.route("/config", methods=["GET", "POST"])
def config_endpoint():
    if request.method == "GET":
        return jsonify(config_manager.get())
    elif request.method == "POST":
        new_config = request.json
        config_manager.save(new_config)
        return jsonify({"status": "updated"})

@app.route("/strategy_performance", methods=["GET"])
def strategy_performance():
    try:
        stats = compute_summary_statistics(db.get_order_history())
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error computing strategy performance: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/logs", methods=["GET"])
def get_logs():
    log_path = os.path.join(os.path.dirname(__file__), "order_status_log.txt")
    if not os.path.exists(log_path):
        return jsonify({"logs": []})
    with open(log_path, "r") as f:
        logs = f.readlines()[-100:]
    return jsonify({"logs": logs})

@app.route("/dashboard")
def serve_dashboard():
    return send_from_directory(app.static_folder, "dashboard.html")

@app.route("/dashboard")
def serve_dashboard_html():
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return send_from_directory(static_dir, "dashboard.html")

@app.route("/")
def root():
    return redirect(url_for("serve_dashboard_html"))

@app.errorhandler(Exception)
def handle_error(e):
    return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(port=5000)
