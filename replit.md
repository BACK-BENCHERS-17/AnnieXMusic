# KHUSHI Bot — Replit Setup

A Telegram Music Bot (Pyrogram + PyTgCalls) that streams audio/video in Telegram Voice Chats from YouTube, Spotify, SoundCloud, and more.

## How to run

```
python3 -m KHUSHI
```

The **"KHUSHI Bot"** workflow runs this automatically.

## Environment variables set

All credentials are stored as Replit environment variables (shared):

| Variable | Description |
|---|---|
| `API_ID` | Telegram API ID |
| `API_HASH` | Telegram API Hash |
| `BOT_TOKEN` | Bot token from @BotFather |
| `MONGO_DB_URI` | MongoDB connection string |
| `STRING_SESSION2` | Pyrogram assistant session (userbot) |
| `COOKIE_URL` | External cookie source URL |
| `YOUTUBE_COOKIES_B64` | Base64-encoded YouTube cookies.txt |
| `LOGGER_ID` | Telegram log channel ID |
| `OWNER_ID` | Bot owner Telegram user ID |

## Known warnings on startup

- **Log channel not accessible** — Add the bot as admin to the LOGGER_ID channel, or update `LOGGER_ID` to a valid channel.
- **Node.js NOT found** — `web_safari` yt-dlp client is unavailable; `android_vr` (the primary client) still works fine.

## Stack

- Python 3.12
- pyrogram 2.2.19
- py-tgcalls 2.2.11 / ntgcalls 2.1.0
- MongoDB (Motor async driver)
- yt-dlp with android_vr client (no cookies needed for most downloads)

## User preferences

- Keep existing project structure — do not restructure or migrate.
