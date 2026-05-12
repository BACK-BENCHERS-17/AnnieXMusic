"""KHUSHI — /playforce: skip queue and play a song immediately."""

import asyncio
import logging

from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, Message

from strings import get_string
from KHUSHI import YouTube, app
from KHUSHI.core.call import JARVIS, _start_progress_timer
from KHUSHI.misc import SUDOERS, db
from KHUSHI.utils.database import (
    get_lang,
    is_active_chat,
    is_autoplay,
    is_maintenance,
)
from KHUSHI.utils.decorators import KhushiAdminCheck as AdminRightsCheck
from KHUSHI.utils.downloader import _trigger_bg_cache, extract_video_id
from KHUSHI.utils.inline import aq_markup, stream_markup_timer
from KHUSHI.utils.stream.autoclear import auto_clean
from KHUSHI.utils.stream.queue import put_queue
from KHUSHI.utils.exceptions import AssistantErr
from config import BANNED_USERS, DURATION_LIMIT, SUPPORT_CHAT

_log = logging.getLogger(__name__)

_E = {
    "music":  '<emoji id="5994566609002303309">🎵</emoji>',
    "dot":    '<emoji id="5972072533833289156">🔹</emoji>',
    "fire":   '<emoji id="5042225965518816316">🔥</emoji>',
    "zap":    '<emoji id="5042334757040423886">⚡️</emoji>',
    "star":   '<emoji id="5039827436737397847">✨</emoji>',
    "mic":    '<emoji id="6030722571412967168">🎤</emoji>',
    "clock":  '<emoji id="5123230779593196220">⏰</emoji>',
    "cross":  '<emoji id="5040042498634810056">❌</emoji>',
    "warn":   '<emoji id="5420323339723881652">⚠️</emoji>',
}


def _panel(title: str, rows: list) -> str:
    bar_open  = f"┌────── ˹ {title} ˼ ─── ⏤‌●"
    bar_close = "└──────────────────●"
    body = bar_open + "\n" + "\n".join(f"┆{r}" for r in rows) + "\n" + bar_close
    return f"<blockquote>{body}</blockquote>"


def _err(text: str) -> str:
    return f"<blockquote>{_E['cross']} <b>ᴇʀʀᴏʀ</b>\n{_E['dot']} {text}</blockquote>"


@app.on_message(
    filters.command(["playforce", "pf", "fplay", "forcep"],
                    prefixes=["/", "!", "."])
    & filters.group
    & ~BANNED_USERS
)
@AdminRightsCheck
async def playforce_cmd(_, message: Message, lang, chat_id):
    _ = get_string(lang)

    try:
        await message.delete()
    except Exception:
        pass

    if await is_maintenance():
        from KHUSHI.misc import SUDOERS as _SUDOERS
        if message.from_user.id not in _SUDOERS:
            return

    query = None
    if message.reply_to_message:
        r = message.reply_to_message
        if r.audio or r.voice:
            return await message.reply_text(
                _err("ʀᴇᴘʟʏ ᴛᴏ ᴀᴜᴅɪᴏ ɴᴏᴛ ꜱᴜᴘᴘᴏʀᴛᴇᴅ ɪɴ /ᴘʟᴀʏꜰᴏʀᴄᴇ — ᴜꜱᴇ /ᴘʟᴀʏ ɪɴꜱᴛᴇᴀᴅ.")
            )
    if len(message.command) > 1:
        query = message.text.split(None, 1)[1].strip()
    if not query:
        return await message.reply_text(
            _panel(
                f"{_E['zap']} ᴘʟᴀʏꜰᴏʀᴄᴇ",
                [
                    f"{_E['fire']} ᴄʟᴇᴀʀꜱ ᴛʜᴇ ǫᴜᴇᴜᴇ ᴀɴᴅ ᴘʟᴀʏꜱ ɪᴍᴍᴇᴅɪᴀᴛᴇʟʏ",
                    f"{_E['dot']} <code>/playforce [ꜱᴏɴɢ ɴᴀᴍᴇ / ʏᴛ ᴜʀʟ]</code>",
                    f"{_E['dot']} ᴀʟɪᴀꜱᴇꜱ: /pf, /fplay, /forcep",
                ],
            ),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )

    try:
        mystic = await app.send_message(
            chat_id,
            f"<blockquote>{_E['fire']} <b>ꜰᴏʀᴄɪɴɢ ᴘʟᴀʏ…</b></blockquote>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        return

    url = await YouTube.url(message)
    search_q = url if url else query

    _early_vid = None
    if url and ("youtube.com" in url or "youtu.be" in url) and "/live/" not in url:
        try:
            _early_vid = extract_video_id(YouTube._prepare_link(url))
            if _early_vid:
                from KHUSHI.utils.downloader import fast_get_stream as _fgs
                asyncio.create_task(_fgs(_early_vid))
        except Exception:
            pass

    try:
        title, duration_min, duration_sec, thumbnail, vidid = await YouTube.details(
            search_q, videoid=False
        )
    except Exception as e:
        return await mystic.edit_text(_err(f"ɴᴏᴛʜɪɴɢ ꜰᴏᴜɴᴅ: <code>{type(e).__name__}</code>"))

    if str(duration_min) == "None" or not vidid:
        return await mystic.edit_text(_err("ᴄᴏᴜʟᴅ ɴᴏᴛ ꜰᴇᴛᴄʜ ᴛʀᴀᴄᴋ ᴅᴇᴛᴀɪʟꜱ."))

    if duration_sec and duration_sec > DURATION_LIMIT:
        return await mystic.edit_text(
            _err(f"ᴛʀᴀᴄᴋ ɪꜱ ᴛᴏᴏ ʟᴏɴɢ. ᴍᴀx: <code>{DURATION_LIMIT // 60} ᴍɪɴᴜᴛᴇꜱ</code>")
        )

    from KHUSHI.utils.downloader import fast_get_stream as _fgs_warm
    asyncio.create_task(_fgs_warm(vidid))
    asyncio.create_task(_trigger_bg_cache(vidid))
    await asyncio.sleep(0)

    try:
        file_path, direct = await YouTube.download(vidid, None, videoid=True, video=False)
    except Exception as e:
        return await mystic.edit_text(_err(f"ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ: <code>{type(e).__name__}</code>"))

    if not file_path:
        return await mystic.edit_text(_err("ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ — ᴘʟᴇᴀꜱᴇ ᴛʀʏ ᴀɢᴀɪɴ."))

    try:
        await mystic.delete()
    except Exception:
        pass

    title_t = title.title()
    stored_file = file_path if direct else f"vid_{vidid}"
    user_name = message.from_user.mention
    user_id = message.from_user.id

    is_active = await is_active_chat(chat_id)

    if is_active:
        old_queue = db.get(chat_id, [])
        for item in old_queue:
            try:
                await auto_clean(item)
            except Exception:
                pass
        db[chat_id] = []

        await put_queue(
            chat_id, chat_id, stored_file, title_t, duration_min,
            user_name, vidid, user_id, "audio",
        )

        button = stream_markup_timer(
            _, chat_id, "0:00", duration_min,
            autoplay_on=await is_autoplay(chat_id)
        )
        _title_short = title_t[:35] + ("..." if len(title_t) > 35 else "")
        caption = (
            f"<blockquote>"
            f"┌────── ˹ {_E['fire']} ꜰᴏʀᴄᴇ ᴩʟᴀʏɪɴɢ ˼ ─── ⏤‌●\n"
            f"┆{_E['star']} <b><a href='https://www.youtube.com/watch?v={vidid}'>{_title_short}</a></b>\n"
            f"┆\n"
            f"┆{_E['clock']} <b>ᴅᴜʀᴀᴛɪᴏɴ :</b>  {duration_min}\n"
            f"┆{_E['mic']} <b>ꜰᴏʀᴄᴇᴅ ʙʏ :</b>  {user_name}\n"
            f"└──────────────────●"
            f"</blockquote>"
        )
        try:
            from KHUSHI.utils.raw_send import send_msg_invert_preview
            from KHUSHI.core.call import THUMB_OFF_VIDEO_URL
            invert_text = f'<a href="{THUMB_OFF_VIDEO_URL}">\u200c</a>{caption}'
            run = await send_msg_invert_preview(app, chat_id, invert_text, InlineKeyboardMarkup(button))
            if not run:
                raise Exception("invert failed")
        except Exception:
            run = await app.send_message(
                chat_id,
                text=caption,
                reply_markup=InlineKeyboardMarkup(button),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )

        if db.get(chat_id):
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "stream"

        try:
            await JARVIS.skip_stream(chat_id, file_path)
        except Exception as e:
            _log.warning(f"[playforce] skip_stream failed for {chat_id}: {e}")

        _start_progress_timer(chat_id)

    else:
        db[chat_id] = []
        try:
            await JARVIS.join_call(chat_id, chat_id, file_path, video=False, image=thumbnail)
        except AssistantErr as ae:
            db.pop(chat_id, None)
            return await app.send_message(chat_id, str(ae))
        except Exception as je:
            db.pop(chat_id, None)
            return await app.send_message(
                chat_id,
                _err(f"ᴠᴄ ᴊᴏɪɴ ꜰᴀɪʟᴇᴅ: <code>{type(je).__name__}</code>"),
                parse_mode=ParseMode.HTML,
            )

        await put_queue(
            chat_id, chat_id, stored_file, title_t, duration_min,
            user_name, vidid, user_id, "audio",
        )

        button = stream_markup_timer(
            _, chat_id, "0:00", duration_min,
            autoplay_on=await is_autoplay(chat_id)
        )
        _title_short = title_t[:35] + ("..." if len(title_t) > 35 else "")
        caption = (
            f"<blockquote>"
            f"┌────── ˹ {_E['fire']} ꜰᴏʀᴄᴇ ᴩʟᴀʏɪɴɢ ˼ ─── ⏤‌●\n"
            f"┆{_E['star']} <b><a href='https://www.youtube.com/watch?v={vidid}'>{_title_short}</a></b>\n"
            f"┆\n"
            f"┆{_E['clock']} <b>ᴅᴜʀᴀᴛɪᴏɴ :</b>  {duration_min}\n"
            f"┆{_E['mic']} <b>ꜰᴏʀᴄᴇᴅ ʙʏ :</b>  {user_name}\n"
            f"└──────────────────●"
            f"</blockquote>"
        )
        try:
            from KHUSHI.utils.raw_send import send_msg_invert_preview
            from KHUSHI.core.call import THUMB_OFF_VIDEO_URL
            invert_text = f'<a href="{THUMB_OFF_VIDEO_URL}">\u200c</a>{caption}'
            run = await send_msg_invert_preview(app, chat_id, invert_text, InlineKeyboardMarkup(button))
            if not run:
                raise Exception("invert failed")
        except Exception:
            run = await app.send_message(
                chat_id,
                text=caption,
                reply_markup=InlineKeyboardMarkup(button),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )

        if db.get(chat_id):
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "stream"

        _start_progress_timer(chat_id)
