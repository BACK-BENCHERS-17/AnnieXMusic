"""KHUSHI — Ping with new super UI."""

from datetime import datetime

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from KHUSHI import app
from KHUSHI.core.call import JARVIS
from ANNIEMUSIC.utils import bot_sys_stats
from config import BANNED_USERS, SUPPORT_CHAT

_BRAND = (
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
)


@app.on_message(filters.command("kping", prefixes=["/", "."]) & ~BANNED_USERS)
async def khushi_ping(_, message: Message):
    start = datetime.now()
    try:
        tgping = await JARVIS.ping()
    except Exception:
        tgping = "N/A"

    UP, CPU, RAM, DISK = await bot_sys_stats()
    ms = (datetime.now() - start).microseconds / 1000

    def _bar(val, total=100, size=10):
        filled = int((val / total) * size)
        return "█" * filled + "░" * (size - filled)

    text = (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        f"<blockquote>"
        f"<emoji id='5042334757040423886'>⚡️</emoji> <b>PING</b> : <code>{ms}ms</code>\n"
        f"<emoji id='5039598514980520994'>❤️‍🔥</emoji> <b>VC PING</b> : <code>{tgping}</code>\n\n"
        f"<emoji id='5123230779593196220'>⏰</emoji> <b>UPTIME</b>  : <code>{UP}</code>\n"
        f"<emoji id='5972055534352733289'>💻</emoji> <b>CPU</b>  [{_bar(float(str(CPU).replace('%','')))}]  <code>{CPU}</code>\n"
        f"<emoji id='5237799019329105246'>🧠</emoji> <b>RAM</b>  [{_bar(float(str(RAM).replace('%','')))}]  <code>{RAM}</code>\n"
        f"<emoji id='5462956611033117422'>📀</emoji> <b>DISK</b> [{_bar(float(str(DISK).replace('%','')))}]  <code>{DISK}</code>"
        f"</blockquote>"
    )

    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("˹ꜱᴜᴘᴘᴏʀᴛ˼", url=f"https://t.me/{SUPPORT_CHAT.lstrip('@')}"),
        ]]),
    )
