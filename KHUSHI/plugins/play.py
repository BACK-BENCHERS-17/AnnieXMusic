"""KHUSHI — Play Plugin: direct VC stream, same notification as AnnieMusic."""

import asyncio
import logging
import random

from pyrogram import enums, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, Message

from KHUSHI.utils.inline import InlineKeyboardButton

from strings import get_string
from KHUSHI import YouTube, app
from KHUSHI.core.call import JARVIS, _start_progress_timer
from KHUSHI.misc import SUDOERS, db
from KHUSHI.utils.database import (
    get_lang,
    get_playtype,
    is_active_chat,
    is_autoplay,
    is_maintenance,
)
from KHUSHI.utils.decorators import KhushiAdminCheck as AdminRightsCheck
from KHUSHI.utils.downloader import _trigger_bg_cache, extract_video_id
from KHUSHI.utils.inline import aq_markup, stream_markup, stream_markup_timer
from KHUSHI.utils.stream.queue import put_queue
from KHUSHI.utils.thumbnails import get_thumb
from config import AYU, BANNED_USERS, BOT_USERNAME, DURATION_LIMIT, OWNER_ID, PING_IMG_URL, START_IMGS, SUPPORT_CHAT, adminlist
from KHUSHI.utils.security import check_and_alert

from KHUSHI.utils.ui import BRAND as _BRAND, E as _EM, msg as _msg, err as _err, info as _info, panel as _panel
from KHUSHI.utils.exceptions import AssistantErr

_log = logging.getLogger(__name__)


async def _send_stream_msg(
    chat_id: int,
    caption: str,
    reply_markup,
    thumbnail: str = None,
) -> object:
    """
    Send stream notification with photo thumbnail when available.

    If `thumbnail` is provided (YouTube thumbnail URL), sends a photo message
    with the caption — looks great and is reliable.
    Falls back to a plain text message when no thumbnail is available.
    """
    if thumbnail:
        try:
            return await app.send_photo(
                chat_id,
                photo=thumbnail,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            _log.warning(f"[notify] send_photo failed for chat={chat_id}: {e}")

    try:
        return await app.send_message(
            chat_id,
            text=caption,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception as e:
        _log.error(f"[notify] send_message also failed for chat={chat_id}: {e}")
        return None


async def _check_maintenance(message: Message) -> bool:
    try:
        if await is_maintenance():
            if message.from_user.id not in SUDOERS:
                _sc = SUPPORT_CHAT if SUPPORT_CHAT.startswith("http") else f"https://t.me/{SUPPORT_CHAT.lstrip('@')}"
                await message.reply_text(
                    f"<blockquote>{_BRAND}</blockquote>\n\n"
                    f"<blockquote>{_EM['zap']} <b>ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ</b>\n"
                    f"{_EM['dot']} ᴠɪꜱɪᴛ "
                    f"<a href='{_sc}'>ꜱᴜᴘᴘᴏʀᴛ</a>.</blockquote>",
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
    try:
        await message.delete()
    except Exception:
        pass

    msg_chat_id = message.chat.id  # group — always used for sending messages
    user = message.from_user
    user_name = user.mention
    user_id = user.id

    if await _check_maintenance(message):
        return
    if await _check_playtype(message, msg_chat_id):
        return

    lang = await get_lang(msg_chat_id)
    _ = get_string(lang)

    # ── Channel play detection ──────────────────────────────────────────────────
    # /cplay and /cvplay route audio to the linked channel's VC instead of group
    cmd = message.command[0].lower().lstrip("/!.")
    is_channel_cmd = cmd.startswith("c")  # cplay / cvplay
    vc_chat_id = msg_chat_id              # default: same as group
    channel_name = None
    if is_channel_cmd:
        from KHUSHI.utils.database import get_cmode
        _linked = await get_cmode(msg_chat_id)
        if _linked is None:
            return await message.reply_text(_["setting_7"])
        try:
            _ch_obj = await app.get_chat(_linked)
            channel_name = _ch_obj.title
        except Exception:
            return await message.reply_text(_["cplay_4"])
        vc_chat_id = _linked

    # Detect file reply
    tg_audio = None
    tg_video = None
    if message.reply_to_message:
        r = message.reply_to_message
        # Audio mode: also accept video replies (audio will be extracted by downloader)
        tg_audio = r.audio or r.voice or (r.video if not video else None)
        tg_video = r.video or r.document if video else None

    url = await YouTube.url(message)

    if tg_audio is None and tg_video is None and url is None:
        if len(message.command) < 2:
            _sc = SUPPORT_CHAT if SUPPORT_CHAT.startswith("http") else f"https://t.me/{SUPPORT_CHAT.lstrip('@')}"
            _play_kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("˹ꜱᴜᴘᴘᴏʀᴛ˼", url=_sc, style="success"),
                    InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close", style="danger"),
                ]
            ])
            await app.send_message(
                msg_chat_id,
                _panel("ʜᴏᴡ ᴛᴏ ᴘʟᴀʏ", [
                    f"{_EM['music']} <code>/play</code> [ꜱᴏɴɢ ɴᴀᴍᴇ / ʏᴛ ᴜʀʟ]",
                    f"{_EM['video']} <code>/vplay</code> [ᴠɪᴅᴇᴏ ɴᴀᴍᴇ / ʏᴛ ᴜʀʟ]",
                    f"{_EM['dot']} <code>/play</code> [ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴛᴇʟᴇɢʀᴀᴍ ꜰɪʟᴇ]",
                    f"{_EM['zap']} <code>/song</code> [ꜱᴏɴɢ] — ᴅᴏᴡɴʟᴏᴀᴅ ᴛᴏ ᴅᴍ",
                ]),
                reply_markup=_play_kb,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return

    # ── Loading indicator ──────────────────────────────────────────────────────
    try:
        mystic = await app.send_message(msg_chat_id, random.choice(AYU))
    except Exception:
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
            return await mystic.edit_text(
                _err(f"ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ: <code>{type(e).__name__}</code>")
            )

        is_video_type = video or bool(tg_video)
        streamtype = "video" if is_video_type else "audio"

        try:
            await mystic.delete()
        except Exception:
            pass

        if await is_active_chat(vc_chat_id):
            await put_queue(
                vc_chat_id, msg_chat_id, file_path, title, duration,
                user_name, "telegram", user_id, streamtype,
            )
            position = len(db.get(vc_chat_id)) - 1
            btn = aq_markup(_, vc_chat_id)
            await app.send_message(
                chat_id=msg_chat_id,
                text=_["queue_4"].format(position, title[:27], duration, user_name),
                reply_markup=InlineKeyboardMarkup(btn),
            )
        else:
            db[vc_chat_id] = []
            try:
                await JARVIS.join_call(vc_chat_id, msg_chat_id, file_path, video=is_video_type)
            except AssistantErr as ae:
                db.pop(vc_chat_id, None)
                return await message.reply_text(str(ae))
            except Exception as je:
                db.pop(vc_chat_id, None)
                return await message.reply_text(
                    f"<blockquote>{_BRAND}</blockquote>\n\n"
                    f"<blockquote>❌ ᴠᴄ ᴊᴏɪɴ ꜰᴀɪʟᴇᴅ.\n{_EM['dot']} {type(je).__name__}</blockquote>"
                )
            await put_queue(
                vc_chat_id, msg_chat_id, file_path, title, duration,
                user_name, "telegram", user_id, streamtype,
            )
            button = stream_markup_timer(_, vc_chat_id, "0:00", duration, autoplay_on=await is_autoplay(vc_chat_id))
            _tg_title_short = title[:35] + "..." if len(title) > 35 else title
            _tg_type = "ᴠɪᴅᴇᴏ" if is_video_type else "ᴀᴜᴅɪᴏ"
            caption = _panel(
                "ɴᴏᴡ ᴩʟᴀʏɪɴɢ",
                [
                    f"{_EM['music']} <b>ᴛɪᴛʟᴇ:</b>  {_tg_title_short}",
                    f"{_EM['video'] if is_video_type else _EM['headset']} <b>ᴛʏᴩᴇ:</b>  {_tg_type} ꜰɪʟᴇ",
                    f"{_EM['clock']} <b>ᴅᴜʀᴀᴛɪᴏɴ:</b>  {duration}",
                    f"{_EM['mic']} <b>ʀᴇǫᴜᴇꜱᴛᴇᴅ ʙʏ:</b>  {user_name}",
                ],
            )
            run = await _send_stream_msg(msg_chat_id, caption, InlineKeyboardMarkup(button))
            if db.get(vc_chat_id):
                db[vc_chat_id][0]["mystic"] = run
                db[vc_chat_id][0]["markup"] = "stream"
            _start_progress_timer(vc_chat_id)
        return

    # ── YouTube URL or search query ────────────────────────────────────────────
    query = url if url else (
        message.text.split(None, 1)[1] if len(message.command) > 1 else None
    )

    if not query:
        return await mystic.edit_text(_err("ɴᴏ ǫᴜᴇʀʏ ᴘʀᴏᴠɪᴅᴇᴅ."))

    # ── Security: block injection / exfiltration attempts ─────────────────────
    if await check_and_alert(app, OWNER_ID, message, query):
        try:
            await mystic.delete()
        except Exception:
            pass
        return await message.reply_text(
            _msg("ʙʟᴏᴄᴋᴇᴅ", "ᴍᴀʟɪᴄɪᴏᴜs ɪɴᴘᴜᴛ ᴅᴇᴛᴇᴄᴛᴇᴅ ᴀɴᴅ ʙʟᴏᴄᴋᴇᴅ.", emoji_key="shield")
        )

    # ── Early URL extraction for YouTube links (head start) ────────────────────
    # For URL-type queries we can extract the video ID immediately without waiting
    # for details(). Fire fast_get_stream() in background right now — it warms
    # both the in-process URL cache and the webserver cache. By the time
    # YouTube.download() is called below, the URL (or file) is already ready
    # → shaves 2–5 seconds off first-play latency.
    _early_vid = None
    if ("youtube.com" in query or "youtu.be" in query) and "/live/" not in query:
        try:
            _early_vid = extract_video_id(YouTube._prepare_link(query))
            if _early_vid:
                from KHUSHI.utils.downloader import fast_get_stream as _fgs
                asyncio.create_task(_fgs(_early_vid))
        except Exception:
            pass

    # ── Live stream check ──────────────────────────────────────────────────────
    if "youtube.com" in query or "youtu.be" in query:
        try:
            if await YouTube.check_live(query):
                vidid = extract_video_id(YouTube._prepare_link(query))
                try:
                    title, duration_min, _, thumbnail, vidid2 = await YouTube.details(vidid, videoid=True)
                    if vidid2:
                        vidid = vidid2
                except Exception:
                    title = vidid
                    thumbnail = ""

                try:
                    await mystic.delete()
                except Exception:
                    pass

                if await is_active_chat(vc_chat_id):
                    await put_queue(
                        vc_chat_id, msg_chat_id, f"live_{vidid}", title, "Live",
                        user_name, vidid, user_id, "video" if video else "audio",
                    )
                    position = len(db.get(vc_chat_id)) - 1
                    btn = aq_markup(_, vc_chat_id)
                    await app.send_message(
                        chat_id=msg_chat_id,
                        text=_["queue_4"].format(position, title[:27], "Live", user_name),
                        reply_markup=InlineKeyboardMarkup(btn),
                    )
                else:
                    db[vc_chat_id] = []
                    n, link = await YouTube.video(query)
                    if n == 0 or not link:
                        return await message.reply_text(
                            f"<blockquote>{_BRAND}</blockquote>\n\n"
                            f"<blockquote>❌ ᴄᴀɴɴᴏᴛ ꜰᴇᴛᴄʜ ʟɪᴠᴇ ꜱᴛʀᴇᴀᴍ.</blockquote>"
                        )
                    try:
                        await JARVIS.join_call(vc_chat_id, msg_chat_id, link, video=video)
                    except AssistantErr as ae:
                        db.pop(vc_chat_id, None)
                        return await message.reply_text(str(ae))
                    except Exception as je:
                        db.pop(vc_chat_id, None)
                        return await message.reply_text(
                            f"<blockquote>{_BRAND}</blockquote>\n\n"
                            f"<blockquote>❌ ᴠᴄ ᴊᴏɪɴ ꜰᴀɪʟᴇᴅ.\n{_EM['dot']} {type(je).__name__}</blockquote>"
                        )
                    await put_queue(
                        vc_chat_id, msg_chat_id, f"live_{vidid}", title, "Live",
                        user_name, vidid, user_id, "video" if video else "audio",
                    )
                    button = stream_markup(_, vc_chat_id)
                    _live_title_short = title[:35] + "..." if len(title) > 35 else title
                    caption = _panel(
                        "ʟɪᴠᴇ ꜱᴛʀᴇᴀᴍ",
                        [
                            f"{_EM['live']} <b>ꜱᴛʀᴇᴀᴍɪɴɢ:</b>  <a href='https://www.youtube.com/watch?v={vidid}'>{_live_title_short}</a>",
                            f"{_EM['radio']} <b>ᴛʏᴩᴇ:</b>  ʟɪᴠᴇ",
                            f"{_EM['mic']} <b>ʀᴇǫᴜᴇꜱᴛᴇᴅ ʙʏ:</b>  {user_name}",
                        ],
                    )
                    run = await _send_stream_msg(msg_chat_id, caption, InlineKeyboardMarkup(button), thumbnail=thumbnail)
                    if db.get(vc_chat_id):
                        db[vc_chat_id][0]["mystic"] = run
                        db[vc_chat_id][0]["markup"] = "stream"
                    _start_progress_timer(vc_chat_id)
                return
        except Exception:
            pass

    # ── Normal YouTube search/URL ──────────────────────────────────────────────
    try:
        title, duration_min, duration_sec, thumbnail, vidid = await YouTube.details(
            query, videoid=False
        )
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
            f"{_EM['dot']} ᴍᴀx: <code>{DURATION_LIMIT // 60} ᴍɪɴᴜᴛᴇꜱ</code></blockquote>"
        )

    # Pre-warm CDN URL cache as soon as we have the vidid.
    # For audio: fast_get_stream warms the in-process URL cache so that the
    # YouTube.download() call below gets an instant cache hit instead of waiting
    # 5-8s for yt-dlp extraction. For video: trigger_bg_cache for file caching.
    if not video:
        from KHUSHI.utils.downloader import fast_get_stream as _fgs_warm
        asyncio.create_task(_fgs_warm(vidid))
    asyncio.create_task(_trigger_bg_cache(vidid))

    # ── Download ───────────────────────────────────────────────────────────────
    try:
        file_path, direct = await YouTube.download(
            vidid, None, videoid=True, video=video
        )
    except Exception as e:
        return await mystic.edit_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ.\n{_EM['dot']} {type(e).__name__}</blockquote>"
        )

    if not file_path:
        return await mystic.edit_text(
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            f"<blockquote>❌ ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ — ᴛʀʏ ᴀɢᴀɪɴ.</blockquote>"
        )

    try:
        await mystic.delete()
    except Exception:
        pass

    streamtype = "video" if video else "audio"
    stored_file = file_path if direct else f"vid_{vidid}"
    title_t = title.title()

    # ── Queue or Play ──────────────────────────────────────────────────────────
    if await is_active_chat(vc_chat_id):
        await put_queue(
            vc_chat_id, msg_chat_id, stored_file, title_t, duration_min,
            user_name, vidid, user_id, streamtype,
        )
        position = len(db.get(vc_chat_id)) - 1
        btn = aq_markup(_, vc_chat_id)
        await app.send_message(
            chat_id=msg_chat_id,
            text=_["queue_4"].format(position, title_t[:27], duration_min, user_name),
            reply_markup=InlineKeyboardMarkup(btn),
        )
    else:
        db[vc_chat_id] = []
        try:
            await JARVIS.join_call(
                vc_chat_id, msg_chat_id, file_path, video=video, image=thumbnail
            )
        except AssistantErr as ae:
            db.pop(vc_chat_id, None)
            return await mystic.edit_text(str(ae))
        except Exception as je:
            db.pop(vc_chat_id, None)
            return await mystic.edit_text(
                f"<blockquote>{_BRAND}</blockquote>\n\n"
                f"<blockquote>❌ ᴠᴄ ᴊᴏɪɴ ꜰᴀɪʟᴇᴅ.\n{_EM['dot']} {type(je).__name__}: {je}</blockquote>"
            )
        await put_queue(
            vc_chat_id, msg_chat_id, stored_file, title_t, duration_min,
            user_name, vidid, user_id, streamtype,
        )
        button = stream_markup_timer(_, vc_chat_id, "0:00", duration_min, autoplay_on=await is_autoplay(vc_chat_id))
        _title_short = title_t[:35] + "..." if len(title_t) > 35 else title_t
        caption = _panel(
            "ɴᴏᴡ ᴩʟᴀʏɪɴɢ",
            [
                f"{_EM['music']} <b>ɴᴏᴡ ᴘʟᴀʏɪɴɢ:</b> <a href='https://www.youtube.com/watch?v={vidid}'>{_title_short}</a>",
                f"{_EM['clock']} <b>ᴅᴜʀᴀᴛɪᴏɴ:</b>  {duration_min}",
                f"{_EM['mic']} <b>ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ:</b>  {user_name}",
            ],
        )
        run = await _send_stream_msg(msg_chat_id, caption, InlineKeyboardMarkup(button), thumbnail=thumbnail)
        if db.get(vc_chat_id):
            db[vc_chat_id][0]["mystic"] = run
            db[vc_chat_id][0]["markup"] = "stream"
        _start_progress_timer(vc_chat_id)


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
    filters.command(["seek", "cseek", "seekback", "cseekback"], prefixes=["/", ".", "!"])
    & filters.group
    & ~BANNED_USERS
)
@AdminRightsCheck
async def kseek(_, message: Message, lang, chat_id):
    cmd = message.command[0].lower().lstrip("/!.")
    is_back = "back" in cmd
    if len(message.command) < 2:
        usage = "<code>/seekback [sec]</code>" if is_back else "<code>/seek [sec]</code>"
        return await message.reply_text(
            _panel("ꜱᴇᴇᴋ", [
                f"{_EM['seek_fwd']} {usage} — ᴊᴜᴍᴘ ꜰᴏʀᴡᴀʀᴅ ᴏʀ ʙᴀᴄᴋ ɪɴ ᴛʜᴇ ᴄᴜʀʀᴇɴᴛ ᴛʀᴀᴄᴋ",
            ])
        )
    check = db.get(chat_id)
    if not check:
        return await message.reply_text(
            _msg("ɴᴏᴛʜɪɴɢ ᴘʟᴀʏɪɴɢ", "ꜱᴛᴀʀᴛ ᴀ ꜱᴏɴɢ ꜰɪʀꜱᴛ ᴡɪᴛʜ <code>/play</code>.", emoji_key="warn")
        )
    # Block seeking on live streams
    _dur_val = str(check[0].get("dur", "")).strip().lower()
    _file_val = str(check[0].get("file", ""))
    if _dur_val == "live" or _file_val.startswith("live_"):
        return await message.reply_text(
            _err("ꜱᴇᴇᴋɪɴɢ ɪꜱ ɴᴏᴛ ꜱᴜᴘᴘᴏʀᴛᴇᴅ ꜰᴏʀ ʟɪᴠᴇ ꜱᴛʀᴇᴀᴍꜱ.")
        )
    try:
        secs_arg = int(message.command[1])
    except ValueError:
        return await message.reply_text(_err("ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ ᴏꜰ ꜱᴇᴄᴏɴᴅꜱ."))
    from KHUSHI.utils.formatters import seconds_to_min
    file_path = check[0].get("file", "")
    total = check[0].get("seconds", 0)
    current = int(check[0].get("played", 0))
    if is_back:
        secs = max(0, current - abs(secs_arg))
    else:
        secs = current + abs(secs_arg)
    if secs < 0 or secs >= int(total):
        return await message.reply_text(
            _err(f"ᴘᴏꜱɪᴛɪᴏɴ ᴏᴜᴛ ᴏꜰ ʀᴀɴɢᴇ. ᴛᴏᴛᴀʟ: <code>{seconds_to_min(total)}</code>")
        )
    dur = seconds_to_min(total)
    played = seconds_to_min(secs)
    mode = check[0].get("streamtype", "audio")
    em_key = "seek_bk" if is_back else "seek_fwd"
    label  = "ꜱᴇᴇᴋᴇᴅ ʙᴀᴄᴋ" if is_back else "ꜱᴇᴇᴋᴇᴅ ꜰᴏʀᴡᴀʀᴅ"
    try:
        await JARVIS.seek_stream(chat_id, file_path, played, dur, mode)
        check[0]["played"] = secs
        _start_progress_timer(chat_id)
        await message.reply_text(
            _msg(label, f"ᴊᴜᴍᴘᴇᴅ ᴛᴏ <code>{played}</code> / <code>{dur}</code>", emoji_key=em_key)
        )
    except Exception as e:
        ename = type(e).__name__
        if ename == "DocumentInvalid":
            errmsg = "ᴠᴏɪᴄᴇ ᴄᴀʟʟ ꜱᴇꜱꜱɪᴏɴ ɪꜱ ɴᴏ ʟᴏɴɢᴇʀ ᴠᴀʟɪᴅ — ᴘʟᴇᴀꜱᴇ ꜱᴛᴏᴘ ᴀɴᴅ ʀᴇꜱᴛᴀʀᴛ ᴘʟᴀʏʙᴀᴄᴋ."
        elif ename in ("NotInCallError", "ConnectionNotFound"):
            errmsg = "ʙᴏᴛ ɪꜱ ɴᴏᴛ ɪɴ ᴀɴ ᴀᴄᴛɪᴠᴇ ᴠᴏɪᴄᴇ ᴄᴀʟʟ."
        elif ename in ("FileError", "AssistantErr"):
            errmsg = "ꜱᴛʀᴇᴀᴍ ꜰɪʟᴇ ɴᴏ ʟᴏɴɢᴇʀ ᴀᴠᴀɪʟᴀʙʟᴇ — ᴘʟᴇᴀꜱᴇ ᴘʟᴀʏ ᴛʜᴇ ꜱᴏɴɢ ᴀɢᴀɪɴ."
        else:
            errmsg = f"ꜱᴇᴇᴋ ꜰᴀɪʟᴇᴅ: <code>{ename}</code>"
        await message.reply_text(_err(errmsg))


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
            _panel("ꜱᴘᴇᴇᴅ", [
                f"{_EM['speed']} <code>/speed [0.5 – 4.0]</code>",
                f"{_EM['dot']} 1.0 = ɴᴏʀᴍᴀʟ  •  2.0 = 2× ꜰᴀꜱᴛ  •  0.5 = ʜᴀʟꜰ",
            ])
        )
    check = db.get(chat_id)
    if not check:
        return await message.reply_text(
            _msg("ɴᴏᴛʜɪɴɢ ᴘʟᴀʏɪɴɢ", "ꜱᴛᴀʀᴛ ᴀ ꜱᴏɴɢ ꜰɪʀꜱᴛ ᴡɪᴛʜ <code>/play</code>.", emoji_key="warn")
        )
    try:
        speed = float(message.command[1])
    except ValueError:
        return await message.reply_text(_err("ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ꜱᴘᴇᴇᴅ (0.5 – 4.0)."))
    if not 0.5 <= speed <= 4.0:
        return await message.reply_text(_err("ꜱᴘᴇᴇᴅ ᴍᴜꜱᴛ ʙᴇ ʙᴇᴛᴡᴇᴇɴ <code>0.5</code> ᴀɴᴅ <code>4.0</code>."))
    try:
        file_path = check[0].get("file", "")
        await JARVIS.speedup_stream(chat_id, file_path, speed, check)
        await message.reply_text(
            _msg("ꜱᴘᴇᴇᴅ ᴄʜᴀɴɢᴇᴅ", f"ᴘʟᴀʏɪɴɢ ᴀᴛ <b>{speed}×</b> ꜱᴘᴇᴇᴅ.", emoji_key="speed")
        )
    except Exception as e:
        await message.reply_text(_err(f"ꜱᴘᴇᴇᴅ ᴄʜᴀɴɢᴇ ꜰᴀɪʟᴇᴅ: <code>{type(e).__name__}</code>"))


# ── RELATED SONG PLAY CALLBACK (rp:{song_name}) ───────────────────────────────
@app.on_callback_query(filters.regex(r"^rp:") & ~BANNED_USERS)
async def related_play_cb(client, query):
    """Play a related-song suggestion from the queue-end buttons.
    In private chat (DM): downloads and sends the audio file.
    In groups: plays in voice chat.
    """
    raw = query.data[3:]  # Everything after "rp:"
    chat_id = query.message.chat.id
    user = query.from_user
    is_private = chat_id > 0  # positive IDs = private/DM chats

    user_name = user.first_name or user.username or "ᴜꜱᴇʀ"
    user_id = user.id

    # New format: "{11-char-vidid}:{title}"  vs old: "{song_name}"
    known_vidid = None
    if len(raw) >= 12 and raw[11] == ":":
        known_vidid = raw[:11]
        song_name = raw[12:]
    else:
        song_name = raw

    if is_private:
        await query.answer("⬇️ ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ…", show_alert=False)
    else:
        await query.answer("ᴘʟᴀʏɪɴɢ… 🎵", show_alert=False)

    # Delete the suggestion card
    try:
        await query.message.delete()
    except Exception:
        pass

    lang = await get_lang(chat_id if not is_private else user_id)
    _ = get_string(lang)

    mystic = await client.send_message(
        chat_id,
        "⬇️ ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ꜱᴏɴɢ…" if is_private else random.choice(AYU)
    )

    # ── Resolve track details ─────────────────────────────────────────────────
    if known_vidid:
        # We already know the video ID — fetch details directly (faster, no search)
        try:
            title, duration_min, duration_sec, thumbnail, vidid = await YouTube.details(
                known_vidid, videoid=True
            )
        except Exception as e:
            return await mystic.edit_text(
                _err(f"ꜰᴇᴛᴄʜ ꜰᴀɪʟᴇᴅ: <code>{type(e).__name__}</code>")
            )
    else:
        # Old format — search by song name
        try:
            title, duration_min, duration_sec, thumbnail, vidid = await YouTube.details(
                song_name, videoid=False
            )
        except Exception as e:
            return await mystic.edit_text(
                _err(f"ɴᴏᴛʜɪɴɢ ꜰᴏᴜɴᴅ ꜰᴏʀ ᴛʜɪs sᴏɴɢ. (<code>{type(e).__name__}</code>)")
            )

    if not vidid:
        return await mystic.edit_text(_err("ᴄᴏᴜʟᴅ ɴᴏᴛ ꜰᴇᴛᴄʜ ᴛʀᴀᴄᴋ ᴅᴇᴛᴀɪʟꜱ."))

    if duration_sec and duration_sec > DURATION_LIMIT:
        return await mystic.edit_text(_err("ᴛʀᴀᴄᴋ ɪs ᴛᴏᴏ ʟᴏɴɢ ᴛᴏ ᴘʟᴀʏ."))

    asyncio.create_task(_trigger_bg_cache(vidid))

    # ── DM: Download and send audio file directly ──────────────────────────────
    if is_private:
        try:
            file_path, direct = await YouTube.download(vidid, None, videoid=True, video=False)
        except Exception as e:
            return await mystic.edit_text(
                _err(f"ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ: <code>{type(e).__name__}</code>")
            )
        if not file_path:
            return await mystic.edit_text(_err("ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ — ᴘʟᴇᴀꜱᴇ ᴛʀʏ ᴀɢᴀɪɴ."))
        try:
            await mystic.delete()
        except Exception:
            pass
        title_t = title.title()
        try:
            await client.send_audio(
                chat_id=chat_id,
                audio=file_path,
                title=title_t,
                duration=duration_sec or 0,
                caption=(
                    f"<b>{title_t}</b>\n"
                    f"<emoji id='5972072533833289156'>🔹</emoji> ᴅᴜʀᴀᴛɪᴏɴ: <code>{duration_min}</code>\n"
                    f"<emoji id='5042334757040423886'>⚡️</emoji> ᴘᴏᴡᴇʀᴇᴅ ʙʏ ᴋʜᴜsʜɪ"
                ),
            )
        except Exception:
            await client.send_document(chat_id=chat_id, document=file_path, caption=title_t)
        return

    # ── Download ──────────────────────────────────────────────────────────────
    try:
        file_path, direct = await YouTube.download(vidid, None, videoid=True, video=False)
    except Exception as e:
        return await mystic.edit_text(
            _err(f"ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ: <code>{type(e).__name__}</code>")
        )

    if not file_path:
        return await mystic.edit_text(_err("ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ — ᴘʟᴇᴀꜱᴇ ᴛʀʏ ᴀɢᴀɪɴ."))

    try:
        await mystic.delete()
    except Exception:
        pass

    stored_file = file_path if direct else f"vid_{vidid}"
    title_t = title.title()

    # ── Queue or Play ─────────────────────────────────────────────────────────
    if await is_active_chat(chat_id):
        await put_queue(
            chat_id, chat_id, stored_file, title_t, duration_min,
            user_name, vidid, user_id, "audio",
        )
        position = len(db.get(chat_id)) - 1
        btn = aq_markup(_, chat_id)
        await client.send_message(
            chat_id=chat_id,
            text=_["queue_4"].format(position, title_t[:27], duration_min, user_name),
            reply_markup=InlineKeyboardMarkup(btn),
        )
    else:
        db[chat_id] = []
        try:
            await JARVIS.join_call(chat_id, chat_id, file_path, video=False, image=thumbnail)
        except AssistantErr as ae:
            db.pop(chat_id, None)
            return await client.send_message(chat_id, str(ae))
        except Exception as je:
            db.pop(chat_id, None)
            return await client.send_message(
                chat_id,
                f"<blockquote>{_BRAND}</blockquote>\n\n"
                f"<blockquote>❌ ᴠᴄ ᴊᴏɪɴ ꜰᴀɪʟᴇᴅ.\n{_EM['dot']} {type(je).__name__}</blockquote>",
            )
        await put_queue(
            chat_id, chat_id, stored_file, title_t, duration_min,
            user_name, vidid, user_id, "audio",
        )
        button = stream_markup_timer(_, chat_id, "0:00", duration_min, autoplay_on=await is_autoplay(chat_id))
        _cb_title_short = title_t[:35] + "..." if len(title_t) > 35 else title_t
        caption = _panel(
            "ɴᴏᴡ ᴩʟᴀʏɪɴɢ",
            [
                f"{_EM['music']} <b>ɴᴏᴡ ᴘʟᴀʏɪɴɢ:</b>  <a href='https://www.youtube.com/watch?v={vidid}'>{_cb_title_short}</a>",
                f"{_EM['clock']} <b>ᴅᴜʀᴀᴛɪᴏɴ:</b>  {duration_min}",
                f"{_EM['mic']} <b>ʀᴇǫᴜᴇꜱᴛᴇᴅ ʙʏ:</b>  {user_name}",
            ],
        )
        run = await _send_stream_msg(chat_id, caption, InlineKeyboardMarkup(button), thumbnail=thumbnail)
        if db.get(chat_id):
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "stream"


# ── CLOSE CALLBACK ────────────────────────────────────────────────────────────
@app.on_callback_query(filters.regex("^close$") & ~BANNED_USERS)
async def close_cb(_, query):
    try:
        await query.message.delete()
    except Exception:
        await query.answer()
