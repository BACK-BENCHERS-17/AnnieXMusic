"""KHUSHI — Stats Plugin (works in DM & Group)."""

from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from KHUSHI import app
from KHUSHI.misc import SUDOERS
from ANNIEMUSIC.utils import bot_sys_stats
from ANNIEMUSIC.utils.database import (
    get_active_chats,
    get_active_video_chats,
    get_banned_users,
    get_gbanned,
    get_served_chats,
    get_served_users,
    get_sudoers,
)
from config import BANNED_USERS

_E = {
    "dot":    "<emoji id='5972072533833289156'>🔹</emoji>",
    "music":  "<emoji id='5188093600538057635'>🎵</emoji>",
    "spark":  "<emoji id='5042334757040423886'>⚡️</emoji>",
    "time":   "<emoji id='4979027931234830344'>⏳</emoji>",
    "bear":   "<emoji id='5042192219960771668'>🧸</emoji>",
    "fire":   "<emoji id='5039598514980520994'>❤️‍🔥</emoji>",
    "crown":  "<emoji id='6122692084806716730'>🌹</emoji>",
    "snow":   "<emoji id='5449449325434266744'>❄️</emoji>",
}

_BRAND = (
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
)


def _stats_keyboard(is_sudo: bool) -> InlineKeyboardMarkup:
    rows = []
    if is_sudo:
        rows.append([
            InlineKeyboardButton("ᴏᴠᴇʀᴀʟʟ", callback_data="kstats:overview"),
            InlineKeyboardButton("sʏsᴛᴇᴍ", callback_data="kstats:system"),
        ])
    else:
        rows.append([
            InlineKeyboardButton("ᴏᴠᴇʀᴀʟʟ sᴛᴀᴛs", callback_data="kstats:overview")
        ])
    rows.append([InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="kstats:close")])
    return InlineKeyboardMarkup(rows)


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("ʙᴀᴄᴋ", callback_data="kstats:back"),
        InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="kstats:close"),
    ]])


def _bar(v, size=11):
    try:
        pct = float(str(v).replace("%", ""))
    except Exception:
        pct = 0
    filled = int((pct / 100) * size)
    return "▰" * filled + "▱" * (size - filled)


async def _main_text() -> str:
    served_chats = len(await get_served_chats())
    served_users = len(await get_served_users())
    active_audio = len(await get_active_chats())
    active_video = len(await get_active_video_chats())
    UP, CPU, RAM, DISK = await bot_sys_stats()

    return (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        "<blockquote>"
        "┌────── ˹ ᴀɴɴɪᴇ sᴛᴀᴛs ˼─── ⏤‌‌●\n"
        f"┆{_E['dot']} <b>sᴇʀᴠᴇᴅ ɢʀᴏᴜᴘs :</b> <code>{served_chats}</code>\n"
        f"┆{_E['dot']} <b>sᴇʀᴠᴇᴅ ᴜsᴇʀs :</b> <code>{served_users}</code>\n"
        f"┆{_E['music']} <b>ᴀᴄᴛɪᴠᴇ ᴀᴜᴅɪᴏ :</b> <code>{active_audio}</code>\n"
        f"┆{_E['music']} <b>ᴀᴄᴛɪᴠᴇ ᴠɪᴅᴇᴏ :</b> <code>{active_video}</code>\n"
        "├──────────────────────\n"
        f"┆{_E['time']} <b>ᴜᴘᴛɪᴍᴇ :</b> <code>{UP}</code>\n"
        f"┆{_E['spark']} <b>ᴄᴘᴜ :</b> [{_bar(CPU)}] <code>{CPU}</code>\n"
        f"┆{_E['spark']} <b>ʀᴀᴍ :</b> [{_bar(RAM)}] <code>{RAM}</code>\n"
        f"┆{_E['spark']} <b>ᴅɪsᴋ :</b> [{_bar(DISK)}] <code>{DISK}</code>\n"
        "└──────────────────────●"
        "</blockquote>"
    )


async def _overview_text() -> str:
    served_chats = len(await get_served_chats())
    served_users = len(await get_served_users())
    active_audio = len(await get_active_chats())
    active_video = len(await get_active_video_chats())
    sudoers      = len(await get_sudoers())
    gbanned      = len(await get_gbanned())
    banned       = len(await get_banned_users())

    return (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        "<blockquote>"
        "┌────── ˹ ᴏᴠᴇʀᴀʟʟ sᴛᴀᴛs ˼─── ⏤‌‌●\n"
        f"┆{_E['dot']} <b>sᴇʀᴠᴇᴅ ɢʀᴏᴜᴘs :</b> <code>{served_chats}</code>\n"
        f"┆{_E['dot']} <b>sᴇʀᴠᴇᴅ ᴜsᴇʀs :</b> <code>{served_users}</code>\n"
        f"┆{_E['music']} <b>ᴀᴄᴛɪᴠᴇ ᴀᴜᴅɪᴏ ᴄᴀʟʟs :</b> <code>{active_audio}</code>\n"
        f"┆{_E['music']} <b>ᴀᴄᴛɪᴠᴇ ᴠɪᴅᴇᴏ ᴄᴀʟʟs :</b> <code>{active_video}</code>\n"
        f"┆{_E['crown']} <b>sᴜᴅᴏᴇʀs :</b> <code>{sudoers}</code>\n"
        f"┆{_E['fire']} <b>ɢʟᴏʙᴀʟ ʙᴀɴɴᴇᴅ :</b> <code>{gbanned}</code>\n"
        f"┆{_E['snow']} <b>ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs :</b> <code>{banned}</code>\n"
        "└──────────────────────●"
        "</blockquote>"
    )


async def _system_text() -> str:
    UP, CPU, RAM, DISK = await bot_sys_stats()
    return (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        "<blockquote>"
        "┌────── ˹ sʏsᴛᴇᴍ sᴛᴀᴛs ˼─── ⏤‌‌●\n"
        f"┆{_E['time']} <b>ᴜᴘᴛɪᴍᴇ :</b> <code>{UP}</code>\n"
        f"┆{_E['spark']} <b>ᴄᴘᴜ :</b>  [{_bar(CPU)}]  <code>{CPU}</code>\n"
        f"┆{_E['spark']} <b>ʀᴀᴍ :</b>  [{_bar(RAM)}]  <code>{RAM}</code>\n"
        f"┆{_E['spark']} <b>ᴅɪsᴋ :</b> [{_bar(DISK)}]  <code>{DISK}</code>\n"
        "└──────────────────────●"
        "</blockquote>"
    )


@app.on_message(filters.command(["stats", "stat"]) & ~BANNED_USERS)
async def stats_command(_, message: Message):
    is_sudo = message.from_user.id in SUDOERS
    text = await _main_text()
    await message.reply_text(text, reply_markup=_stats_keyboard(is_sudo))


@app.on_callback_query(filters.regex(r"^kstats:overview$") & ~BANNED_USERS)
async def kstats_overview_cb(_, cb: CallbackQuery):
    text = await _overview_text()
    try:
        await cb.message.edit_text(text, reply_markup=_back_keyboard())
    except Exception:
        await cb.answer()


@app.on_callback_query(filters.regex(r"^kstats:system$") & ~BANNED_USERS)
async def kstats_system_cb(_, cb: CallbackQuery):
    if cb.from_user.id not in SUDOERS:
        return await cb.answer("ᴏɴʟʏ sᴜᴅᴏᴇʀs!", show_alert=True)
    text = await _system_text()
    try:
        await cb.message.edit_text(text, reply_markup=_back_keyboard())
    except Exception:
        await cb.answer()


@app.on_callback_query(filters.regex(r"^kstats:back$") & ~BANNED_USERS)
async def kstats_back_cb(_, cb: CallbackQuery):
    is_sudo = cb.from_user.id in SUDOERS
    text = await _main_text()
    try:
        await cb.message.edit_text(text, reply_markup=_stats_keyboard(is_sudo))
    except Exception:
        await cb.answer()


@app.on_callback_query(filters.regex(r"^kstats:close$") & ~BANNED_USERS)
async def kstats_close_cb(_, cb: CallbackQuery):
    try:
        await cb.message.delete()
    except Exception:
        await cb.answer()
