"""KHUSHI — Play Plugin: direct VC stream, same notification as AnnieMusic."""

import asyncio

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from strings import get_string
from KHUSHI import YouTube, app
from KHUSHI.core.call import JARVIS
from KHUSHI.misc import SUDOERS, db
from KHUSHI.utils.database import (
    get_lang,
    get_playtype,
    is_active_chat,
    is_autoplay,
    is_maintenance,
)
from KHUSHI.utils.decorators import KhushiAdminCheck as AdminRightsCheck
from KHUSHI.utils.downloader import _trigger_bg_cache
from KHUSHI.utils.inline import aq_markup, stream_markup
from KHUSHI.utils.raw_send import send_msg_invert_preview
from KHUSHI.utils.stream.queue import put_queue
from KHUSHI.utils.thumbnails import get_thumb
from config import BANNED_USERS, BOT_USERNAME, DURATION_LIMIT, SUPPORT_CHAT, adminlist

THUMB_OFF_VIDEO_URL = "https://files.catbox.moe/4vr2jc.mp4"

_BRAND = (
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
)

_EM = {
    "music": "<emoji id='5463107823946717464'>🎵</emoji>",
    "video": "<emoji id='5375464961822695044'>🎬</emoji>",
    "zap":   "<emoji id='5042334757040423886'>⚡️</emoji>",
    "dot":   "<emoji id='5972072533833289156'>🔹</emoji>",
}


async def _send_stream_msg(chat_id: int, caption: str, reply_markup) -> object:
    """Send stream notification — same mechanism as AnnieMusic (invert_media banner)."""
    link_text = f'<a href="{THUMB_OFF_VIDEO_URL}">&#8203;</a>'
    return await send_msg_invert_preview(
        app,
        chat_id,
        text=f"{link_text}{caption}",
        reply_markup=reply_markup,
    )


async def _check_maintenance(message: Message) -> bool:
    try:
        if await is_maintenance():
            if message.from_user.id not in SUDOERS:
                await message.reply_text(
                    f"<blockquote>{_BRAND}</blockquote>\n\n"
                    f"<blockquote>{_EM['zap']} <b>ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ</b>\n"
                    f"{_EM['dot']} ᴠɪꜱɪᴛ "
                    f"<a href='https://t.me/{SUPPORT_CHAT.lstrip('@')}'>ꜱᴜᴘᴘᴏʀᴛ</a>.</blockquote>",
                    disable_web_page_preview=True,
                )
                return True
    except Exception:
        pass
    return False


async def _check_playtype(message: Message, chat_id: int) -> bool:
    try:
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


async def _handle_play(message: Message, video: bool = False):
    chat_id = message.chat.id
    user = message.from_user
    user_name = user.mention
    user_id = user.id

    if await _check_maintenance(message):
        return
    if await _check_playtype(message, chat_id):
        return

    lang = await get_lang(chat_id)
    _ = get_string(lang)

    # Detect file reply
    tg_audio = None
    tg_video = None
    if message.reply_to_message:
        r = message.reply_to_message
        tg_audio = r.audio or r.voice
        tg_video = r.video or r.document if video else None

    url = await YouTube.url(message)

    if tg_audio is None and tg_video is None and url is None:
        if len(message.command) < 2:
            await message.reply_text(
                f"<blockquote>{_BRAND}</blockquote>\n\n"
                f"<blockquote>{_EM['music']} <b>ᴜꜱᴀɢᴇ</b>\n"
                f"{_EM['dot']} /play [ꜱᴏɴɢ ɴᴀᴍᴇ / ᴜʀʟ]\n"
                f"{_EM['video']} /vplay [ᴠɪᴅᴇᴏ ɴᴀᴍᴇ / ᴜʀʟ]</blockquote>"
            )
            return

    # ── Telegram file ──────────────────────────────────────────────────────────
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
            file_path = await app.download_media(
                file_obj.file_id,
                file_name=f"downloads/tg_{file_obj.file_id}.file",
            )
        except Exception as e:
            return await message.reply_text(
                f"<blockquote>{_BRAND}</blockquote>\n\n"
                f"<blockquote>❌ ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ: {type(e).__name__}</blockquote>"
            )

        is_video_type = video or bool(tg_video)
        streamtype = "video" if is_video_type else "audio"

        if await is_active_chat(chat_id):
            await put_queue(
                chat_id, chat_id, file_path, title, duration,
                user_name, "telegram", user_id, streamtype,
            )
            position = len(db.get(chat_id)) - 1
            btn = aq_markup(_, chat_id)
            await app.send_message(
                chat_id=chat_id,
                text=_["queue_4"].format(position, title[:27], duration, user_name),
                reply_markup=InlineKeyboardMarkup(btn),
            )
        else:
            db[chat_id] = []
            await JARVIS.join_call(chat_id, chat_id, file_path, video=is_video_type)
            await put_queue(
                chat_id, chat_id, file_path, title, duration,
                user_name, "telegram", user_id, streamtype,
            )
            button = stream_markup(_, chat_id)
            caption = _["stream_1"].format(
                SUPPORT_CHAT, title[:23], duration, user_name
            )
            run = await _send_stream_msg(chat_id, caption, InlineKeyboardMarkup(button))
            if db.get(chat_id):
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
        return

    # ── YouTube URL or search query ────────────────────────────────────────────
    query = url if url else (
        message.text.split(None, 1)[1] if len(message.command) > 1 else None
    )

    if not query:
        return await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ɴᴏ ǫᴜᴇʀʏ ᴘʀᴏᴠɪᴅᴇᴅ.</blockquote>"
        )

    # ── Live stream check ──────────────────────────────────────────────────────
    if "youtube.com" in query or "youtu.be" in query:
        try:
            if await YouTube.check_live(query):
                vidid = query.split("v=")[-1].split("&")[0].split("/")[-1]
                title, duration_min, _, thumbnail, vidid2 = await YouTube.details(vidid, videoid=True)
                if vidid2:
                    vidid = vidid2

                if await is_active_chat(chat_id):
                    await put_queue(
                        chat_id, chat_id, f"live_{vidid}", title, "Live",
                        user_name, vidid, user_id, "video" if video else "audio",
                    )
                    position = len(db.get(chat_id)) - 1
                    btn = aq_markup(_, chat_id)
                    await app.send_message(
                        chat_id=chat_id,
                        text=_["queue_4"].format(position, title[:27], "Live", user_name),
                        reply_markup=InlineKeyboardMarkup(btn),
                    )
                else:
                    db[chat_id] = []
                    n, link = await YouTube.video(query)
                    if n == 0 or not link:
                        return await message.reply_text(
                            f"<blockquote>{_BRAND}</blockquote>\n\n"
                            f"<blockquote>❌ ᴄᴀɴɴᴏᴛ ꜰᴇᴛᴄʜ ʟɪᴠᴇ ꜱᴛʀᴇᴀᴍ.</blockquote>"
                        )
                    await JARVIS.join_call(chat_id, chat_id, link, video=video)
                    await put_queue(
                        chat_id, chat_id, f"live_{vidid}", title, "Live",
                        user_name, vidid, user_id, "video" if video else "audio",
                    )
                    button = stream_markup(_, chat_id)
                    caption = _["stream_1"].format(
                        f"https://t.me/{BOT_USERNAME.lstrip('@')}?start=info_{vidid}",
                        title[:23], "Live", user_name,
                    )
                    run = await _send_stream_msg(chat_id, caption, InlineKeyboardMarkup(button))
                    if db.get(chat_id):
                        db[chat_id][0]["mystic"] = run
                        db[chat_id][0]["markup"] = "tg"
                return
        except Exception:
            pass

    # ── Normal YouTube search/URL ──────────────────────────────────────────────
    try:
        title, duration_min, duration_sec, thumbnail, vidid = await YouTube.details(
            query, videoid=False
        )
    except Exception as e:
        return await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ɴᴏᴛʜɪɴɢ ꜰᴏᴜɴᴅ.\n{_EM['dot']} {type(e).__name__}</blockquote>"
        )

    if str(duration_min) == "None" or not vidid:
        return await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ᴄᴏᴜʟᴅ ɴᴏᴛ ꜰᴇᴛᴄʜ ᴛʀᴀᴄᴋ ᴅᴇᴛᴀɪʟꜱ.</blockquote>"
        )

    if duration_sec and duration_sec > DURATION_LIMIT:
        return await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ᴛʀᴀᴄᴋ ɪꜱ ᴛᴏᴏ ʟᴏɴɢ.\n"
            f"{_EM['dot']} ᴍᴀx: <code>{DURATION_LIMIT // 60} ᴍɪɴᴜᴛᴇꜱ</code></blockquote>"
        )

    # Pre-warm CDN URL cache as soon as we have the vidid
    asyncio.create_task(_trigger_bg_cache(vidid))

    # ── Download ───────────────────────────────────────────────────────────────
    try:
        file_path, direct = await YouTube.download(
            vidid, None, videoid=True, video=video
        )
    except Exception as e:
        return await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ.\n{_EM['dot']} {type(e).__name__}</blockquote>"
        )

    if not file_path:
        return await message.reply_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ — ᴛʀʏ ᴀɢᴀɪɴ.</blockquote>"
        )

    streamtype = "video" if video else "audio"
    stored_file = file_path if direct else f"vid_{vidid}"
    title_t = title.title()

    # ── Queue or Play ──────────────────────────────────────────────────────────
    if await is_active_chat(chat_id):
        await put_queue(
            chat_id, chat_id, stored_file, title_t, duration_min,
            user_name, vidid, user_id, streamtype,
        )
        position = len(db.get(chat_id)) - 1
        btn = aq_markup(_, chat_id)
        await app.send_message(
            chat_id=chat_id,
            text=_["queue_4"].format(position, title_t[:27], duration_min, user_name),
            reply_markup=InlineKeyboardMarkup(btn),
        )
    else:
        db[chat_id] = []
        await JARVIS.join_call(
            chat_id, chat_id, file_path, video=video, image=thumbnail
        )
        await put_queue(
            chat_id, chat_id, stored_file, title_t, duration_min,
            user_name, vidid, user_id, streamtype,
        )
        button = stream_markup(_, chat_id, autoplay_on=await is_autoplay(chat_id))
        caption = _["stream_1"].format(
            f"https://t.me/{BOT_USERNAME.lstrip('@')}?start=info_{vidid}",
            title_t[:23],
            duration_min,
            user_name,
        )
        run = await _send_stream_msg(chat_id, caption, InlineKeyboardMarkup(button))
        if db.get(chat_id):
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "stream"


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
    from KHUSHI.utils.formatters import seconds_to_min
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
