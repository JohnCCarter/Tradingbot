#!/bin/bash
# Setup-script för Tradingbot-miljö
conda env create -f environment.yml || conda env update -f environment.yml
pip install -r requirements.txt || true
echo "Setup klar."
