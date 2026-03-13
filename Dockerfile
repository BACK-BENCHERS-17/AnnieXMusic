FROM python:3.12-slim

WORKDIR /app

ENV GIT_PYTHON_GIT_EXECUTABLE=/usr/bin/git

COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends git ffmpeg build-essential libssl-dev curl gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --upgrade -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python3", "-m", "ANNIEMUSIC"]
