#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
# script_start.sh – Startar Tradingbot i rätt miljö

# 1) Bestäm scriptets katalog och byt dit
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 2) Ladda .env om den finns, exportera alla variabler
if [ -f ".env" ]; then
  echo "🔑 Laddar miljövariabler från .env…"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
else
  echo "[WARNING] .env file not found. Continuing, but environment variables may be missing."
fi

# 3) Initiera Conda om det finns, och aktivera din miljö
ENV_NAME="tradingbot_env"
if command -v conda &> /dev/null; then
  echo "🐍 Initierar Conda…"
  # Källa till conda.sh så att 'conda activate' fungerar i non-login shell
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
  echo "🚀 Aktiverar miljö: $ENV_NAME"
  # Kontrollera att miljön finns
  if ! conda env list | grep -q "^$ENV_NAME\s"; then
    echo "[ERROR] Conda environment '$ENV_NAME' not found."
    exit 1
  fi
  conda activate "$ENV_NAME"
else
  echo "❌ Fel: Conda hittades inte. Se till att du har installerat Miniconda eller Mambaforge."
  exit 1
fi

# 4) Kontrollera att scriptet finns
if [ ! -f "tradingbot.py" ]; then
  echo "[ERROR] tradingbot.py not found in $SCRIPT_DIR."
  exit 1
fi

echo "[*] Environment and files validated. Launching Tradingbot..."

# 5) Kör tradingbot-skriptet
echo "▶️ Kör tradingbot.py…"
exec python tradingbot.py
