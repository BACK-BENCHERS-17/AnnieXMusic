FROM python:3.12-slim

WORKDIR /app

ENV GIT_PYTHON_GIT_EXECUTABLE=/usr/bin/git
ENV DEBIAN_FRONTEND=noninteractive

# Install core build dependencies for Python packages (especially ntgcalls)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    build-essential \
    libssl-dev \
    curl \
    gnupg \
    cmake \
    pkg-config \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    libswscale-dev \
    nodejs && \
    pip install --no-cache-dir --upgrade pip && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

CMD ["python3", "-m", "ANNIEMUSIC"]
