#!/bin/bash
# Start-script för Tradingbot
cd "$(dirname "$0")/.."
conda run -n tradingbot_env screen -dmS tradingbot python main.py
conda run -n tradingbot_env screen -dmS apiserver python api_server.py
