"""KHUSHI — Queue display with premium UI."""

from pyrogram import filters
from pyrogram.types import Message

from KHUSHI import app
from KHUSHI.misc import db
from KHUSHI.utils import seconds_to_min
from KHUSHI.utils.database import get_cmode, is_active_chat
from config import BANNED_USERS

_BRAND = ""

_E = {
    "fire":   '<emoji id="5042225965518816316">❤️\u200d🔥</emoji>',
    "dot":    '<emoji id="5972072533833289156">🔹</emoji>',
    "music":  '<emoji id="5994566609002303309">🎵</emoji>',
    "zap":    '<emoji id="5042334757040423886">⚡️</emoji>',
    "mic":    '<emoji id="6030722571412967168">🎤</emoji>',
    "clock":  '<emoji id="5123230779593196220">⏰</emoji>',
    "star":   '<emoji id="5039827436737397847">✨</emoji>',
    "warn":   '<emoji id="5420323339723881652">⚠️</emoji>',
    "list":   '<emoji id="6039454987250044861">🔊</emoji>',
    "type":   '<emoji id="5375464961822695044">🎬</emoji>',
    "next":   '<emoji id="6192553546102085729">⏩</emoji>',
    "num":    '<emoji id="5471952986970267163">🔢</emoji>',
}


@app.on_message(
    filters.command(
        ["q", "queue", "cqueue", "player", "cplayer", "playing", "cplaying"],
        prefixes=["/", ".", "!"],
    )
    & filters.group
    & ~BANNED_USERS
)
async def kqueue(_, message: Message):
    is_channel = message.command[0].startswith("c")
    if is_channel:
        chat_id = await get_cmode(message.chat.id)
        if not chat_id:
            return await message.reply_text(
                f"<blockquote>{_E['warn']} ᴄʜᴀɴɴᴇʟ ᴘʟᴀʏ ɴᴏᴛ ꜱᴇᴛ.</blockquote>"
            )
    else:
        chat_id = message.chat.id

    if not await is_active_chat(chat_id):
        return await message.reply_text(
            f"<blockquote>{_E['warn']} ʙᴏᴛ ɪꜱ ɴᴏᴛ ᴀᴄᴛɪᴠᴇ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ.</blockquote>"
        )

    q = db.get(chat_id)
    if not q:
        return await message.reply_text(
            f"<blockquote>{_E['zap']} ǫᴜᴇᴜᴇ ɪꜱ ᴇᴍᴘᴛʏ.</blockquote>"
        )

    now = q[0]
    title = now.get("title", "Unknown").title()
    user = now.get("by", "Unknown")
    dur = now.get("dur", "Unknown")
    stype = now.get("streamtype", "audio").upper()
    played = now.get("played", 0)
    seconds = now.get("seconds", 0)

    if seconds and int(seconds) > 0:
        progress = int((int(played) / int(seconds)) * 10)
        bar = "▰" * progress + "▱" * (10 - progress)
        time_str = f"{seconds_to_min(played)} / {dur}"
    else:
        bar = "— ʟɪᴠᴇ —"
        time_str = "ʟɪᴠᴇ"

    stype_icon = _E["type"] if stype == "VIDEO" else _E["music"]

    text = (
        f"<blockquote>"
        f"┌────── ˹ {_E['music']} ɴᴏᴡ ᴩʟᴀʏɪɴɢ ˼ ─── ⏤‌●\n"
        f"┆\n"
        f"┆{_E['fire']} <b>{title}</b>\n"
        f"┆\n"
        f"┆{stype_icon} <b>ᴛʏᴘᴇ :</b>  <code>{stype}</code>\n"
        f"┆{_E['clock']} <b>ᴘʀᴏɢʀᴇꜱꜱ :</b>  <code>{time_str}</code>\n"
        f"┆{_E['mic']} <b>ʀᴇǫᴜᴇꜱᴛᴇᴅ ʙʏ :</b>  {user}\n"
        f"┆\n"
        f"┆<code>[{bar}]</code>\n"
        f"└──────────────────●"
        f"</blockquote>"
    )

    if len(q) > 1:
        remaining = len(q) - 1
        text += f"\n\n<blockquote>┌────── ˹ {_E['list']} ᴜᴩ ɴᴇxᴛ ({remaining}) ˼ ─── ⏤‌●\n"
        for i, item in enumerate(q[1:8], 1):
            t = item.get("title", "Unknown").title()[:38]
            d = item.get("dur", "?")
            by = item.get("by", "?")
            text += f"┆{_E['next']} <b>{i}.</b> {t}  <code>{d}</code>  — {by}\n"
        if len(q) > 9:
            text += f"┆{_E['dot']} <i>... ᴀɴᴅ {len(q) - 9} ᴍᴏʀᴇ</i>\n"
        text += "└──────────────────●</blockquote>"

    await message.reply_text(text)
