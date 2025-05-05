#!/usr/bin/env bash
# script.sh – Sätter upp Tradingbot-miljön på en ny server/VM

set -euo pipefail
IFS=$'\n\t'

# 1) Konfigurera variabler
env_name="tradingbot_env"
bot_dir="/opt/Tradingbot"
repo_url="https://github.com/JohnCCarter/Tradingbot.git"

# 2) Uppdatera paketlista och installera grundläggande verktyg
echo "🔄 Uppdaterar apt och installerar git, curl, wget, bzip2…"
sudo apt-get update
sudo apt-get install -y git curl wget bzip2

# 3) Installera Miniconda om det saknas
if ! command -v conda &> /dev/null; then
  echo "🐍 Installerar Miniconda…"
  tmp_installer="$(mktemp)"
  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O "$tmp_installer"
  bash "$tmp_installer" -b -p "$HOME/miniconda3"
  rm "$tmp_installer"
  
  # Konfigurera conda-kanaler för att eliminera FutureWarnings
echo "⚙️ Konfigurerar conda-kanaler…"
  "$HOME/miniconda3/bin/conda" config --system --add channels conda-forge
  "$HOME/miniconda3/bin/conda" config --system --add channels defaults
else
  echo "✅ Conda redan installerat."
fi

# 4) Initiera Conda så att `conda activate` fungerar
if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
  # shellcheck disable=SC1091
  source "$HOME/miniconda3/etc/profile.d/conda.sh"
else
  conda init bash
  # shellcheck disable=SC1091
  source "$HOME/.bashrc"
fi

# 5) Klona eller uppdatera repot
if [ ! -d "$bot_dir" ]; then
  echo "📥 Klonar repo till $bot_dir…"
  sudo git clone "$repo_url" "$bot_dir"
  sudo chown -R "$USER":"$USER" "$bot_dir"
else
  echo "🔄 Uppdaterar befintligt repo i $bot_dir…"
  cd "$bot_dir"
  git pull --ff-only
fi

# 6) Byt till botkatalogen
cd "$bot_dir"

# 7) Ladda .env om den finns\if [ -f ".env" ]; then
  echo "🔑 Laddar miljövariabler från .env…"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# 8) Skapa eller uppdatera conda-miljön
if conda env list | grep -q "^${env_name}[[:space:]]"; then
  echo "♻️ Uppdaterar befintlig conda-miljö '$env_name'…"
  conda env update -n "$env_name" -f environment.yml --prune
else
  echo "✨ Skapar conda-miljö '$env_name'…"
  conda env create -n "$env_name" -f environment.yml
fi

# 9) Klart
echo "🎉 Setup klar! Kör ./script_start.sh för att starta Tradingbot."
