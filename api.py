from flask import Flask, jsonify, request, send_file, redirect, url_for
import threading
import subprocess
import os
import logging
from dotenv import load_dotenv

app = Flask(__name__)

# Path to your tradingbot.py
BOT_PATH = os.path.join(os.path.dirname(__file__), 'tradingbot.py')

# Global variable to keep track of the bot process
bot_process = None

@app.route('/status', methods=['GET'])
def status():
    global bot_process
    running = bot_process is not None and bot_process.poll() is None
    return jsonify({"bot_running": running})

@app.route('/start', methods=['POST'])
def start_bot():
    global bot_process
    if bot_process is None or bot_process.poll() is not None:
        bot_process = subprocess.Popen(['python3', BOT_PATH])
        return jsonify({"started": True})
    else:
        return jsonify({"started": False, "reason": "Bot already running"}), 400

@app.route('/stop', methods=['POST'])
def stop_bot():
    global bot_process
    if bot_process is not None and bot_process.poll() is None:
        bot_process.terminate()
        bot_process = None
        return jsonify({"stopped": True})
    else:
        return jsonify({"stopped": False, "reason": "Bot not running"}), 400

@app.route('/balance', methods=['GET'])
def get_balance():
    from tradingbot import fetch_balance
    balance = fetch_balance()
    return jsonify(balance)

@app.route('/logs', methods=['GET'])
def get_logs():
    log_path = os.path.join(os.path.dirname(__file__), 'order_status_log.txt')
    if not os.path.exists(log_path):
        return jsonify({"logs": []})
    logs = []
    with open(log_path, 'r') as f:
        for line in f:
            # Visa endast tekniska/systemloggar, filtrera bort orderhändelser
            if 'EXECUTED' not in line and 'CANCELED' not in line:
                logs.append(line.strip())
    return jsonify({"logs": logs[-100:]})

@app.route('/orders', methods=['GET'])
def get_orders():
    log_path = os.path.join(os.path.dirname(__file__), 'order_status_log.txt')
    if not os.path.exists(log_path):
        return jsonify({"orders": []})
    orders = []
    with open(log_path, 'r') as f:
        for line in f:
            if 'EXECUTED' in line or 'CANCELED' in line:
                orders.append(line.strip())
    return jsonify({"orders": orders[-150:]})  # Endast utförda/avbrutna ordrar, nu 150

@app.route('/orderhistory', methods=['GET'])
def order_history():
    log_path = os.path.join(os.path.dirname(__file__), 'order_status_log.txt')
    if not os.path.exists(log_path):
        return jsonify({"orders": []})
    symbol = request.args.get('symbol')
    date = request.args.get('date')  # format: 'YYYY-MM-DD'
    orders = []
    with open(log_path, 'r') as f:
        for line in f:
            if 'EXECUTED' not in line and 'CANCELED' not in line:
                continue  # Endast orderhändelser
            if symbol and symbol not in line:
                continue
            if date and not line.startswith(date):
                continue
            orders.append(line.strip())
    # Logga antal filtrerade ordrar och parametrar
    print(f"[DEBUG] /orderhistory symbol={symbol} date={date} -> {len(orders[-150:])} rader returneras")
    return jsonify({"orders": orders[-150:]})  # Returnera max 150 senaste orderhändelser

@app.route('/order', methods=['POST'])
def create_order():
    data = request.json
    order_type = data.get('type')  # 'buy' eller 'sell'
    amount = float(data.get('amount', 0.001))
    price = data.get('price')
    if price is not None:
        price = float(price)
    from tradingbot import place_order, SYMBOL
    try:
        place_order(order_type, SYMBOL, amount, price)
        return jsonify({"success": True, "message": f"{order_type} order sent."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/realtimedata', methods=['GET'])
def realtimatedata():
    from tradingbot import get_current_price, SYMBOL
    try:
        price = get_current_price(SYMBOL)
        return jsonify({"symbol": SYMBOL, "price": price})
    except Exception as e:
        return jsonify({"error": str(e)}), 150

@app.route('/config', methods=['GET', 'POST'])
def config_endpoint():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if request.method == 'GET':
        with open(config_path, 'r') as f:
            config = f.read()
        return jsonify({"config": config})
    elif request.method == 'POST':
        new_config = request.json
        with open(config_path, 'w') as f:
            import json
            json.dump(new_config, f, indent=2)
        return jsonify({"updated": True})

@app.route('/')
def root():
    return redirect(url_for('serve_dashboard'))

@app.route('/dashboard')
def serve_dashboard():
    dashboard_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard.html')
    return send_file(dashboard_path)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
    app.run(host='0.0.0.0', port=5000)
