FROM python:3.12-slim

WORKDIR /app

ENV GIT_PYTHON_GIT_EXECUTABLE=/usr/bin/git

COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends git ffmpeg build-essential libssl-dev curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --upgrade -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python3", "-m", "ANNIEMUSIC"]
