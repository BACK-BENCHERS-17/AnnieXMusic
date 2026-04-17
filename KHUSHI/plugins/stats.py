"""KHUSHI — Stats Plugin."""

from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from KHUSHI.utils.inline import InlineKeyboardButton

from KHUSHI import app
from KHUSHI.misc import SUDOERS
from KHUSHI.utils import bot_sys_stats
from KHUSHI.utils.database import (
    get_active_chats,
    get_active_video_chats,
    get_banned_users,
    get_gbanned,
    get_served_chats,
    get_served_users,
    get_sudoers,
)
from config import BANNED_USERS, OWNER_ID

from KHUSHI.utils.ui import BRAND as _BRAND, E as _E_UI

_E = {
    "globe":  "<emoji id='5372981976804366741'>🌐</emoji>",
    "user":   "<emoji id='5391233076587903881'>👤</emoji>",
    "music":  _E_UI["music"],
    "video":  _E_UI["video"],
    "time":   _E_UI["clock"],
    "cpu":    "<emoji id='5373230054116079491'>🖥</emoji>",
    "ram":    _E_UI["dot"],
    "disk":   _E_UI["link"],
    "crown":  _E_UI["crown"],
    "fire":   _E_UI["fire"],
    "banned": _E_UI["ban"],
    "block":  _E_UI["shield"],
}


def _stats_keyboard(is_sudo: bool) -> InlineKeyboardMarkup:
    rows = []
    if is_sudo:
        rows.append([
            InlineKeyboardButton("˹ᴏᴠᴇʀᴀʟʟ˼",  callback_data="kstats:overview", style="primary"),
            InlineKeyboardButton("˹sʏsᴛᴇᴍ˼",    callback_data="kstats:system",   style="primary"),
        ])
    else:
        rows.append([
            InlineKeyboardButton("˹ᴏᴠᴇʀᴀʟʟ sᴛᴀᴛs˼", callback_data="kstats:overview", style="primary"),
        ])
    rows.append([InlineKeyboardButton("˹ᴄʟᴏsᴇ˼", callback_data="kstats:close", style="danger")])
    return InlineKeyboardMarkup(rows)


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("˹ʙᴀᴄᴋ˼",  callback_data="kstats:back",  style="success"),
        InlineKeyboardButton("˹ᴄʟᴏsᴇ˼", callback_data="kstats:close", style="danger"),
    ]])


async def _main_text() -> str:
    try:
        served_chats = len(await get_served_chats())
    except Exception:
        served_chats = 0
    try:
        served_users = len(await get_served_users())
    except Exception:
        served_users = 0
    try:
        active_audio = len(await get_active_chats())
    except Exception:
        active_audio = 0
    try:
        active_video = len(await get_active_video_chats())
    except Exception:
        active_video = 0
    UP, CPU, RAM, DISK = await bot_sys_stats()
    return (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        "<blockquote>"
        "┌────── ˹ ᴀɴɴɪᴇ sᴛᴀᴛs ˼─── ⏤‌‌●\n"
        f"┆{_E['globe']} <b>sᴇʀᴠᴇᴅ ɢʀᴏᴜᴘs :</b> <code>{served_chats}</code>\n"
        f"┆{_E['user']} <b>sᴇʀᴠᴇᴅ ᴜsᴇʀs :</b> <code>{served_users}</code>\n"
        f"┆{_E['music']} <b>ᴀᴄᴛɪᴠᴇ ᴀᴜᴅɪᴏ :</b> <code>{active_audio}</code>\n"
        f"┆{_E['video']} <b>ᴀᴄᴛɪᴠᴇ ᴠɪᴅᴇᴏ :</b> <code>{active_video}</code>\n"
        "├──────────────────────\n"
        f"┆{_E['time']} <b>ᴜᴘᴛɪᴍᴇ :</b> <code>{UP}</code>\n"
        f"┆{_E['cpu']} <b>ᴄᴘᴜ :</b> <code>{CPU}</code>\n"
        f"┆{_E['ram']} <b>ʀᴀᴍ :</b> <code>{RAM}</code>\n"
        f"┆{_E['disk']} <b>ᴅɪsᴋ :</b> <code>{DISK}</code>\n"
        "└──────────────────────●"
        "</blockquote>"
    )


async def _overview_text() -> str:
    try:
        served_chats = len(await get_served_chats())
    except Exception:
        served_chats = 0
    try:
        served_users = len(await get_served_users())
    except Exception:
        served_users = 0
    try:
        active_audio = len(await get_active_chats())
    except Exception:
        active_audio = 0
    try:
        active_video = len(await get_active_video_chats())
    except Exception:
        active_video = 0
    try:
        sudoers = len(await get_sudoers())
    except Exception:
        sudoers = 0
    try:
        gbanned = len(await get_gbanned())
    except Exception:
        gbanned = 0
    try:
        banned = len(await get_banned_users())
    except Exception:
        banned = 0
    return (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        "<blockquote>"
        "┌────── ˹ ᴏᴠᴇʀᴀʟʟ sᴛᴀᴛs ˼─── ⏤‌‌●\n"
        f"┆{_E['globe']} <b>sᴇʀᴠᴇᴅ ɢʀᴏᴜᴘs :</b> <code>{served_chats}</code>\n"
        f"┆{_E['user']} <b>sᴇʀᴠᴇᴅ ᴜsᴇʀs :</b> <code>{served_users}</code>\n"
        f"┆{_E['music']} <b>ᴀᴄᴛɪᴠᴇ ᴀᴜᴅɪᴏ ᴄᴀʟʟs :</b> <code>{active_audio}</code>\n"
        f"┆{_E['video']} <b>ᴀᴄᴛɪᴠᴇ ᴠɪᴅᴇᴏ ᴄᴀʟʟs :</b> <code>{active_video}</code>\n"
        f"┆{_E['crown']} <b>sᴜᴅᴏᴇʀs :</b> <code>{sudoers}</code>\n"
        f"┆{_E['banned']} <b>ɢʟᴏʙᴀʟ ʙᴀɴɴᴇᴅ :</b> <code>{gbanned}</code>\n"
        f"┆{_E['block']} <b>ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs :</b> <code>{banned}</code>\n"
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
        f"┆{_E['cpu']} <b>ᴄᴘᴜ :</b> <code>{CPU}</code>\n"
        f"┆{_E['ram']} <b>ʀᴀᴍ :</b> <code>{RAM}</code>\n"
        f"┆{_E['disk']} <b>ᴅɪsᴋ :</b> <code>{DISK}</code>\n"
        "└──────────────────────●"
        "</blockquote>"
    )


@app.on_message(filters.command(["stats", "stat"]) & ~BANNED_USERS)
async def stats_command(_, message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.reply_text(
            "<blockquote>"
            f"{_E_UI['ban']} <b>Access Denied</b>\n\n"
            "You are not authorised to use the <code>/stats</code> command.\n"
            "This command is reserved exclusively for the bot owner."
            "</blockquote>"
        )
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
