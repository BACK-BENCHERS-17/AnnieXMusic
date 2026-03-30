"""KHUSHI — Ping with spoiler image."""

import random
from datetime import datetime

from pyrogram import enums, filters
from pyrogram.parser import Parser
from pyrogram.raw import functions as raw_func, types as raw_types
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from KHUSHI import app
from KHUSHI.core.call import JARVIS
from KHUSHI.utils import bot_sys_stats
from config import BANNED_USERS, PING_IMG_URL, START_IMGS, SUPPORT_CHAT

_BRAND = (
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
)


async def _send_ping_photo(client, message: Message, caption: str, markup: InlineKeyboardMarkup):
    img = PING_IMG_URL or random.choice(START_IMGS)

    # Tier 1 — raw API spoiler
    try:
        peer = await client.resolve_peer(message.chat.id)
        parser = Parser(client)
        parsed = await parser.parse(caption, mode=enums.ParseMode.HTML)
        text = parsed.get("message", "")
        entities = parsed.get("entities") or []
        raw_markup = await markup.write(client) if markup else None
        media = raw_types.InputMediaPhotoExternal(url=img, spoiler=True)
        await client.invoke(
            raw_func.messages.SendMedia(
                peer=peer,
                media=media,
                message=text,
                random_id=random.randint(-(2**63), 2**63 - 1),
                reply_markup=raw_markup,
                entities=entities,
            )
        )
        return
    except Exception:
        pass

    # Tier 2 — high-level reply_photo spoiler
    try:
        await message.reply_photo(
            photo=img,
            caption=caption,
            reply_markup=markup,
            has_spoiler=True,
        )
        return
    except Exception:
        pass

    # Tier 3 — plain text
    await message.reply_text(caption, reply_markup=markup, disable_web_page_preview=True)


def _bar(val, total=100, size=10):
    try:
        filled = int((float(str(val).replace("%", "")) / total) * size)
    except Exception:
        filled = 0
    return "█" * filled + "░" * (size - filled)


@app.on_message(filters.command(["kping", "ping"], prefixes=["/", "."]) & ~BANNED_USERS)
async def khushi_ping(client, message: Message):
    start = datetime.now()
    try:
        tgping = await JARVIS.ping()
    except Exception:
        tgping = "N/A"

    UP, CPU, RAM, DISK = await bot_sys_stats()
    ms = round((datetime.now() - start).microseconds / 1000, 2)

    caption = (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        f"<blockquote>"
        f"<emoji id='5042334757040423886'>⚡️</emoji> <b>ᴘɪɴɢ</b> : <code>{ms}ms</code>\n"
        f"<emoji id='5039598514980520994'>❤️‍🔥</emoji> <b>ᴠᴄ ᴘɪɴɢ</b> : <code>{tgping}</code>\n\n"
        f"<emoji id='5123230779593196220'>⏰</emoji> <b>ᴜᴘᴛɪᴍᴇ</b>  : <code>{UP}</code>\n"
        f"<emoji id='5972055534352733289'>💻</emoji> <b>ᴄᴘᴜ</b>  [{_bar(CPU)}]  <code>{CPU}</code>\n"
        f"<emoji id='5237799019329105246'>🧠</emoji> <b>ʀᴀᴍ</b>  [{_bar(RAM)}]  <code>{RAM}</code>\n"
        f"<emoji id='5462956611033117422'>📀</emoji> <b>ᴅɪsᴋ</b> [{_bar(DISK)}]  <code>{DISK}</code>"
        f"</blockquote>"
    )

    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("˹ꜱᴜᴘᴘᴏʀᴛ˼", url=f"https://t.me/{SUPPORT_CHAT.lstrip('@')}"),
    ]])

    await _send_ping_photo(client, message, caption, markup)
