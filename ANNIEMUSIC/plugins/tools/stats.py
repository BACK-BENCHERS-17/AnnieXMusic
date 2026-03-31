from pyrogram import filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from ANNIEMUSIC import app
from ANNIEMUSIC.misc import SUDOERS
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
    "globe":  "<emoji id='5316832074047441823'>🌐</emoji>",
    "user":   "<emoji id='5316992572680320646'>👤</emoji>",
    "music":  "<emoji id='5463107823946717464'>🎵</emoji>",
    "video":  "<emoji id='5375464961822695044'>🎬</emoji>",
    "time":   "<emoji id='5123230779593196220'>⏰</emoji>",
    "cpu":    "<emoji id='5972055534352733289'>💻</emoji>",
    "ram":    "<emoji id='5237799019329105246'>🧠</emoji>",
    "disk":   "<emoji id='5462956611033117422'>📀</emoji>",
    "crown":  "<emoji id='5039727497143387500'>👑</emoji>",
    "fire":   "<emoji id='5039598514980520994'>❤️‍🔥</emoji>",
    "banned": "<emoji id='6307831155521494118'>💩</emoji>",
    "block":  "<emoji id='5039671744172917707'>🚫</emoji>",
}

_BRAND = (
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
)


def _bar(v, size=11):
    try:
        pct = float(str(v).replace("%", ""))
    except Exception:
        pct = 0
    filled = int((pct / 100) * size)
    return "▰" * filled + "▱" * (size - filled)


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
        f"┆{_E['cpu']} <b>ᴄᴘᴜ :</b> [{_bar(CPU)}] <code>{CPU}</code>\n"
        f"┆{_E['ram']} <b>ʀᴀᴍ :</b> [{_bar(RAM)}] <code>{RAM}</code>\n"
        f"┆{_E['disk']} <b>ᴅɪsᴋ :</b> [{_bar(DISK)}] <code>{DISK}</code>\n"
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
        f"┆{_E['cpu']} <b>ᴄᴘᴜ :</b>  [{_bar(CPU)}]  <code>{CPU}</code>\n"
        f"┆{_E['ram']} <b>ʀᴀᴍ :</b>  [{_bar(RAM)}]  <code>{RAM}</code>\n"
        f"┆{_E['disk']} <b>ᴅɪsᴋ :</b> [{_bar(DISK)}]  <code>{DISK}</code>\n"
        "└──────────────────────●"
        "</blockquote>"
    )


def _stats_keyboard(is_sudo: bool) -> InlineKeyboardMarkup:
    non_sudo_row = [
        InlineKeyboardButton("ᴏᴠᴇʀᴀʟʟ sᴛᴀᴛs", callback_data="stats:overview"),
    ]
    sudo_row = [
        InlineKeyboardButton("ɢᴇɴᴇʀᴀʟ", callback_data="stats:bot"),
        InlineKeyboardButton("ᴏᴠᴇʀᴀʟʟ", callback_data="stats:overview"),
    ]
    rows = [
        sudo_row if is_sudo else non_sudo_row,
        [InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="stats:close")],
    ]
    return InlineKeyboardMarkup(rows)


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("ʙᴀᴄᴋ", callback_data="stats:back"),
        InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="stats:close"),
    ]])


@app.on_message(filters.command(["stats", "stat"]) & ~BANNED_USERS)
async def stats_command(client, message: Message):
    user = message.from_user
    is_sudo = (user.id in SUDOERS) if user else False
    text = await _main_text()
    await message.reply_text(text, reply_markup=_stats_keyboard(is_sudo))


@app.on_callback_query(filters.regex(r"^stats:overview$") & ~BANNED_USERS)
async def stats_overview_cb(client, cb: CallbackQuery):
    text = await _overview_text()
    try:
        await cb.message.edit_text(text, reply_markup=_back_keyboard())
    except Exception:
        await cb.answer()


@app.on_callback_query(filters.regex(r"^stats:bot$") & ~BANNED_USERS)
async def stats_system_cb(client, cb: CallbackQuery):
    if cb.from_user.id not in SUDOERS:
        return await cb.answer("ᴏɴʟʏ sᴜᴅᴏᴇʀs ᴄᴀɴ ᴠɪᴇᴡ ᴛʜɪs!", show_alert=True)
    text = await _system_text()
    try:
        await cb.message.edit_text(text, reply_markup=_back_keyboard())
    except Exception:
        await cb.answer()


@app.on_callback_query(filters.regex(r"^stats:back$") & ~BANNED_USERS)
async def stats_back_cb(client, cb: CallbackQuery):
    is_sudo = cb.from_user.id in SUDOERS
    text = await _main_text()
    try:
        await cb.message.edit_text(text, reply_markup=_stats_keyboard(is_sudo))
    except Exception:
        await cb.answer()


@app.on_callback_query(filters.regex(r"^stats:close$") & ~BANNED_USERS)
async def stats_close_cb(client, cb: CallbackQuery):
    try:
        await cb.message.delete()
    except Exception:
        await cb.answer()
