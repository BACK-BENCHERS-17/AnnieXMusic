import re
from os import getenv
from dotenv import load_dotenv
from pyrogram import filters

# Load environment variables from .env file
load_dotenv()

# ── Core bot config ────────────────────────────────────────────────────────────
API_ID = int(getenv("API_ID", 27798659))
API_HASH = getenv("API_HASH", "26100c77cee02e5e34b2bbee58440f86")
BOT_TOKEN = getenv("BOT_TOKEN")

OWNER_ID = int(getenv("OWNER_ID", 7044783841))
OWNER_USERNAME = getenv("OWNER_USERNAME", "PGL_B4CHI")
BOT_USERNAME = getenv("BOT_USERNAME", "AnnieXRobot")
BOT_NAME = getenv("BOT_NAME", "˹𝐀ɴɴɪᴇ ✘ 𝙼ᴜsɪᴄ˼ ♪")
ASSUSERNAME = getenv("ASSUSERNAME", "musicxannie")

# ── Database & logging ─────────────────────────────────────────────────────────
MONGO_DB_URI = getenv("MONGO_DB_URI")
LOGGER_ID = int(getenv("LOGGER_ID", -1002014167331))

# ── Limits (durations in min/sec; sizes in bytes) ──────────────────────────────
DURATION_LIMIT_MIN = int(getenv("DURATION_LIMIT", 300))
SONG_DOWNLOAD_DURATION = int(getenv("SONG_DOWNLOAD_DURATION", "1200"))
SONG_DOWNLOAD_DURATION_LIMIT = int(getenv("SONG_DOWNLOAD_DURATION_LIMIT", "1800"))
TG_AUDIO_FILESIZE_LIMIT = int(getenv("TG_AUDIO_FILESIZE_LIMIT", "157286400"))
TG_VIDEO_FILESIZE_LIMIT = int(getenv("TG_VIDEO_FILESIZE_LIMIT", "1288490189"))
PLAYLIST_FETCH_LIMIT = int(getenv("PLAYLIST_FETCH_LIMIT", "30"))

# ── External APIs ──────────────────────────────────────────────────────────────
COOKIE_URL = getenv("COOKIE_URL")  # required (paste link)
API_URL = getenv("API_URL")        # optional
API_KEY = getenv("API_KEY")        # optional
DEEP_API = getenv("DEEP_API")      # optional

# ── Hosting / deployment ───────────────────────────────────────────────────────
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")
HEROKU_API_KEY = getenv("HEROKU_API_KEY")

# ── Git / updates ──────────────────────────────────────────────────────────────
UPSTREAM_REPO = getenv("UPSTREAM_REPO", "https://github.com/BACK-BENCHERS-17/AnnieXMusic")
UPSTREAM_BRANCH = getenv("UPSTREAM_BRANCH", "main")
GIT_TOKEN = getenv("GIT_TOKEN")  # needed if repo is private

# ── Support links ──────────────────────────────────────────────────────────────
SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/AnnieSupportGroup")
SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/AnnieSupportGroup")

# ── Assistant auto-leave ───────────────────────────────────────────────────────
AUTO_LEAVING_ASSISTANT = False
AUTO_LEAVE_ASSISTANT_TIME = int(getenv("ASSISTANT_LEAVE_TIME", "3600"))

# ── Debug ──────────────────────────────────────────────────────────────────────
DEBUG_IGNORE_LOG = True

# ── Spotify (optional) ─────────────────────────────────────────────────────────
SPOTIFY_CLIENT_ID = getenv("SPOTIFY_CLIENT_ID", "22b6125bfe224587b722d6815002db2b")
SPOTIFY_CLIENT_SECRET = getenv("SPOTIFY_CLIENT_SECRET", "c9c63c6fbf2f467c8bc68624851e9773")

# ── Session strings (optional) ─────────────────────────────────────────────────
STRING1 = getenv("STRING_SESSION")
STRING2 = getenv("STRING_SESSION2")
STRING3 = getenv("STRING_SESSION3")
STRING4 = getenv("STRING_SESSION4")
STRING5 = getenv("STRING_SESSION5")

# ── Media assets ───────────────────────────────────────────────────────────────
START_VIDS = [
    "https://telegra.ph/file/9b7e1b820c72a14d90be7.mp4",
    "https://telegra.ph/file/72f349b1386d6d9374a38.mp4",
    "https://telegra.ph/file/a4d90b0cb759b67d68644.mp4",
]
STICKERS = [
    "CAACAgUAAx0Cd6nKUAACASBl_rnalOle6g7qS-ry-aZ1ZpVEnwACgg8AAizLEFfI5wfykoCR4h4E",
    "CAACAgUAAx0Cd6nKUAACATJl_rsEJOsaaPSYGhU7bo7iEwL8AAPMDgACu2PYV8Vb8aT4_HUPHgQ",
]
HELP_IMG_URL = "https://files.catbox.moe/yg2vky.jpg"
PING_IMG_URL = "https://files.catbox.moe/040arl.png"
PING_VID_URL = "https://files.catbox.moe/3ivvgo.mp4"
PLAYLIST_IMG_URL = "https://files.catbox.moe/sn49xa.png"
STATS_VID_URL = "https://telegra.ph/file/e2ab6106ace2e95862372.mp4"
TELEGRAM_AUDIO_URL = "https://files.catbox.moe/qcydig.png"
TELEGRAM_VIDEO_URL = "https://files.catbox.moe/bgjn01.png"
STREAM_IMG_URL = "https://files.catbox.moe/452e1q.png"
SOUNCLOUD_IMG_URL = "https://files.catbox.moe/zhymxl.jpg"
YOUTUBE_IMG_URL = "https://files.catbox.moe/veykzq.jpg"
SPOTIFY_ARTIST_IMG_URL = SPOTIFY_ALBUM_IMG_URL = SPOTIFY_PLAYLIST_IMG_URL = YOUTUBE_IMG_URL

# ── Helpers ────────────────────────────────────────────────────────────────────
def time_to_seconds(time: str) -> int:
    return sum(int(x) * 60**i for i, x in enumerate(reversed(time.split(":"))))

DURATION_LIMIT = time_to_seconds(f"{DURATION_LIMIT_MIN}:00")

# ───── Bot Introduction Messages ───── #
AYU = ["<tg-emoji emoji-id=\"5296587316201005019\">💕</tg-emoji>", "<tg-emoji emoji-id=\"4958719848390591540\">🦋</tg-emoji>", "<tg-emoji emoji-id=\"4958587679361991667\">🔍</tg-emoji>", "<tg-emoji emoji-id=\"4956561910792192697\">🧪</tg-emoji>", "<tg-emoji emoji-id=\"6095843123252957701\">⚡️</tg-emoji>", "<tg-emoji emoji-id=\"4956222745814762495\">❤️‍🔥</tg-emoji>", "<tg-emoji emoji-id=\"5298709502491637271\">🌈</tg-emoji>", "<tg-emoji emoji-id=\"5361964771509808811\">🍷</tg-emoji>", "<tg-emoji emoji-id=\"6339298873365763591\">🥂</tg-emoji>", "<tg-emoji emoji-id=\"6192635880625150393\">🥃</tg-emoji>", "<tg-emoji emoji-id=\"5902433418699870159\">❤️</tg-emoji>", "<tg-emoji emoji-id=\"6021792097454002931\">🪄</tg-emoji>", "<tg-emoji emoji-id=\"6222054022895899468\">🧨</tg-emoji>"]
AYUV = [
    "<b>❅────✦ ʜᴇʟʟᴏ {0} ✦────❅</b>\n\n<b>◆ ᴜʟᴛʀᴀ ғᴀsᴛ ᴠᴄ ᴘʟᴀʏᴇʀ ғᴇᴀᴛᴜʀᴇs.</b>\n\n<b>✨ ғᴇᴀᴛᴜʀᴇs ⚡️</b>\n<b>◆ ʙᴏᴛ ғᴏʀ ᴛᴇʟᴇɢʀᴀᴍ ɢʀᴏᴜᴘs.</b>\n<b>◆ sᴜᴘᴇʀғᴀsᴛ ʟᴀɢ ғʀᴇᴇ ᴘʟᴀʏᴇʀ.</b>\n<b>◆ ʏᴏᴜ ᴄᴀɴ ᴘʟᴀʏ ᴍᴜsɪᴄ + ᴠɪᴅᴇᴏ.</b>\n<b>◆ ʟɪᴠᴇ sᴛʀᴇᴀᴍɪɴɢ.</b>\n<b>◆ ɴᴏ ᴘʀᴏᴍᴏ.</b>\n<b>◆ ʙᴇsᴛ sᴏᴜɴᴅ ǫᴜᴀʟɪᴛʏ.</b>\n<b>◆ 24×7 ʏᴏᴜ ᴄᴀɴ ᴘʟᴀʏ ᴍᴜsɪᴄ.</b>\n<b>◆ ᴀᴅᴅ ᴛʜɪs ʙᴏᴛ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴀɴᴅ ᴍᴀᴋᴇ ɪᴛ ᴀᴅᴍɪɴ ᴀɴᴅ ᴇɴᴊᴏʏ ᴍᴜsɪᴄ 🎵.</b>\n\n<b>▰▰▰▰▰▰▰▰▰▰▰▰▰</b>\n<b>➻ sᴜᴘᴘᴏʀᴛɪɴɢ ᴘʟᴀᴛғᴏʀᴍs ✧ ʏᴏᴜᴛᴜʙᴇ, sᴘᴏᴛɪғʏ, ʀᴇssᴏ, ᴀᴘᴘʟᴇᴍᴜsɪᴄ, sᴏᴜɴᴅᴄʟᴏᴜᴅ ᴇᴛᴄ.</b>\n<b>▰▰▰▰▰▰▰▰▰▰▰▰▰</b>\n<b>➻ ᴜᴘᴛɪᴍᴇ ✧ {2}</b>\n<b>➻ sᴇʀᴠᴇʀ sᴛᴏʀᴀɢᴇ ✧ {3}</b>\n<b>➻ ᴄᴘᴜ ʟᴏᴀᴅ ✧ {4}</b>\n<b>➻ ʀᴀᴍ ᴄᴏɴsᴜᴘᴛɪᴏɴ ✧ {5}</b>\n<b>➻ ᴜsᴇʀs ✧ {6}</b>\n<b>➻ ᴄʜᴀᴛs ✧ {7}</b>\n<b>▰▰▰▰▰▰▰▰▰▰▰▰▰</b>\n<b>❅─────✧❅✦❅✧─────❅</b>",
    "<b>❅────✦ ʜɪɪ {0} ✦────❅</b>\n\nɪ'ᴍ <b>{1}</b>, ᴀ ᴘᴏᴡᴇʀғᴜʟ ᴍᴜsɪᴄ ʙᴏᴛ.\n\n<b>◆ ᴜʟᴛʀᴀ ғᴀsᴛ ᴠᴄ ᴘʟᴀʏᴇʀ ғᴇᴀᴛᴜʀᴇs.</b>\n\n<b>✨ ғᴇᴀᴛᴜʀᴇs ⚡️</b>\n<b>◆ ʙᴏᴛ ғᴏʀ ᴛᴇʟᴇɢʀᴀᴍ ɢʀᴏᴜᴘs.</b>\n<b>◆ sᴜᴘᴇʀғᴀsᴛ ʟᴀɢ ғʀᴇᴇ ᴘʟᴀʏᴇʀ.</b>\n<b>◆ ʏᴏᴜ ᴄᴀɴ ᴘʟᴀʏ ᴍᴜsɪᴄ + ᴠɪᴅᴇᴏ.</b>\n<b>◆ ʟɪᴠᴇ sᴛʀᴇᴀᴍɪɴɢ.</b>\n<b>◆ ɴᴏ ᴘʀᴏᴍᴏ.</b>\n<b>◆ ʙᴇsᴛ sᴏᴜɴᴅ ǫᴜᴀʟɪᴛʏ.</b>\n<b>◆ 24×7 ʏᴏᴜ ᴄᴀɴ ᴘʟᴀʏ ᴍᴜsɪᴄ.</b>\n<b>◆ ᴀᴅᴅ ᴛʜɪs ʙᴏᴛ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴀɴᴅ ᴍᴀᴋᴇ ɪᴛ ᴀᴅᴍɪɴ ᴀɴᴅ ᴇɴᴊᴏʏ ᴍᴜsɪᴄ 🎵.</b>\n\n<b>▰▰▰▰▰▰▰▰▰▰▰▰▰</b>\n<b>➻ sᴜᴘᴘᴏʀᴛɪɴɢ ᴘʟᴀᴛғᴏʀᴍs ✧ ʏᴏᴜᴛᴜʙᴇ, sᴘᴏᴛɪғʏ, ʀᴇssᴏ, ᴀᴘᴘʟᴇᴍᴜsɪᴄ, sᴏᴜɴᴅᴄʟᴏᴜᴅ ᴇᴛᴄ.</b>\n<b>▰▰▰▰▰▰▰▰▰▰▰▰▰</b>\n<b>➻ ᴜᴘᴛɪᴍᴇ ✧ {2}</b>\n<b>➻ sᴇʀᴠᴇʀ sᴛᴏʀᴀɢᴇ ✧ {3}</b>\n<b>➻ ᴄᴘᴜ ʟᴏᴀᴅ ✧ {4}</b>\n<b>➻ ʀᴀᴍ ᴄᴏɴsᴜᴘᴛɪᴏɴ ✧ {5}</b>\n<b>➻ ᴜsᴇʀs ✧ {6}</b>\n<b>➻ ᴄʜᴀᴛs ✧ {7}</b>\n<b>▰▰▰▰▰▰▰▰▰▰▰▰▰</b>\n<b>❅─────✧❅✦❅✧─────❅</b>",
]

# ── Runtime structures ─────────────────────────────────────────────────────────
BANNED_USERS = filters.user()
adminlist, lyrical, votemode, autoclean, confirmer = {}, {}, {}, [], {}

# ── Minimal validation ─────────────────────────────────────────────────────────
if SUPPORT_CHANNEL and not re.match(r"^https?://", SUPPORT_CHANNEL):
    raise SystemExit("[ERROR] - Invalid SUPPORT_CHANNEL URL. Must start with https://")

if SUPPORT_CHAT and not re.match(r"^https?://", SUPPORT_CHAT):
    raise SystemExit("[ERROR] - Invalid SUPPORT_CHAT URL. Must start with https://")

if not COOKIE_URL:
    raise SystemExit("[ERROR] - COOKIE_URL is required.")

# Only allow these cookie link formats
if not re.match(r"^https://(batbin\.me|pastebin\.com)/[A-Za-z0-9]+$", COOKIE_URL):
    raise SystemExit("[ERROR] - Invalid COOKIE_URL. Use https://batbin.me/<id> or https://pastebin.com/<id>")
