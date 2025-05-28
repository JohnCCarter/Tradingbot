"""
Main Flask application for Tradingbot API.
Sets up the Flask app and imports routes.
"""

import os
import logging
from flask import Flask
from dotenv import load_dotenv

# Create Flask app
app = Flask(__name__)

# CORS headers
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses"""
    for k, v in CORS_HEADERS.items():
        response.headers[k] = v
    return response


# Handle CORS preflight requests
@app.route("/<path:path>", methods=["OPTIONS"])
def handle_options(path):
    """Handle CORS preflight requests"""
    from flask import Response
    return Response(status=200)


# Import route modules
def register_routes():
    """Register API routes from modules"""
    from Tradingbot.api.routes import (
        bot_routes,
        data_routes,
        order_routes,
        dashboard_routes,
        performance_routes,
    )
    
    # Register routes with Flask application
    bot_routes.register_routes(app)
    data_routes.register_routes(app)
    order_routes.register_routes(app)
    dashboard_routes.register_routes(app)
    performance_routes.register_routes(app)


def create_app():
    """Create and configure Flask application"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    
    # Load environment variables
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    
    # Register routes
    register_routes()
    
    return app


# Create a singleton instance for importing
app = create_app()


def run_app(host="0.0.0.0", port=None):
    """Run the Flask application"""
    # Use API_PORT env var or default to 5000
    api_port = int(port or os.getenv("API_PORT", "5000"))
    app.run(host=host, port=api_port)


if __name__ == "__main__":
    run_app()