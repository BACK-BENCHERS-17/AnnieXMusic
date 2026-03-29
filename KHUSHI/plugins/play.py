"""KHUSHI — Play Plugin: /play and /vplay commands."""

import asyncio
from datetime import datetime

from pyrogram import filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from KHUSHI import YouTube, app
from KHUSHI.core.call import JARVIS
from KHUSHI.misc import SUDOERS, db
from ANNIEMUSIC.utils.database import (
    add_active_chat,
    get_assistant,
    get_lang,
    get_playmode,
    is_active_chat,
    is_maintenance,
)
from ANNIEMUSIC.utils.decorators import AdminRightsCheck
from config import BANNED_USERS, DURATION_LIMIT, SUPPORT_CHAT, adminlist

_BRAND = (
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
)

_EM = {
    "music":  "<emoji id='5463107823946717464'>🎵</emoji>",
    "video":  "<emoji id='5375464961822695044'>🎬</emoji>",
    "zap":    "<emoji id='5042334757040423886'>⚡️</emoji>",
    "dot":    "<emoji id='5972072533833289156'>🔹</emoji>",
    "fire":   "<emoji id='5039598514980520994'>❤️‍🔥</emoji>",
    "clock":  "<emoji id='5123230779593196220'>⏰</emoji>",
    "user":   "<emoji id='5316992572680320646'>👤</emoji>",
    "queue":  "<emoji id='5462956611033117422'>📀</emoji>",
}

THUMB_OFF_VIDEO_URL = "https://files.catbox.moe/4vr2jc.mp4"


def _close_kb():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✖ ᴄʟᴏꜱᴇ", callback_data="close")
    ]])


def _playing_kb(chat_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ ᴘᴀᴜꜱᴇ", callback_data=f"Pause|||{chat_id}"),
            InlineKeyboardButton("⏭ ꜱᴋɪᴘ", callback_data=f"Skip|||{chat_id}"),
            InlineKeyboardButton("⏹ ꜱᴛᴏᴘ", callback_data=f"Stop|||{chat_id}"),
        ],
    ])


def _queued_kb():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✖ ᴄʟᴏꜱᴇ", callback_data="close")
    ]])


async def _check_maintenance(message: Message) -> bool:
    try:
        if await is_maintenance():
            if message.from_user.id not in SUDOERS:
                await message.reply_text(
                    f"<blockquote>{_BRAND}</blockquote>\n\n"
                    f"<blockquote>{_EM['zap']} <b>ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ</b>\n"
                    f"{_EM['dot']} ʙᴏᴛ ɪꜱ ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ.\n"
                    f"{_EM['dot']} ᴠɪꜱɪᴛ <a href='https://t.me/{SUPPORT_CHAT.lstrip('@')}'>ꜱᴜᴘᴘᴏʀᴛ</a> ᴄʜᴀᴛ.</blockquote>",
                    disable_web_page_preview=True,
                )
                return True
    except Exception:
        pass
    return False


async def _check_playtype(message: Message, chat_id: int) -> bool:
    try:
        from ANNIEMUSIC.utils.database import get_playtype
        playty = await get_playtype(chat_id)
        if playty != "Everyone":
            if message.from_user.id not in SUDOERS:
                admins = adminlist.get(chat_id)
                if not admins or message.from_user.id not in admins:
                    await message.reply_text(
                        f"<blockquote>{_BRAND}</blockquote>\n\n"
                        f"<blockquote>❌ ꜱᴇᴛ ᴛᴏ <b>Aᴅᴍɪɴꜱ Oɴʟʏ</b> — ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴜꜱᴇ /ᴘʟᴀʏ.</blockquote>"
                    )
                    return True
    except Exception:
        pass
    return False


def _put_to_db(chat_id, original_chat_id, file, title, duration, user, vidid, user_id, streamtype, forceplay=False):
    from config import time_to_seconds, autoclean
    try:
        secs = time_to_seconds(duration) - 3
    except Exception:
        secs = 0

    entry = {
        "title":      title.title(),
        "dur":        duration,
        "streamtype": streamtype,
        "by":         user,
        "user_id":    user_id,
        "chat_id":    original_chat_id,
        "file":       file,
        "vidid":      vidid,
        "seconds":    secs,
        "played":     0,
    }

    if forceplay:
        q = db.get(chat_id)
        if q:
            q.insert(0, entry)
        else:
            db[chat_id] = [entry]
    else:
        if chat_id not in db:
            db[chat_id] = []
        db[chat_id].append(entry)

    try:
        if hasattr(file, "startswith") and not file.startswith(("live_", "vid_", "index_")):
            autoclean.append(file)
    except Exception:
        pass


async def _handle_play(message: Message, video: bool = False):
    chat_id = message.chat.id
    user = message.from_user
    user_name = user.mention
    user_id = user.id

    if await _check_maintenance(message):
        return
    if await _check_playtype(message, chat_id):
        return

    # Detect file reply
    tg_audio = None
    tg_video = None
    if message.reply_to_message:
        r = message.reply_to_message
        tg_audio = r.audio or r.voice
        tg_video = r.video or r.document if video else None

    # Get URL/query from message
    url = await YouTube.url(message)

    # Check if we have something to play
    if tg_audio is None and tg_video is None and url is None:
        if len(message.command) < 2:
            await message.reply_text(
                f"<blockquote>{_BRAND}</blockquote>\n\n"
                f"<blockquote>{_EM['music']} <b>ᴜꜱᴀɢᴇ</b>\n"
                f"{_EM['dot']} /play [ꜱᴏɴɢ ɴᴀᴍᴇ / ᴜʀʟ]\n"
                f"{_EM['video']} /vplay [ᴠɪᴅᴇᴏ ɴᴀᴍᴇ / ᴜʀʟ]</blockquote>"
            )
            return

    mystic = await message.reply_text(
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        f"<blockquote>{_EM['zap']} ꜱᴇᴀʀᴄʜɪɴɢ...</blockquote>"
    )

    # Handle Telegram audio/video file
    if tg_audio or tg_video:
        file_obj = tg_audio or tg_video
        fname = getattr(file_obj, "file_name", None) or "Telegram File"
        title = fname.rsplit(".", 1)[0][:50]
        duration = "00:00"
        if hasattr(file_obj, "duration") and file_obj.duration:
            m, s = divmod(int(file_obj.duration), 60)
            h, m = divmod(m, 60)
            duration = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

        try:
            dl_msg = await mystic.edit_text(
                f"<blockquote>{_BRAND}</blockquote>\n\n"
                f"<blockquote>{_EM['zap']} ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴛᴇʟᴇɢʀᴀᴍ ꜰɪʟᴇ...</blockquote>"
            )
            file_path = await app.download_media(file_obj.file_id, file_name=f"downloads/tg_{file_obj.file_id}.file")
        except Exception as e:
            return await mystic.edit_text(
                f"<blockquote>{_BRAND}</blockquote>\n\n"
                f"<blockquote>❌ ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ: {type(e).__name__}</blockquote>"
            )

        _put_to_db(chat_id, chat_id, file_path, title, duration, user_name, "telegram", user_id,
                   "video" if (video or tg_video) else "audio")
        return await _start_or_queue(chat_id, mystic, title, duration, user_name, "queued" if await is_active_chat(chat_id) else "playing", video or bool(tg_video))

    # Handle YouTube URL or search
    query = url if url else message.text.split(None, 1)[1] if len(message.command) > 1 else None

    if not query:
        return await mystic.edit_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ɴᴏ ǫᴜᴇʀʏ ᴘʀᴏᴠɪᴅᴇᴅ.</blockquote>"
        )

    # Check if it's a YouTube live stream
    if "youtube.com" in query or "youtu.be" in query:
        try:
            is_live = await YouTube.check_live(query)
            if is_live:
                vidid = YouTube.ytid(query) if hasattr(YouTube, "ytid") else query.split("v=")[-1].split("&")[0]
                title, duration_min, duration_sec, thumbnail, vidid2 = await YouTube.details(vidid, videoid=True)
                if vidid2:
                    vidid = vidid2
                _put_to_db(chat_id, chat_id, f"live_{vidid}", title, "Live", user_name, vidid, user_id,
                           "video" if video else "audio")
                already_active = await is_active_chat(chat_id)
                return await _start_or_queue(chat_id, mystic, title, "LIVE", user_name,
                                             "queued" if already_active else "playing", video)
        except Exception:
            pass

    # Search/details
    try:
        title, duration_min, duration_sec, thumbnail, vidid = await YouTube.details(query, videoid=False)
    except Exception as e:
        return await mystic.edit_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ɴᴏᴛʜɪɴɢ ꜰᴏᴜɴᴅ.\n{_EM['dot']} {type(e).__name__}</blockquote>"
        )

    if str(duration_min) == "None" or not vidid:
        return await mystic.edit_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ᴄᴏᴜʟᴅ ɴᴏᴛ ꜰᴇᴛᴄʜ ᴛʀᴀᴄᴋ ᴅᴇᴛᴀɪʟꜱ.</blockquote>"
        )

    if duration_sec and duration_sec > DURATION_LIMIT:
        return await mystic.edit_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ᴛʀᴀᴄᴋ ɪꜱ ᴛᴏᴏ ʟᴏɴɢ.\n"
            f"{_EM['dot']} ᴍᴀx ᴅᴜʀᴀᴛɪᴏɴ: <code>{DURATION_LIMIT // 60} ᴍɪɴᴜᴛᴇꜱ</code></blockquote>"
        )

    already_active = await is_active_chat(chat_id)

    if already_active:
        _put_to_db(chat_id, chat_id, f"vid_{vidid}", title, duration_min, user_name, vidid, user_id,
                   "video" if video else "audio")
        return await _start_or_queue(chat_id, mystic, title, duration_min, user_name, "queued", video)

    # First track — download then play
    await mystic.edit_text(
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        f"<blockquote>{_EM['zap']} ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ...</blockquote>"
    )
    try:
        file_path, direct = await YouTube.download(vidid, mystic, videoid=True, video=video)
    except Exception as e:
        return await mystic.edit_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ.\n{_EM['dot']} {type(e).__name__}</blockquote>"
        )

    _put_to_db(chat_id, chat_id, file_path, title, duration_min, user_name, vidid, user_id,
               "video" if video else "audio")
    await _start_or_queue(chat_id, mystic, title, duration_min, user_name, "playing", video)


async def _start_or_queue(chat_id, mystic, title, duration, user_name, mode, video):
    if mode == "queued":
        try:
            await mystic.edit_text(
                f"<blockquote>{_BRAND}</blockquote>\n\n"
                f"<blockquote>"
                f"{_EM['queue']} <b>ᴀᴅᴅᴇᴅ ᴛᴏ ǫᴜᴇᴜᴇ</b>\n\n"
                f"{_EM['music']} <b>{title.title()[:40]}</b>\n"
                f"{_EM['clock']} <b>ᴅᴜʀᴀᴛɪᴏɴ:</b> <code>{duration}</code>\n"
                f"{_EM['user']} <b>ʙʏ:</b> {user_name}"
                f"</blockquote>",
                reply_markup=_queued_kb(),
            )
        except Exception:
            pass
        return

    # Playing — call JARVIS.join_call
    try:
        q = db.get(chat_id)
        if not q:
            return
        link = q[0]["file"]
        await JARVIS.join_call(chat_id, chat_id, link, video=video)
        try:
            await mystic.delete()
        except Exception:
            pass
    except Exception as e:
        try:
            await mystic.edit_text(
                f"<blockquote>{_BRAND}</blockquote>\n\n"
                f"<blockquote>❌ ᴄᴀɴɴᴏᴛ ᴊᴏɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ.\n{_EM['dot']} {str(e)[:100]}</blockquote>"
            )
        except Exception:
            pass


# ── PLAY COMMAND ──────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["play", "cplay"], prefixes=["/", ".", "!"])
    & filters.group
    & ~BANNED_USERS
)
async def play_cmd(_, message: Message):
    await _handle_play(message, video=False)


# ── VPLAY COMMAND ─────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["vplay", "cvplay"], prefixes=["/", ".", "!"])
    & filters.group
    & ~BANNED_USERS
)
async def vplay_cmd(_, message: Message):
    await _handle_play(message, video=True)


# ── SEEK COMMAND ──────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["seek", "cseek"], prefixes=["/", ".", "!"])
    & filters.group
    & ~BANNED_USERS
)
@AdminRightsCheck
async def kseek(_, message: Message, lang, chat_id):
    if len(message.command) < 2:
        return await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>{_EM['dot']} ᴜꜱᴀɢᴇ: /seek [ꜱᴇᴄᴏɴᴅꜱ]</blockquote>"
        )
    check = db.get(chat_id)
    if not check:
        return await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>⚠️ ɴᴏᴛʜɪɴɢ ɪꜱ ᴘʟᴀʏɪɴɢ.</blockquote>"
        )
    try:
        secs = int(message.command[1])
    except ValueError:
        return await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ᴘʀᴏᴠɪᴅᴇ ᴠᴀʟɪᴅ ꜱᴇᴄᴏɴᴅꜱ.</blockquote>"
        )
    from ANNIEMUSIC.utils.formatters import seconds_to_min
    file_path = check[0].get("file", "")
    total = check[0].get("seconds", 0)
    if secs < 0 or secs >= int(total):
        return await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ɪɴᴠᴀʟɪᴅ ᴘᴏꜱɪᴛɪᴏɴ. ᴍᴀx: <code>{seconds_to_min(total)}</code></blockquote>"
        )
    dur = seconds_to_min(total)
    played = seconds_to_min(secs)
    mode = check[0].get("streamtype", "audio")
    try:
        await JARVIS.seek_stream(chat_id, file_path, played, dur, mode)
        check[0]["played"] = secs
        await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>{_EM['zap']} <b>ꜱᴇᴇᴋᴇᴅ</b> ᴛᴏ <code>{played}</code></blockquote>"
        )
    except Exception as e:
        await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ꜱᴇᴇᴋ ꜰᴀɪʟᴇᴅ: {type(e).__name__}</blockquote>"
        )


# ── SPEED COMMAND ─────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["speed", "cspeed"], prefixes=["/", ".", "!"])
    & filters.group
    & ~BANNED_USERS
)
@AdminRightsCheck
async def kspeed(_, message: Message, lang, chat_id):
    if len(message.command) < 2:
        return await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>{_EM['dot']} ᴜꜱᴀɢᴇ: /speed [0.5 - 4.0]</blockquote>"
        )
    check = db.get(chat_id)
    if not check:
        return await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>⚠️ ɴᴏᴛʜɪɴɢ ɪꜱ ᴘʟᴀʏɪɴɢ.</blockquote>"
        )
    try:
        speed = float(message.command[1])
    except ValueError:
        return await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ᴘʀᴏᴠɪᴅᴇ ᴠᴀʟɪᴅ ꜱᴘᴇᴇᴅ (0.5 - 4.0).</blockquote>"
        )
    if not 0.5 <= speed <= 4.0:
        return await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ꜱᴘᴇᴇᴅ ᴍᴜꜱᴛ ʙᴇ ʙᴇᴛᴡᴇᴇɴ 0.5 ᴀɴᴅ 4.0.</blockquote>"
        )
    try:
        file_path = check[0].get("file", "")
        await JARVIS.speedup_stream(chat_id, file_path, speed, check)
        await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>{_EM['zap']} <b>ꜱᴘᴇᴇᴅ ꜱᴇᴛ ᴛᴏ {speed}×</b></blockquote>"
        )
    except Exception as e:
        await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ꜱᴘᴇᴇᴅ ᴄʜᴀɴɢᴇ ꜰᴀɪʟᴇᴅ: {type(e).__name__}</blockquote>"
        )


# ── CLOSE CALLBACK ────────────────────────────────────────────────────────────
@app.on_callback_query(filters.regex("^close$") & ~BANNED_USERS)
async def close_cb(_, query):
    try:
        await query.message.delete()
    except Exception:
        await query.answer()
