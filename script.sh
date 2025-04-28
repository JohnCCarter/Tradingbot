#!/bin/bash
# script.sh - Setup Tradingbot on Azure Linux VM

# Uppdatera paketlistor och installera nödvändiga paket
sudo apt-get update
sudo apt-get install -y git python3 python3-pip

# Skapa mappen om den inte finns och ge rätt ägare
sudo mkdir -p /opt/Tradingbot
sudo chown $USER:$USER /opt/Tradingbot

# Klona ditt repo (korrigerat mellanslag och sökväg)
git clone https://github.com/JohnCCarter/Tradingbot.git /opt/Tradingbot

# Gå till projektmappen
cd /opt/Tradingbot

# Installera pip-bibliotek (eller använd conda om du föredrar det)
if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt
elif [ -f environment.yml ]; then
    pip3 install -r environment.yml
fi

# Kopiera .env-filen (lägg till din .env manuellt eller via Azure Key Vault för säkerhet)
# cp /path/to/your/.env .env

# Starta boten i bakgrunden med nohup
nohup python3 tradingbot.py > tradingbot.log 2>&1 &

echo "Tradingbot installation och start klar!"

# Script för att aktivera conda-miljön och starta tradingboten

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
