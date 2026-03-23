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
- `LOGGER_ID` - Telegram chat ID for logging

## YouTube Streaming (No Cookies Needed)
Uses yt-dlp with `android_vr` + `ios_downgraded` player clients — works on Replit/cloud without any cookies or COOKIE_URL. The bot's internal API at port 8080 (`/api/yturl`) is used for fast stream URL fetching.

## YouTube Search — Permanent Free Solution (Invidious API)
Search is powered by **Invidious** — a free, open-source YouTube frontend with a public API.
- **No API key needed, no quota limits, completely free forever**
- 10 public Invidious instances in rotation — if one is down, others take over automatically
- Speed: ~300-600ms (much faster than yt-dlp search 2-5s)
- Files: `ANNIEMUSIC/utils/yt_api.py` (async bot helper), `webserver.py` (`_search_via_ytapi` + `/api/search`)
- Priority: Invidious → YouTube Data API v3 (if `YOUTUBE_API_KEY` set) → yt-dlp (final fallback)
- `OWNER_ID` - Owner's Telegram user ID (Required Secret)

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
