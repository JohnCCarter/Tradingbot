#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# 1) Gå till scriptets katalog
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 2) Ladda .env om den finns — exporterar bara giltiga KEY=VALUE-rader
if [ -f ".env" ]; then
  echo "🔑 Laddar miljövariabler från .env…"
  # Endast rader som börjar med bokstav/underscore följt av = tecken
  grep -E '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=' .env |
  while IFS='=' read -r key val; do
    # Trimma eventuella omgivande blanksteg
    key="$(echo "$key"   | xargs)"
    val="$(echo "$val"   | xargs)"
    # Hoppa över blanksteg-keys eller kommentarer
    [[ -z "$key" || "$key" == \#* ]] && continue
    export "$key=$val"
  done
else
  echo "[WARNING] .env-fil hittades inte. Fortsätter utan extra miljövariabler."
fi

# 3) Initiera och aktivera Conda-miljö
ENV_NAME="tradingbot_env"
if command -v conda &> /dev/null; then
  echo "🐍 Initierar och aktiverar Conda-miljön: $ENV_NAME"
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate "$ENV_NAME"
else
  echo "[ERROR] Conda kunde inte hittas. Installera Miniconda eller Mambaforge först."
  exit 1
fi

# 4) Kontrollera att både api.py och tradingbot.py finns
for f in api.py tradingbot.py; do
  if [ ! -f "$f" ]; then
    echo "[ERROR] Filen '$f' saknas i $SCRIPT_DIR."
    exit 1
  fi
done

echo "[*] Miljö och filer validerade. Startar tjänster..."

# 5) Trappa signaler för att stänga båda processerna vid Ctrl+C
cleanup() {
  echo "🛑 Avslutar API- och bot-processerna..."
  kill -TERM $API_PID $BOT_PID 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

# 6) Starta API-servern
echo "▶️ Startar API-server (api.py)…"
python api.py &
API_PID=$!

# 7) Starta tradingbot
echo "▶️ Startar Tradingbot (tradingbot.py)…"
python tradingbot.py &
BOT_PID=$!

# 8) Vänta på att tradingbot-processen avslutas
wait $BOT_PID

# 9) Städa upp
cleanup
