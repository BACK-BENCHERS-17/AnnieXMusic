"""KHUSHI — Start & Help Plugin with new premium UI."""

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from KHUSHI import app
from ANNIEMUSIC.utils.database import get_lang
from config import BANNED_USERS, SUPPORT_CHAT
from strings import get_string

_BRAND = (
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
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
    "<emoji id='5042334757040423886'>⚡️</emoji> <b>ᴘʀᴏᴛᴇᴄᴛɪᴏɴ</b>\n"
    "  /nsfw on|off — ᴄᴏɴᴛᴇɴᴛ ɢᴜᴀʀᴅ\n"
    "  /auth  /unauth — ᴍᴜꜱɪᴄ ʙᴏᴛ ᴀᴅᴍɪɴꜱ\n\n"
    "<emoji id='5042334757040423886'>⚡️</emoji> <b>ꜱᴜᴅᴏ ᴏɴʟʏ</b>\n"
    "  /gban  /ungban  /block  /unblock\n"
    "  /bc — ʙʀᴏᴀᴅᴄᴀꜱᴛ\n"
    "  /maintenance  /restart</blockquote>"
)


def _start_kb(_):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 ʜᴇʟᴘ", callback_data="khushi_help"),
            InlineKeyboardButton("💬 ꜱᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{SUPPORT_CHAT.lstrip('@')}"),
        ],
        [
            InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ɢʀᴏᴜᴘ", url=f"https://t.me/{app.username}?startgroup=true"),
        ],
    ])


@app.on_message(filters.command("kstart") & ~BANNED_USERS)
async def khushi_start(_, message: Message):
    try:
        lang = await get_lang(message.from_user.id)
        _ = get_string(lang)
    except Exception:
        _ = get_string("en")

    text = f"<blockquote>{_BRAND}</blockquote>\n\n" + START_TEXT.format(
        mention=message.from_user.mention,
        bot=app.mention,
    )
    await message.reply_text(text, reply_markup=_start_kb(_), disable_web_page_preview=True)


@app.on_message(filters.command("khelp") & ~BANNED_USERS)
async def khushi_help(_, message: Message):
    await message.reply_text(
        f"<blockquote>{_BRAND}</blockquote>\n\n" + HELP_TEXT,
        disable_web_page_preview=True,
    )


@app.on_callback_query(filters.regex("khushi_help") & ~BANNED_USERS)
async def khushi_help_cb(_, query):
    await query.answer()
    await query.edit_message_text(
        f"<blockquote>{_BRAND}</blockquote>\n\n" + HELP_TEXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="khushi_back")]
        ]),
    )


@app.on_callback_query(filters.regex("khushi_back") & ~BANNED_USERS)
async def khushi_back_cb(_, query):
    await query.answer()
    try:
        _ = get_string("en")
    except Exception:
        _ = {}
    text = f"<blockquote>{_BRAND}</blockquote>\n\n" + START_TEXT.format(
        mention=query.from_user.mention,
        bot=app.mention,
    )
    await query.edit_message_text(text, reply_markup=_start_kb(_), disable_web_page_preview=True)
