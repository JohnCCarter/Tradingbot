#!/bin/bash

# Aktivera Conda-miljön
source ~/miniconda3/etc/profile.d/conda.sh
conda activate tradingbot_env

# Starta Tradingbot
python tradingbot.py