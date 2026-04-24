# KHUSHI — Telegram Music Bot

## Overview
KHUSHI (Annie Music Bot) is a feature-rich Telegram music bot built with Pyrogram + PyTgCalls targeting Indian users. It streams audio/video in group voice chats with a focus on Hindi/Punjabi/Bollywood music. Supports YouTube, Spotify, SoundCloud, Apple Music, and Resso. Includes a built-in web player (Mini App) at t.me/VcAnnieBot/annie with song suggestions, trending music, search, liked songs, and download.

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

## Web Player — Ultra-Fast Proxy Stream (`/api/proxy`)
The web player at port 5000 now uses a **proxy streaming** endpoint:
- `/api/proxy?v={videoId}` — extracts the YouTube CDN URL and pipes audio directly to the browser (no local download, sub-second start)
- Falls back to `/api/audio` (local file) if already cached on disk
- Supports byte-range requests for seeking
- CDN URLs cached in-process with auto-expiry to avoid repeated extraction
- File deletion: proxy mode never writes to disk; `/api/audio` fallback uses existing disk-management logic

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

## Railway Deployment Fix (April 2026)
- **ButtonStyle on Railway**: pyrofork 2.3.69 has `button_style.py` but does NOT export `ButtonStyle` from `pyrogram/enums/__init__.py` on a clean install. On Replit it worked because base pyrogram was already present. Fixed in `Dockerfile` by adding a `RUN python3` patch step that: (1) creates `button_style.py` if missing (IntEnum stub), (2) appends `from .button_style import ButtonStyle` to `__init__.py` if not already there, then verifies the import before proceeding. Build now prints `BUILD OK: pyrogram X.X.X | ButtonStyle: ButtonStyle.SUCCESS`.

## Bug Fixes (April 2026 — Session 4)
- **Channel play fixed** (`/cplay`, `/cvplay`): `_handle_play` in `KHUSHI/plugins/play.py` now detects channel-prefixed commands, resolves the linked channel ID via `get_cmode`, and correctly routes VC operations (join_call, put_queue, is_active_chat, db) to the channel while keeping notifications in the group. Variables renamed: `msg_chat_id` (group) and `vc_chat_id` (channel or group).
- **Seek `DocumentInvalid` fixed**: `kseek` handler now blocks seeking on live streams (checks `dur == "Live"` or `file.startswith("live_")`). Exception handler distinguishes `DocumentInvalid`, `NotInCallError`, `ConnectionNotFound`, `FileError` and `AssistantErr` with specific human-readable messages.
- **Bot auto-suggestions improved**: `_fetch_reco_songs` in `KHUSHI/core/call.py` now uses `yt_api_related_videos` (Invidious `recommendedVideos` — actual YouTube algorithm) as the primary source for post-queue suggestions. Keyword search is now a secondary fallback, static pool is the last resort.
- **Web player suggestions improved**: `/api/suggested` endpoint in `KHUSHI/utils/webserver.py` now uses `yt_api_related_videos` as the primary source when a video ID is present. Keyword search and trending are secondary/tertiary fallbacks.
- **`yt_api_related_videos` added** to `KHUSHI/utils/yt_api.py`: fetches `recommendedVideos` from Invidious for a given video ID, filters live streams and long compilations (>12 min).

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

## UI Cleanup (April 2026 — Session 5)
- **Brand row removed**: The `🧸 ᴀɴɴɪᴇ` blockquote header that prefixed every bot reply has been stripped everywhere.
  - `KHUSHI/utils/ui.py` — `BRAND = ""`, `brand_block()` returns `""`, `msg()` and `panel()` no longer prepend it.
  - All `<blockquote>{_BRAND}</blockquote>\n\n` fragments removed across `KHUSHI/plugins/*.py` and `KHUSHI/core/*.py`.
  - Local multi-line `_BRAND = ( ... )` definitions in `ping.py / song.py / queue.py / nsfw.py / language.py / security.py / broadcast.py` set to `""`.
  - `sudo.py._r()` now returns a single clean blockquote.
  - `strings/helpers.py` — `_ANNIE = ""`.
  - `strings/langs/en.yml` — 54 brand prefixes removed.
  - `KHUSHI/__main__.py` and `KHUSHI/core/bot.py / call.py` — visible "ᴀɴɴɪᴇ" labels replaced with "ᴋʜᴜsʜɪ".
- **Result**: every message now has a single clean blockquote with its premium emojis — no redundant brand row.
- **Premium emojis (Session 6)**: `KHUSHI/utils/ui.py` rebuilt with a `_P` map of `(custom_emoji_id, fallback)` tuples covering 50+ keys (status / music / actions / indicators / system). The `_emoji()` helper renders each as a `<emoji id="...">unicode</emoji>` HTML entity that Telegram parses as a real premium custom emoji while gracefully falling back to plain unicode on non-premium clients. New keys added: videocam, disc, timer, snow, heart, rose, globe, user, brain, download, playpause, ping, vc, uptime, cpu, ram, disk, stats, settings, computer.
- **/start fix**: removed stray unary-`+` before `START_TEXT.format(...)` at three sites in `KHUSHI/plugins/start.py` (left over from a prior bulk edit) that caused a TypeError and made `/start` reply nothing.
- **/play preview at top**: `_send_stream_msg` in `KHUSHI/plugins/play.py` now uses the same invisible-link / `invert_media` trick as `core/call.py._notify_now_playing`, anchoring a static catbox.moe video so the now-playing preview renders ABOVE the caption — no separate thumbnail photo.
- **First-song thumb removed (Session 7)**: `KHUSHI/utils/stream/stream.py._send_stream_msg` was still doing `app.send_photo(...)` for the very first track of a session, which left a stray thumbnail photo. Switched it to the same invisible-link / `invert_media` helper so the first track now renders identically to subsequent ones — clean text + animated preview at top.
- **Premium emoji IDs refreshed (Session 7)**: replaced the IDs in `KHUSHI/utils/ui.py` with the user-provided validated set (66 entries). New keys added: `check2`, `notes2`, `sax`, `tv`, `dizzy`, `announce`, `bookmark`, `butterfly`, `user2`, `tired`, `camera`, `camera2`, `left`, `right`, `stats2`, `gear`. Updated IDs for `music`, `notes`, `mic`, `live`, `sparkle`, `clock`, `repeat`, `shuffle`, `seek_fwd`, `queue`, `lock`, `crown`, `globe`, `download`, `vc`, `warn`, `heart`, `cross`, `disk`, `settings`, `check`.
- **Custom-emoji TAG fix (Session 8)**: every premium emoji was rendering as plain unicode because the wrapper used `<emoji id="...">x</emoji>` — Pyrogram's HTML parser **only** recognises `<tg-emoji emoji-id="...">x</tg-emoji>`, so the wrong tag was silently stripped, leaving just the unicode fallback. Fixed `_emoji()` in `KHUSHI/utils/ui.py` to emit the correct `<tg-emoji emoji-id="...">…</tg-emoji>` tag, which Pyrogram converts into a proper `MessageEntityCustomEmoji` entity. Also extended `_safe_text()` in `start.py` to strip both legacy and new tag forms when sanitising captions/buttons.
- **Assistant peer-resolution hardening (Session 7)**: the previous M1 strategy in `KHUSHI/core/call.py` injected the bot's `access_hash` directly into the assistant's SQLite — but `access_hash` is per-account in Telegram, so this poisoned the assistant's storage and `assistant.play()` still failed with `CHANNEL_INVALID`. Replaced M1 (and the M3a "is_member" branch) with an `await _ci_raw.get_dialogs(limit=200)` sweep + an `updates.GetState()` ping, so Telegram pushes the assistant the correct per-account access_hash. This fixes the case where the assistant is already in the VC / group but `/play` reports "ᴀssɪsᴛᴀɴᴛ ᴩᴇᴇʀ ʀᴇsᴏʟᴜᴛɪᴏɴ ꜰᴀɪʟᴇᴅ" for new 13-digit channel IDs.

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
