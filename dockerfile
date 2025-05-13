FROM python:alpine

# 1) Uppgradera pip & installera grundläggande byggverktyg
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      wget \
      curl \
      gcc \
      libffi-dev \
      python3-dev \
      libssl-dev \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --upgrade pip

# 2) Kopiera in din environment.yml och skapa conda-miljön
WORKDIR /app
COPY environment.yml /app/
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh \
 && bash miniconda.sh -b -p /opt/miniconda \
 && rm miniconda.sh \
 && /opt/miniconda/bin/conda init \
 && /opt/miniconda/bin/conda env create -f /app/environment.yml \
 && /opt/miniconda/bin/conda clean -afy

# 3) Lägg conda-env bin-katalog först i PATH
ENV PATH="/opt/miniconda/envs/tradingbot_env/bin:$PATH"

# 4) Kopiera resten av koden
COPY . /app/

# 5) Skriv ditt startkommando
CMD ["python", "tradingbot.py"]
