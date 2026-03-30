"""KHUSHI — Start & Help Plugin with spoiler images."""

import random

from pyrogram import enums, filters
from pyrogram.parser import Parser
from pyrogram.raw import functions as raw_func, types as raw_types
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from KHUSHI import app
from ANNIEMUSIC.utils.database import get_lang
from config import BANNED_USERS, HELP_IMG_URL, START_IMGS, SUPPORT_CHAT
from strings import get_string

_BRAND = (
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
)

START_TEXT = (
    "<blockquote><b>{mention}</b>, ɪ'ᴍ <b>{bot}</b> — ᴀ ꜱᴜᴘᴇʀ ꜰᴀꜱᴛ ᴍᴜꜱɪᴄ ʙᴏᴛ ᴡɪᴛʜ\n"
    "ʜɪɢʜ ǫᴜᴀʟɪᴛʏ ᴀᴜᴅɪᴏ & ᴠɪᴅᴇᴏ ꜱᴛʀᴇᴀᴍɪɴɢ.\n\n"
    "<emoji id='5972072533833289156'>🔹</emoji> ᴘʟᴀʏ ꜱᴏɴɢꜱ ꜰʀᴏᴍ ʏᴏᴜᴛᴜʙᴇ, ꜱᴘᴏᴛɪꜰʏ, ꜱᴏᴜɴᴅᴄʟᴏᴜᴅ\n"
    "<emoji id='5972072533833289156'>🔹</emoji> ǫᴜᴇᴜᴇ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ, ʟᴏᴏᴘ, ꜱʜᴜꜰꜰʟᴇ, ꜱᴇᴇᴋ\n"
    "<emoji id='5972072533833289156'>🔹</emoji> 24/7 ᴍᴏᴅᴇ, ᴠᴏʟᴜᴍᴇ, ꜱᴘᴇᴇᴅ ᴄᴏɴᴛʀᴏʟ\n"
    "<emoji id='5972072533833289156'>🔹</emoji> ɴꜱꜰᴡ ꜰɪʟᴛᴇʀ, ᴄᴏɴᴛᴇɴᴛ ɢᴜᴀʀᴅ</blockquote>"
)

HELP_TEXT = (
    "<blockquote><b>📌 ᴄᴏᴍᴍᴀɴᴅꜱ</b>\n\n"
    "<emoji id='5042334757040423886'>⚡️</emoji> <b>ᴍᴜꜱɪᴄ</b>\n"
    "  /play — ꜱᴛʀᴇᴀᴍ ᴀᴜᴅɪᴏ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ\n"
    "  /vplay — ꜱᴛʀᴇᴀᴍ ᴠɪᴅᴇᴏ ɪɴ ᴠɪᴅᴇᴏ ᴄʜᴀᴛ\n"
    "  /pause  /resume  /skip  /stop\n"
    "  /queue — ꜱʜᴏᴡ ᴄᴜʀʀᴇɴᴛ ǫᴜᴇᴜᴇ\n"
    "  /loop [0-10]  /shuffle  /seek [ꜱᴇᴄ]\n"
    "  /volume [0-200]  /speed [0.5-4.0]\n"
    "  /247 — 24/7 ᴍᴏᴅᴇ ᴛᴏɢɢʟᴇ\n\n"
    "<emoji id='5042334757040423886'>⚡️</emoji> <b>ɪɴꜰᴏ</b>\n"
    "  /ping — ʙᴏᴛ ꜱᴛᴀᴛᴜꜱ & ꜱʏꜱᴛᴇᴍ ꜱᴛᴀᴛꜱ\n"
    "  /stats — ᴅᴇᴛᴀɪʟᴇᴅ ꜱᴛᴀᴛꜱ\n\n"
    "<emoji id='5042334757040423886'>⚡️</emoji> <b>ᴘʀᴏᴛᴇᴄᴛɪᴏɴ</b>\n"
    "  /nsfw on|off — ᴄᴏɴᴛᴇɴᴛ ɢᴜᴀʀᴅ\n"
    "  /auth  /unauth — ᴍᴜꜱɪᴄ ʙᴏᴛ ᴀᴅᴍɪɴꜱ\n\n"
    "<emoji id='5042334757040423886'>⚡️</emoji> <b>ꜱᴜᴅᴏ ᴏɴʟʏ</b>\n"
    "  /gban  /ungban  /block  /unblock\n"
    "  /bc — ʙʀᴏᴀᴅᴄᴀꜱᴛ\n"
    "  /maintenance  /restart</blockquote>"
)


def _start_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("˹ʜᴇʟᴘ˼", callback_data="khushi_help"),
            InlineKeyboardButton("˹ꜱᴜᴘᴘᴏʀᴛ˼", url=f"https://t.me/{SUPPORT_CHAT.lstrip('@')}"),
        ],
        [
            InlineKeyboardButton("˹ᴀᴅᴅ ᴛᴏ ɢʀᴏᴜᴘ˼", url=f"https://t.me/{app.username}?startgroup=true"),
        ],
    ])


def _help_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("˹ʙᴀᴄᴋ˼", callback_data="khushi_back")]
    ])


async def _send_spoiler_photo(
    client,
    message: Message,
    photo_url: str,
    caption: str,
    markup: InlineKeyboardMarkup,
) -> bool:
    """3-tier spoiler photo sender."""
    # Tier 1 — raw API
    try:
        peer = await client.resolve_peer(message.chat.id)
        parser = Parser(client)
        parsed = await parser.parse(caption, mode=enums.ParseMode.HTML)
        text = parsed.get("message", "")
        entities = parsed.get("entities") or []
        raw_markup = await markup.write(client) if markup else None
        media = raw_types.InputMediaPhotoExternal(url=photo_url, spoiler=True)
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
        return True
    except Exception:
        pass

    # Tier 2 — high-level
    try:
        await message.reply_photo(
            photo=photo_url,
            caption=caption,
            reply_markup=markup,
            has_spoiler=True,
        )
        return True
    except Exception:
        pass

    return False


# ── /start & /kstart ──────────────────────────────────────────────────────────

@app.on_message(filters.command(["start", "kstart"]) & ~BANNED_USERS)
async def khushi_start(client, message: Message):
    try:
        lang = await get_lang(message.from_user.id)
    except Exception:
        lang = "en"

    caption = (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        + START_TEXT.format(
            mention=message.from_user.mention,
            bot=app.mention,
        )
    )
    markup = _start_kb()
    img = random.choice(START_IMGS)

    sent = await _send_spoiler_photo(client, message, img, caption, markup)
    if not sent:
        await message.reply_text(caption, reply_markup=markup, disable_web_page_preview=True)


# ── /help & /khelp ────────────────────────────────────────────────────────────

@app.on_message(filters.command(["help", "khelp"]) & ~BANNED_USERS)
async def khushi_help(client, message: Message):
    caption = f"<blockquote>{_BRAND}</blockquote>\n\n" + HELP_TEXT
    markup = _help_kb()

    sent = await _send_spoiler_photo(client, message, HELP_IMG_URL, caption, markup)
    if not sent:
        await message.reply_text(caption, reply_markup=markup, disable_web_page_preview=True)


# ── Callbacks — accept both old (annie_*) and new (khushi_*) names ────────────

@app.on_callback_query(filters.regex("^(khushi_help|annie_help)$") & ~BANNED_USERS)
async def khushi_help_cb(_, query):
    await query.answer()
    caption = f"<blockquote>{_BRAND}</blockquote>\n\n" + HELP_TEXT
    try:
        await query.message.edit_caption(caption, reply_markup=_help_kb())
    except Exception:
        try:
            await query.edit_message_text(
                caption, reply_markup=_help_kb(), disable_web_page_preview=True
            )
        except Exception:
            pass


@app.on_callback_query(filters.regex("^(khushi_back|annie_back)$") & ~BANNED_USERS)
async def khushi_back_cb(_, query):
    await query.answer()
    caption = (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        + START_TEXT.format(
            mention=query.from_user.mention,
            bot=app.mention,
        )
    )
    markup = _start_kb()
    try:
        await query.message.edit_caption(caption, reply_markup=markup)
    except Exception:
        try:
            await query.edit_message_text(
                caption, reply_markup=markup, disable_web_page_preview=True
            )
        except Exception:
            pass
