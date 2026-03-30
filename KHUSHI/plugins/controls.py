"""KHUSHI — Music Controls: pause, resume, skip, stop, loop, seek, shuffle, volume, 247, speed."""

import random

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from KHUSHI import app
from KHUSHI.core.call import JARVIS
from KHUSHI.misc import db
from KHUSHI.utils import seconds_to_min
from KHUSHI.utils.database import (
    disable_247,
    enable_247,
    get_loop,
    get_volume,
    is_24_7,
    is_active_chat,
    is_music_playing,
    music_off,
    music_on,
    set_loop,
    set_volume,
)
from KHUSHI.utils.decorators import KhushiAdminCheck as AdminRightsCheck
from KHUSHI.utils.stream.autoclear import auto_clean
from config import BANNED_USERS

_EM = {
    "fire":   "<emoji id='5039598514980520994'>❤️‍🔥</emoji>",
    "dot":    "<emoji id='5972072533833289156'>🔹</emoji>",
    "zap":    "<emoji id='5042334757040423886'>⚡️</emoji>",
    "star":   "<emoji id='5041975203853239332'>🎁</emoji>",
}
_BRAND = (
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
)

def _close():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close")
    ]])

def _reply(text):
    return f"<blockquote>{_BRAND}</blockquote>\n\n<blockquote>{text}</blockquote>"


# ── PAUSE ─────────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["pause", "cpause"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def kpause(_, message: Message, lang, chat_id):
    if not await is_music_playing(chat_id):
        return await message.reply_text(_reply("▶️ ɴᴏᴛʜɪɴɢ ɪꜱ ᴘʟᴀʏɪɴɢ ʀɪɢʜᴛ ɴᴏᴡ."))
    await music_off(chat_id)
    await JARVIS.pause_stream(chat_id)
    await message.reply_text(
        _reply(f"{_EM['zap']} <b>ᴘᴀᴜꜱᴇᴅ</b>\n{_EM['dot']} ʙʏ : {message.from_user.mention}"),
        reply_markup=_close(),
    )


# ── RESUME ────────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["resume", "cresume"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def kresume(_, message: Message, lang, chat_id):
    if await is_music_playing(chat_id):
        return await message.reply_text(_reply("▶️ ᴀʟʀᴇᴀᴅʏ ᴘʟᴀʏɪɴɢ."))
    await music_on(chat_id)
    await JARVIS.resume_stream(chat_id)
    await message.reply_text(
        _reply(f"{_EM['fire']} <b>ʀᴇꜱᴜᴍᴇᴅ</b>\n{_EM['dot']} ʙʏ : {message.from_user.mention}"),
        reply_markup=_close(),
    )


# ── STOP ──────────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["stop", "end", "cstop", "cend"], prefixes=["/", "!", "."]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def kstop(_, message: Message, lang, chat_id):
    await JARVIS.stop_stream(chat_id)
    await set_loop(chat_id, 0)
    await message.reply_text(
        _reply(f"{_EM['zap']} <b>ꜱᴛᴏᴘᴘᴇᴅ & ǫᴜᴇᴜᴇ ᴄʟᴇᴀʀᴇᴅ</b>\n{_EM['dot']} ʙʏ : {message.from_user.mention}"),
        reply_markup=_close(),
    )


# ── SKIP ──────────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["skip", "next", "cskip", "cnext"], prefixes=["/", "!", "."]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def kskip(_, message: Message, lang, chat_id):
    check = db.get(chat_id)
    if not check:
        return await message.reply_text(_reply("⚠️ ɴᴏᴛʜɪɴɢ ɪɴ ǫᴜᴇᴜᴇ."))

    popped = None
    try:
        popped = check.pop(0)
        if popped:
            await auto_clean(popped)
        if not check:
            await message.reply_text(
                _reply(f"{_EM['star']} <b>ǫᴜᴇᴜᴇ ᴇᴍᴘᴛʏ</b> — ꜱᴛᴏᴘᴘɪɴɢ.\n{_EM['dot']} ʙʏ : {message.from_user.mention}"),
                reply_markup=_close(),
            )
            return await JARVIS.stop_or_autoplay(chat_id, popped)
    except Exception:
        return await message.reply_text(_reply("❌ ᴄᴀɴɴᴏᴛ ꜱᴋɪᴘ."))

    title = check[0].get("title", "Unknown").title()
    await message.reply_text(
        _reply(
            f"{_EM['fire']} <b>ꜱᴋɪᴘᴘᴇᴅ</b>\n"
            f"{_EM['dot']} <b>ɴᴏᴡ ᴘʟᴀʏɪɴɢ:</b> {title}\n"
            f"{_EM['dot']} ʙʏ : {message.from_user.mention}"
        ),
        reply_markup=_close(),
    )
    try:
        await JARVIS.skip_stream(chat_id, check[0]["file"])
    except Exception:
        pass


# ── LOOP ──────────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["loop", "cloop"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def kloop(_, message: Message, lang, chat_id):
    if len(message.command) != 2:
        return await message.reply_text(_reply(f"{_EM['dot']} ᴜꜱᴀɢᴇ: /loop [1-10 | enable | disable]"))
    state = message.text.split(None, 1)[1].strip()
    if state.lower() == "disable":
        await set_loop(chat_id, 0)
        return await message.reply_text(
            _reply(f"{_EM['zap']} <b>ʟᴏᴏᴘ ᴅɪꜱᴀʙʟᴇᴅ</b>\n{_EM['dot']} ʙʏ : {message.from_user.mention}"),
            reply_markup=_close(),
        )
    if state.lower() == "enable":
        state = "10"
    if state.isnumeric():
        n = int(state)
        if 1 <= n <= 10:
            await set_loop(chat_id, n)
            return await message.reply_text(
                _reply(f"{_EM['fire']} <b>ʟᴏᴏᴘ ꜱᴇᴛ ᴛᴏ {n}×</b>\n{_EM['dot']} ʙʏ : {message.from_user.mention}"),
                reply_markup=_close(),
            )
    await message.reply_text(_reply(f"{_EM['dot']} ᴜꜱᴀɢᴇ: /loop [1-10 | enable | disable]"))


# ── SHUFFLE ───────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["shuffle", "cshuffle"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def kshuffle(_, message: Message, lang, chat_id):
    check = db.get(chat_id)
    if not check:
        return await message.reply_text(_reply("⚠️ ǫᴜᴇᴜᴇ ɪꜱ ᴇᴍᴘᴛʏ."))
    try:
        first = check.pop(0)
        random.shuffle(check)
        check.insert(0, first)
    except Exception:
        return await message.reply_text(_reply("❌ ᴄᴀɴɴᴏᴛ ꜱʜᴜꜰꜰʟᴇ."))
    await message.reply_text(
        _reply(f"{_EM['fire']} <b>ǫᴜᴇᴜᴇ ꜱʜᴜꜰꜰʟᴇᴅ</b> 🔀\n{_EM['dot']} ʙʏ : {message.from_user.mention}"),
        reply_markup=_close(),
    )


# ── VOLUME ────────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["volume", "vol", "cvol", "cvolume"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def kvolume(_, message: Message, lang, chat_id):
    if not await is_active_chat(chat_id):
        return await message.reply_text(_reply("⚠️ ʙᴏᴛ ɪꜱ ɴᴏᴛ ᴀᴄᴛɪᴠᴇ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ."))

    if len(message.command) < 2:
        cur = await get_volume(chat_id)
        bar = "█" * (cur // 20) + "░" * (10 - cur // 20)
        return await message.reply_text(
            _reply(
                f"🔊 <b>ᴄᴜʀʀᴇɴᴛ ᴠᴏʟᴜᴍᴇ</b>\n"
                f"[{bar}] <code>{cur}%</code>\n\n"
                f"{_EM['dot']} ᴜꜱᴀɢᴇ: /volume [0-200]"
            ),
            reply_markup=_close(),
        )

    try:
        vol = int(message.command[1])
    except ValueError:
        return await message.reply_text(_reply("❌ ᴘʀᴏᴠɪᴅᴇ ᴀ ɴᴜᴍʙᴇʀ 0-200."))

    if not 0 <= vol <= 200:
        return await message.reply_text(_reply("❌ ᴠᴏʟᴜᴍᴇ ᴍᴜꜱᴛ ʙᴇ 0-200."))

    try:
        assistant = await JARVIS.group_assistant(chat_id)
        client = JARVIS.pytgcalls[assistant]
        await client.change_volume_call(chat_id, vol)
    except Exception:
        return await message.reply_text(_reply("❌ ᴄᴀɴɴᴏᴛ ᴄʜᴀɴɢᴇ ᴠᴏʟᴜᴍᴇ. ꜱᴛʀᴇᴀᴍ ᴀᴄᴛɪᴠᴇ?"))

    await set_volume(chat_id, vol)
    bar = "█" * (vol // 20) + "░" * (10 - vol // 20)
    await message.reply_text(
        _reply(
            f"🔊 <b>ᴠᴏʟᴜᴍᴇ ꜱᴇᴛ</b>\n"
            f"[{bar}] <code>{vol}%</code>\n\n"
            f"{_EM['dot']} ʙʏ : {message.from_user.mention}"
        ),
        reply_markup=_close(),
    )


# ── 24/7 MODE ────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["247", "nonstop"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def k247(_, message: Message, lang, chat_id):
    on = await is_24_7(chat_id)
    if on:
        await disable_247(chat_id)
        await message.reply_text(
            _reply(
                f"{_EM['zap']} <b>24/7 ᴅɪꜱᴀʙʟᴇᴅ</b>\n"
                f"{_EM['dot']} ʙᴏᴛ ᴡɪʟʟ ʟᴇᴀᴠᴇ ᴡʜᴇɴ ǫᴜᴇᴜᴇ ɪꜱ ᴇᴍᴘᴛʏ.\n"
                f"{_EM['dot']} ʙʏ : {message.from_user.mention}"
            ),
            reply_markup=_close(),
        )
    else:
        await enable_247(chat_id)
        await message.reply_text(
            _reply(
                f"{_EM['fire']} <b>24/7 ᴍᴏᴅᴇ ᴇɴᴀʙʟᴇᴅ</b>\n"
                f"{_EM['dot']} ʙᴏᴛ ꜱᴛᴀʏꜱ ᴇᴠᴇɴ ᴡʜᴇɴ ǫᴜᴇᴜᴇ ɪꜱ ᴇᴍᴘᴛʏ.\n"
                f"{_EM['dot']} ʙʏ : {message.from_user.mention}"
            ),
            reply_markup=_close(),
        )
