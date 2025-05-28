"""
Bot control routes for Tradingbot API.
Handles status, start/stop, and configuration operations.
"""

import subprocess
import os
import logging
import json
from flask import jsonify, request
import psutil

# Global variables
bot_process = None
BOT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "tradingbot.py")
logger = logging.getLogger(__name__)


def register_routes(app):
    """Register bot routes with Flask app"""
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Global exception handler for API errors"""
        logger.exception("Unhandled exception in API:")
        return jsonify({"error": "Internal server error"}), 500
    
    @app.route("/status", methods=["GET"])
    def status():
        """Get bot running status"""
        global bot_process
        running = bot_process is not None and bot_process.poll() is None
        return jsonify({"bot_running": running})
    
    @app.route("/start", methods=["POST"])
    def start_bot():
        """Start the bot process"""
        global bot_process
        logger.info("API /start called, bot_process=%s", bot_process)
        if bot_process is None or bot_process.poll() is not None:
            bot_process = subprocess.Popen(["python3", BOT_PATH])
            return jsonify({"started": True})
        else:
            return jsonify({"started": False, "reason": "Bot already running"}), 400
    
    @app.route("/stop", methods=["POST"])
    def stop_bot():
        """Stop the bot process"""
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
    
    @app.route("/config", methods=["GET", "POST"])
    def config_endpoint():
        """Get or update bot configuration"""
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config.json")
        if request.method == "GET":
            try:
                with open(config_path, "r") as f:
                    config = f.read()
                return jsonify({"config": config})
            except Exception as e:
                logger.error(f"Error reading config: {e}")
                return jsonify({"error": f"Could not read config: {e}"}), 500
        elif request.method == "POST":
            try:
                new_config = request.json
                with open(config_path, "w") as f:
                    json.dump(new_config, f, indent=2)
                return jsonify({"updated": True})
            except Exception as e:
                logger.error(f"Error updating config: {e}")
                return jsonify({"error": f"Could not update config: {e}"}), 500
    
    @app.route("/debug_log", methods=["GET"])
    def debug_log():
        """Get debug logs and system status"""
        # System statistics
        system_stats = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "api_uptime_seconds": 0,  # Placeholder
        }
    
        # Log files
        log_files = {}
        log_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "order_status_log.txt")
    
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                log_content = f.readlines()
                log_files["order_status_log"] = {
                    "size_bytes": os.path.getsize(log_path),
                    "lines": len(log_content),
                    "last_modified": os.path.getmtime(log_path),
                    "last_lines": log_content[-20:] if len(log_content) > 0 else [],
                }
    
        # Bot status
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
    
        # Configuration information (sanitized)
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config.json")
        config_info = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
    
                    # Show only non-sensitive parts of the configuration
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
    
        # Return all debug information
        import time
        return jsonify(
            {
                "system_stats": system_stats,
                "log_files": log_files,
                "bot_status": bot_status,
                "config_info": config_info,
                "timestamp": time.time(),
            }
        )