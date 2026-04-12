FROM python:3.12-slim

WORKDIR /app

ENV GIT_PYTHON_GIT_EXECUTABLE=/usr/bin/git
ENV PYTHONUNBUFFERED=1

# Install system dependencies + Node.js 20
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    ffmpeg \
    build-essential \
    libssl-dev \
    curl \
    gnupg \
    cmake \
    g++ \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libpostproc-dev \
    libopus-dev \
    libvpx-dev \
    pkg-config && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy patch script and run it to fix ButtonStyle export in pyrogram.enums
COPY scripts/patch_pyrogram.py /tmp/patch_pyrogram.py
RUN python3 /tmp/patch_pyrogram.py

# Verify the patch worked — FAIL the build loudly if ButtonStyle is broken
RUN python3 -c "
import pyrogram
from pyrogram.enums import ButtonStyle
from pyrogram.types import InlineKeyboardButton
import inspect
src = inspect.getsource(InlineKeyboardButton)
has_kbs = 'KeyboardButtonStyle' in src
print('BUILD OK: pyrogram', pyrogram.__version__, '| ButtonStyle:', ButtonStyle.SUCCESS, '| write() KeyboardButtonStyle:', has_kbs)
if not has_kbs:
    print('WARNING: InlineKeyboardButton.write() is missing KeyboardButtonStyle support!')
    print('Button colors will NOT show. Install pyrofork from git for full support.')
"

# Copy everything else
COPY . .

# Run the bot
CMD ["python3", "-m", "KHUSHI"]
