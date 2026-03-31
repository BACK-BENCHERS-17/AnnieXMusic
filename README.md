# KHUSHI Bot

A fast, feature-rich Telegram Music Bot built with **Pyrogram** (kurigram/pyrofork) and **PyTgCalls**. Stream high-quality audio & video directly in Telegram Voice Chats from YouTube, Spotify, SoundCloud, and more.

---

## Features

- High-quality audio & video streaming in Telegram Voice Chats
- YouTube, Spotify, SoundCloud, Apple Music, Resso support
- Queue management — loop, shuffle, seek, skip, stop
- 24/7 mode, volume control, speed control
- Auto-play, auto-end, channel play support
- Group security — antiflood, antilink, NSFW filter
- Song recommendation system (Hindi, Punjabi, Bollywood)
- Multi-language support
- Colored inline buttons with premium emoji icons

---

## Requirements

- Python 3.10+
- MongoDB (for database)
- Telegram API credentials
- FFmpeg + Node.js (for audio processing)

---

## Environment Variables

| Variable | Description |
|---|---|
| `API_ID` | Telegram API ID |
| `API_HASH` | Telegram API Hash |
| `BOT_TOKEN` | Bot token from @BotFather |
| `MONGO_DB_URI` | MongoDB connection string |
| `OWNER_ID` | Your Telegram user ID |
| `STRING_SESSIONS` | Pyrogram string session(s) for assistant |
| `SUPPORT_CHAT` | Support group link |
| `SUPPORT_CHANNEL` | Channel link |

---

## Deployment

### VPS / Local

```bash
git clone <your-repo-url>
cd KHUSHI
pip install -r requirements.txt
python3 -m KHUSHI
```

Or use the included start script:

```bash
bash start
```

### Docker

```bash
docker build -t khushi-bot .
docker run --env-file .env khushi-bot
```

### Heroku

1. Upload this repo to GitHub
2. Connect repo to Heroku
3. Set all environment variables in Config Vars
4. Deploy — uses `Dockerfile` with `CMD python3 -m KHUSHI`

### Railway

1. Upload repo to GitHub
2. Create new Railway project and deploy from GitHub
3. Set environment variables in Railway dashboard
4. Uses `railway.toml` config automatically

---

## Running

```bash
python3 -m KHUSHI
```

---

## License

MIT License
