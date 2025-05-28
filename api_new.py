#!/usr/bin/env python3
"""
API server entry point for Tradingbot.
This script starts the Flask API server.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask application
from Tradingbot.api.app import app, run_app


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    
    # Load environment variables
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
    
    # Get port from environment variable
    api_port = int(os.getenv("API_PORT", "5000"))
    
    # Run the Flask application
    run_app(port=api_port)