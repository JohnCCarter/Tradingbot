#!/bin/bash
# script_start.sh - Startar Tradingbot i rätt miljö

# Ange miljönamn och botens mapp
ENV_NAME="tradingbot_env"
BOT_DIR="$(dirname "$0")"

# Aktivera conda-miljön
source ~/miniconda3/etc/profile.d/conda.sh
conda activate "$ENV_NAME"

# Gå till botens mapp om scriptet körs utanför
cd "$BOT_DIR"

# Starta boten
python tradingbot.py
