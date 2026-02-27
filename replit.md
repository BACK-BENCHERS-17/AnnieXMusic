# AnnieMusic Telegram Bot

## Overview
AnnieMusic is a Telegram Music Bot that streams audio/video in Telegram group voice chats. It supports multiple music platforms including YouTube, Spotify, SoundCloud, Apple Music, and Resso.

## Project Structure
```
ANNIEMUSIC/
├── core/          # Bot core components (bot, userbot, calls, mongo)
├── plugins/       # Bot command handlers
│   ├── admins/    # Admin commands (pause, resume, skip, etc.)
│   ├── bot/       # Bot management (help, settings, start)
│   ├── play/      # Music playback commands
│   ├── sudo/      # Sudo/owner commands
│   └── tools/     # Utility commands
├── platforms/     # Music platform APIs
├── utils/         # Helper utilities
└── assets/        # Static assets (fonts, images)
strings/           # Language files (en, hi, ru, ar, tr)
config.py          # Configuration from environment
```

## Required Secrets
- `API_ID` - Telegram API ID (from https://my.telegram.org)
- `API_HASH` - Telegram API Hash
- `BOT_TOKEN` - Bot token from @BotFather
- `STRING_SESSION` - Pyrogram session string for assistant account
- `MONGO_DB_URI` - MongoDB connection URI
- `COOKIE_URL` - YouTube cookies URL (batbin.me or pastebin.com)
- `LOGGER_ID` - Telegram chat ID for logging
- `OWNER_ID` - Owner's Telegram user ID

## Running the Bot
The bot runs as a console workflow:
```bash
python -m ANNIEMUSIC
```

## Dependencies
- Python 3.12
- kurigram (Pyrogram fork) - Telegram MTProto API
- py-tgcalls - Voice chat streaming
- motor - Async MongoDB driver
- yt-dlp - YouTube downloading
- ffmpeg - Audio/video processing

## System Dependencies
- ffmpeg
- libGL, libGLU, mesa (for OpenCV)

## Customizations (December 2025)
- **Developer Branding**: Changed developer name to "⎯꯭̽ 𝚱 𝚮 𝐔 𝛅 𝚮 𝚰⥱" (PGL_B4CHI) everywhere
- **Developer Link**: Updated all developer/support links to https://t.me/PGL_B4CHI
- **Owner Username**: Changed to PGL_B4CHI in config.py
- **Support Chat/Channel**: Updated to AnnieSupportGroup
- **Spoiler Effects**: Added has_spoiler=True to all media (photos/videos) sent by the bot
- **Heart Reactions**: Added ❤ reaction to /start command messages

### Files Modified:
- strings/langs/*.yml (all 5 language files)
- config.py (owner, support links, upstream repo)
- ANNIEMUSIC/plugins/bot/start.py (reactions + spoilers)
- ANNIEMUSIC/plugins/bot/repo.py (branding + spoilers)
- ANNIEMUSIC/plugins/Kishu/wishcute.py (support chat)
- ANNIEMUSIC/core/userbot.py (groups to join)
- ANNIEMUSIC/utils/stream/stream.py (spoilers)
- ANNIEMUSIC/core/call.py (spoilers)
- ANNIEMUSIC/utils/reactions.py (new file for heart reactions)
