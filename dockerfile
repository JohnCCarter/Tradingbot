# Start with a base image that supports Python 3.9
FROM python:3.9-slim

# Install system dependencies required for ta-lib
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    curl \
    gcc \
    libffi-dev \
    python3-dev \
    libssl-dev \
    libta-lib0-dev \
    ta-lib \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the environment.yml file into the Docker image
COPY environment.yml /app/

# Install Miniconda to manage Conda environments
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh && \
    bash miniconda.sh -b -p /opt/miniconda && \
    rm miniconda.sh && \
    /opt/miniconda/bin/conda init && \
    /opt/miniconda/bin/conda env create -f /app/environment.yml && \
    /opt/miniconda/bin/conda clean -afy

# Ensure the Conda environment is activated by default
ENV PATH="/opt/miniconda/envs/$(head -1 environment.yml | cut -d':' -f2 | tr -d ' ')/bin:$PATH"
ENV CONDA_DEFAULT_ENV="$(head -1 environment.yml | cut -d':' -f2 | tr -d ' ')"

# Copy the rest of your application code into the Docker image
COPY . /app/

# Specify the command to run your application
CMD ["python", "your_application.py"]
