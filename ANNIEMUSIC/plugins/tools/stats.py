from pyrogram import filters
from pyrogram.types import Message, CallbackQuery

from ANNIEMUSIC import app
from ANNIEMUSIC.misc import SUDOERS
from ANNIEMUSIC.utils import bot_sys_stats
from ANNIEMUSIC.utils.database import (
    get_active_chats,
    get_active_video_chats,
    get_served_chats,
    get_served_users,
)
from ANNIEMUSIC.utils.decorators.language import language, languageCB
from ANNIEMUSIC.utils.inline.stats import (
    StatsCallbacks,
    build_back_keyboard,
    build_stats_keyboard,
)
from config import BANNED_USERS


async def _overview_text() -> str:
    served_chats = len(await get_served_chats())
    served_users = len(await get_served_users())
    active_chats = len(await get_active_chats())
    active_video = len(await get_active_video_chats())
    UP, CPU, RAM, DISK = await bot_sys_stats()

    return (
        "<blockquote>"
        "┌────── ˹ ᴏᴠᴇʀᴀʟʟ sᴛᴀᴛs ˼─── ⏤‌‌●\n"
        f"┆🌐 <b>sᴇʀᴠᴇᴅ ɢʀᴏᴜᴘs :</b> <code>{served_chats}</code>\n"
        f"┆👤 <b>sᴇʀᴠᴇᴅ ᴜsᴇʀs :</b> <code>{served_users}</code>\n"
        f"┆🎵 <b>ᴀᴄᴛɪᴠᴇ ᴄᴀʟʟs :</b> <code>{active_chats}</code>\n"
        f"┆🎬 <b>ᴠɪᴅᴇᴏ ᴄᴀʟʟs :</b> <code>{active_video}</code>\n"
        "└──────────────────────●"
        "</blockquote>"
    )


async def _bot_text() -> str:
    UP, CPU, RAM, DISK = await bot_sys_stats()
    return (
        "<blockquote>"
        "┌────── ˹ sʏsᴛᴇᴍ sᴛᴀᴛs ˼─── ⏤‌‌●\n"
        f"┆⏱ <b>ᴜᴘᴛɪᴍᴇ :</b> <code>{UP}</code>\n"
        f"┆💻 <b>ᴄᴘᴜ :</b> <code>{CPU}</code>\n"
        f"┆🧠 <b>ʀᴀᴍ :</b> <code>{RAM}</code>\n"
        f"┆💾 <b>ᴅɪsᴋ :</b> <code>{DISK}</code>\n"
        "└──────────────────────●"
        "</blockquote>"
    )


@app.on_message(filters.command(["stats", "stat"]) & ~BANNED_USERS)
@language
async def stats_command(client, message: Message, _):
    is_sudo = message.from_user.id in SUDOERS
    text = await _overview_text()
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
async def stats_bot_cb(client, cb: CallbackQuery, _):
    if cb.from_user.id not in SUDOERS:
        return await cb.answer("ᴏɴʟʏ sᴜᴅᴏᴇʀs ᴄᴀɴ ᴠɪᴇᴡ ᴛʜɪs!", show_alert=True)
    text = await _bot_text()
    try:
        await cb.message.edit_text(text, reply_markup=build_back_keyboard(_))
    except Exception:
        await cb.answer()


@app.on_callback_query(filters.regex(f"^{StatsCallbacks.BACK}$") & ~BANNED_USERS)
@languageCB
async def stats_back_cb(client, cb: CallbackQuery, _):
    is_sudo = cb.from_user.id in SUDOERS
    text = await _overview_text()
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
