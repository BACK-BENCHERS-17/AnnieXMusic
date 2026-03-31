# KHUSHI — Telegram Music Bot

## Overview
KHUSHI is a feature-rich Telegram music bot built with Pyrogram + PyTgCalls targeting Indian users. It streams audio/video in group voice chats with a focus on Hindi/Punjabi/Bollywood music. Supports YouTube, Spotify, SoundCloud, Apple Music, and Resso.

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

## KHUSHI — Main Bot Package (Migrated March 2026)
The bot has been fully migrated from ANNIEMUSIC to KHUSHI. KHUSHI is now fully self-contained with its own core, platforms, and utils.

### Structure
```
KHUSHI/
├── __init__.py       # Fully independent core — own app, userbot, platforms
├── __main__.py       # Entry point — run with: python -m KHUSHI
├── core/             # Bot core (bot.py, userbot.py, call.py, mongo.py)
├── platforms/        # YouTube, Spotify, Apple, SoundCloud, Resso, Telegram, Carbon
├── plugins/
│   ├── start.py      # /kstart /khelp — premium UI with blockquotes & emojis
│   ├── ping.py       # /kping — super UI with progress bars
│   ├── controls.py   # pause/resume/skip/stop/loop/shuffle/volume/247
│   ├── queue.py      # /queue — premium queue card UI
│   ├── play.py       # /play /vplay — full YouTube/Spotify/SoundCloud/etc.
│   ├── broadcast.py  # /bc /broadcast — -nf -pin -pinloud -user flags
│   └── sudo.py       # gban/ungban/block/unblock/maintenance/addsudo/delsudo
├── utils/            # Full utils — database, formatters, inline, stream, decorators
├── web/
│   └── index.html    # KHUSHI web player
├── webserver.py      # Thin wrapper — serves KHUSHI/web/ using main webserver
└── assets/           # Assets (images, fonts)
```

### Migration Notes (Circular Import Fixes — March 2026)
All `from KHUSHI import app/userbot` at module level were converted to lazy imports inside functions to eliminate circular imports during package initialization:
- `KHUSHI/platforms/Telegram.py` — lazy import in `download()`
- `KHUSHI/utils/decorators.py` — lazy import in `KhushiAdminCheck` and `KhushiActualAdmin` wrappers
- `KHUSHI/utils/channelplay.py` — lazy import in `get_channeplayCB()`
- `KHUSHI/utils/database.py` — lazy import in `get_client()`
- `KHUSHI/utils/extraction.py` — lazy import in `extract_user()`
- `KHUSHI/utils/errors.py` — lazy import in `send_large_error()`, `handle_trace()`, `capture_err` wrapper
- `KHUSHI/utils/inline/help.py` — lazy import in `private_help_panel()`
- `KHUSHI/utils/inline/start.py` — created fresh with lazy imports (was missing)
- Root `webserver.py` — all `ANNIEMUSIC.*` imports changed to `KHUSHI.*`

### Key Features
- **Fully self-contained**: No dependency on ANNIEMUSIC folder
- **New UI**: All messages use `<blockquote>`, premium emojis, progress bars
- **8/8 plugins loading successfully**
- **Workflow**: "KHUSHI Bot" — `python -m KHUSHI`
- **Web player**: KHUSHI/web/index.html

## Bug Fixes (March 2026 — Session 2)
- **`/start` crash fix**: `asyncio.gather(get_served_chats, get_served_users, ...)` wrapped in try-except — MongoDB DNS failures no longer crash the handler, bot sends start message with fallback stats
- **`stream_call` crash fix**: `group_assistant()` call in `ANNIEMUSIC/core/call.py` wrapped in try-except — MongoDB DNS failures no longer crash stream_call
- **`auto_end` crash fix**: `is_autoend()` in `autoleave.py` wrapped in try-except — loop continues on DB failure instead of crashing
- **KHUSHI fast stream module**: `KHUSHI/utils/fast_stream.py` created — full millisecond-level stream with parallel webserver+SmartYTDL race, YouTube search, and background caching

## KHUSHI Fast Stream Module (`KHUSHI/utils/fast_stream.py`)
Standalone fast stream engine for KHUSHI bot, mirrors ANNIEMUSIC's `fast_get_stream`:
- `fast_get_stream(vid)` — Returns file path or CDN URL in ms (local→webserver→SmartYTDL→full download)
- `search_youtube(query, limit)` — Async YouTube search returning title/url/duration/thumbnail
- `search_and_stream(query)` — Combined search+stream: search YouTube → return (stream_path, info)
- Background caching: auto-downloads to local after first stream URL extraction
- Uses ANNIEMUSIC's SmartYTDL engine (android_vr, ios, web_safari multi-client bypass)

## Customizations (March 2026)
- **KHUSHI Branding in Logs**: All `LOGGER("ANNIEMUSIC")` calls changed to `LOGGER("KHUSHI")` in `__main__.py`
- **New Attractive UI**: All command buttons updated with premium emojis (🎵 ⏯ 🔀 🔁 ⏩ ⚡️ ❄️ 📻 📊 ⚙️ etc.)
- **Premium Icon Support**: `icon_custom_emoji_id` added to help and start panel buttons
- **Player Branding**: "ᴀɴɴɪᴇ ᴘʟᴀʏᴇʀ" → "🎵 ᴋʜᴜsʜɪ ᴘʟᴀʏᴇʀ" in player inline buttons
- **Autoplay Messages**: "ᴀɴɴɪᴇ" → "ᴋʜᴜsʜɪ" in autoplay.py and callback.py visible messages
- **Menu Button**: Bot menu button text changed from "ANNIE" to "KHUSHI"
- **Welcome Removed**: Removed group welcome function and images (welcome.png, couple.png)

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
