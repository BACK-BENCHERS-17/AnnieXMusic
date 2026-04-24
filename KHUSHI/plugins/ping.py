"""KHUSHI — Ping."""

import random
from datetime import datetime

from pyrogram import enums, filters
from pyrogram.parser import Parser
from pyrogram.raw import functions as raw_func, types as raw_types
from pyrogram.types import InlineKeyboardMarkup, Message

from KHUSHI.utils.inline import InlineKeyboardButton

from KHUSHI import app
from KHUSHI.core.call import JARVIS
from KHUSHI.utils import bot_sys_stats
from KHUSHI.utils.ui import E as _E_UI
from config import BANNED_USERS, PING_IMG_URL, START_IMGS, SUPPORT_CHAT

_BRAND = ""
_E = {
    "ping":   _E_UI["ping"],
    "vc":     _E_UI["vc"],
    "up":     _E_UI["uptime"],
    "cpu":    _E_UI["cpu"],
    "ram":    _E_UI["ram"],
    "disk":   _E_UI["disk"],
    "zap":    _E_UI["zap"],
}


async def _send_ping_photo(client, message: Message, caption: str, markup: InlineKeyboardMarkup):
    img = PING_IMG_URL or random.choice(START_IMGS)
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
    await message.reply_text(caption, reply_markup=markup, disable_web_page_preview=True)


@app.on_message(filters.command(["ping"], prefixes=["/", "."]) & ~BANNED_USERS)
async def khushi_ping(client, message: Message):
    start = datetime.now()
    try:
        tgping = await JARVIS.ping()
    except Exception:
        tgping = "N/A"

    UP, CPU, RAM, DISK = await bot_sys_stats()
    ms = round((datetime.now() - start).microseconds / 1000, 2)

    caption = (
        f"<blockquote>"
        f"┌────── ˹ ᴘɪɴɢ ˼─── ⏤‌‌●\n"
        f"┆{_E['ping']} <b>ᴘɪɴɢ :</b> <code>{ms} ᴍs</code>\n"
        f"┆{_E['vc']} <b>ᴠᴄ ᴘɪɴɢ :</b> <code>{tgping}</code>\n"
        f"├──────────────────────\n"
        f"┆{_E['up']} <b>ᴜᴘᴛɪᴍᴇ :</b> <code>{UP}</code>\n"
        f"┆{_E['cpu']} <b>ᴄᴘᴜ :</b> <code>{CPU}</code>\n"
        f"┆{_E['ram']} <b>ʀᴀᴍ :</b> <code>{RAM}</code>\n"
        f"┆{_E['disk']} <b>ᴅɪsᴋ :</b> <code>{DISK}</code>\n"
        f"└──────────────────────●"
        f"</blockquote>"
    )

    _sc = SUPPORT_CHAT if SUPPORT_CHAT.startswith("http") else f"https://t.me/{SUPPORT_CHAT.lstrip('@')}"
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("˹ꜱᴜᴘᴘᴏʀᴛ˼", url=_sc, style="primary"),
    ]])

    await _send_ping_photo(client, message, caption, markup)
    try:
        await message.delete()
    except Exception:
        pass
