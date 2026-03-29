from pyrogram import filters
from pyrogram.types import Message, CallbackQuery

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
from ANNIEMUSIC.utils.decorators.language import language, languageCB
from ANNIEMUSIC.utils.inline.stats import (
    StatsCallbacks,
    build_back_keyboard,
    build_stats_keyboard,
)
from config import BANNED_USERS

_E = {
    "dot":   "<emoji id='5972072533833289156'>🔹</emoji>",
    "music": "<emoji id='5188093600538057635'>🎵</emoji>",
    "spark": "<emoji id='5042334757040423886'>⚡️</emoji>",
    "time":  "<emoji id='4979027931234830344'>⏳</emoji>",
    "crown": "<emoji id='6122692084806716730'>🌹</emoji>",
    "fire":  "<emoji id='5039598514980520994'>❤️‍🔥</emoji>",
    "snow":  "<emoji id='5449449325434266744'>❄️</emoji>",
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
@language
async def stats_command(client, message: Message, _):
    is_sudo = message.from_user.id in SUDOERS
    text = await _main_text()
    keyboard = build_stats_keyboard(_, is_sudo)
    await message.reply_text(text, reply_markup=keyboard)


@app.on_callback_query(filters.regex(f"^{StatsCallbacks.SHOW_OVERVIEW}$") & ~BANNED_USERS)
@languageCB
async def stats_overview_cb(client, cb: CallbackQuery, _):
    text = await _overview_text()
    try:
        await cb.message.edit_text(text, reply_markup=build_back_keyboard(_))
    except Exception:
        await cb.answer()


@app.on_callback_query(filters.regex(f"^{StatsCallbacks.SHOW_BOT_STATS}$") & ~BANNED_USERS)
@languageCB
async def stats_system_cb(client, cb: CallbackQuery, _):
    if cb.from_user.id not in SUDOERS:
        return await cb.answer("ᴏɴʟʏ sᴜᴅᴏᴇʀs ᴄᴀɴ ᴠɪᴇᴡ ᴛʜɪs!", show_alert=True)
    text = await _system_text()
    try:
        await cb.message.edit_text(text, reply_markup=build_back_keyboard(_))
    except Exception:
        await cb.answer()


@app.on_callback_query(filters.regex(f"^{StatsCallbacks.BACK}$") & ~BANNED_USERS)
@languageCB
async def stats_back_cb(client, cb: CallbackQuery, _):
    is_sudo = cb.from_user.id in SUDOERS
    text = await _main_text()
    try:
        await cb.message.edit_text(text, reply_markup=build_stats_keyboard(_, is_sudo))
    except Exception:
        await cb.answer()


@app.on_callback_query(filters.regex(f"^{StatsCallbacks.CLOSE}$") & ~BANNED_USERS)
async def stats_close_cb(client, cb: CallbackQuery):
    try:
        await cb.message.delete()
    except Exception:
        await cb.answer()
