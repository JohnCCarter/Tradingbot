#!/bin/bash
# Kör Tradingbot med rätt conda-miljö

# Aktivera conda-miljön tradingbot_env
source $(conda info --base)/etc/profile.d/conda.sh
conda activate tradingbot_env

# Gå till Tradingbot-mappen och kör main.py
cd "$(dirname "$0")"
python main.py
