"""KHUSHI — DM Song Downloader: /song, /dl"""

import asyncio
import os
import re
import time
from typing import Optional

import yt_dlp
from pyrogram import filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from youtubesearchpython.__future__ import VideosSearch

from KHUSHI import app
from KHUSHI.core.dir import DOWNLOAD_DIR
from KHUSHI.utils.ytdl_smart import get_base_ytdlp_opts, smart_download
from config import BANNED_USERS

_SONG_DL_DIR = os.path.join(DOWNLOAD_DIR, "song_dl")
os.makedirs(_SONG_DL_DIR, exist_ok=True)

_pending: dict = {}

from KHUSHI.utils.ui import BRAND as _BRAND_LOGO, E as _E_UI

_BRAND = ""
_EM = {
    "audio": _E_UI["music"],
    "video": _E_UI["video"],
    "wait":  _E_UI["hourglass"],
    "ok":    _E_UI["check"],
    "err":   _E_UI["cross"],
    "dot":   _E_UI["dot"],
}

_QUALITY_LABELS = {
    "a128":   f"{_EM['audio']} ᴀᴜᴅɪᴏ  128ᴋ",
    "a_best": f"{_EM['audio']} ᴀᴜᴅɪᴏ ʙᴇsᴛ",
    "v360":   f"{_EM['video']} ᴠɪᴅᴇᴏ 360ᴘ",
    "v720":   f"{_EM['video']} ᴠɪᴅᴇᴏ 720ᴘ",
}

_QUALITY_FMT = {
    "a128":   "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
    "a_best": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
    "v360":   "bestvideo[height<=360]+bestaudio/best[height<=360]/bestvideo+bestaudio/best",
    "v720":   "bestvideo[height<=720]+bestaudio/best[height<=720]/bestvideo+bestaudio/best",
}

_IS_AUDIO = {"a128", "a_best"}
_IS_VIDEO = {"v360", "v720"}


def _extract_vid_id(text: str) -> Optional[str]:
    m = re.search(r"(?:v=|youtu\.be/|/embed/)([\w-]{11})", text)
    return m.group(1) if m else None


def _quality_markup(key: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 Audio 128k",  callback_data=f"sdl_{key}_a128"),
            InlineKeyboardButton("🎵 Audio Best",  callback_data=f"sdl_{key}_a_best"),
        ],
        [
            InlineKeyboardButton("📹 Video 360p",  callback_data=f"sdl_{key}_v360"),
            InlineKeyboardButton("📹 Video 720p",  callback_data=f"sdl_{key}_v720"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"sdl_{key}_cancel")],
    ])


async def _search_yt(query: str) -> Optional[dict]:
    try:
        res = VideosSearch(query, limit=1)
        data = await res.next()
        items = (data or {}).get("result") or []
        if not items:
            return None
        item = items[0]
        return {
            "vid_id":    _extract_vid_id(item.get("link") or ""),
            "title":     item.get("title") or "Unknown",
            "duration":  item.get("duration") or "?",
            "channel":   (item.get("channel") or {}).get("name") or "Unknown",
            "url":       item.get("link") or "",
            "thumbnail": ((item.get("thumbnails") or [{}])[0].get("url") or "").split("?")[0],
        }
    except Exception:
        return None


def _dl_yt(vid_id: str, quality: str) -> Optional[str]:
    # ── Audio: use smart_download (client rotation + Invidious fallback) ───────
    if quality in _IS_AUDIO:
        return smart_download(vid_id, _SONG_DL_DIR, fmt=_QUALITY_FMT[quality])

    # ── Video: yt-dlp with permissive format fallbacks ─────────────────────────
    fmt = _QUALITY_FMT[quality]
    ts = int(time.time())
    out_tmpl = os.path.join(_SONG_DL_DIR, f"{vid_id}_{quality}_{ts}.%(ext)s")
    opts = get_base_ytdlp_opts(_SONG_DL_DIR)
    opts.update({
        "format":              fmt,
        "outtmpl":             out_tmpl,
        "quiet":               True,
        "no_warnings":         True,
        "retries":             5,
        "prefer_ffmpeg":       True,
        "merge_output_format": "mp4",
    })
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid_id}", download=True)
            if info is None:
                return None
            prepared = ydl.prepare_filename(info)
            base = os.path.splitext(prepared)[0]
            for ext in ("mp4", "webm", "mkv", "m4a", "opus", "mp3"):
                path = f"{base}.{ext}"
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    return path
            if os.path.exists(prepared) and os.path.getsize(prepared) > 0:
                return prepared
    except Exception:
        pass
    return None


@app.on_message(
    filters.command(["song", "dl", "download"], prefixes=["/", "."]) & filters.private & ~BANNED_USERS
)
async def song_cmd(client, message: Message):
    try:
        await message.delete()
    except Exception:
        pass

    query = " ".join(message.command[1:]).strip() if len(message.command) > 1 else ""
    if not query:
        return await message.reply_text(
            f"<blockquote>{_EM['dot']} ᴜsᴀɢᴇ: <code>/song &lt;song name or YouTube URL&gt;</code>\n"
            f"{_EM['dot']} ᴇxᴀᴍᴘʟᴇ: <code>/song arijit singh tum hi ho</code></blockquote>",
            disable_web_page_preview=True,
        )

    searching = await message.reply_text(
        f"<blockquote>{_EM['wait']} sᴇᴀʀᴄʜɪɴɢ...</blockquote>"
    )

    vid_id = _extract_vid_id(query)
    info: Optional[dict] = None

    if vid_id:
        info = {
            "vid_id":   vid_id,
            "title":    query,
            "duration": "?",
            "channel":  "YouTube",
            "url":      f"https://youtu.be/{vid_id}",
            "thumbnail": "",
        }
        try:
            loop = asyncio.get_running_loop()
            opts = get_base_ytdlp_opts(_SONG_DL_DIR)
            opts.update({"skip_download": True, "quiet": True})
            def _fetch_info():
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(info["url"], download=False)
            meta = await asyncio.wait_for(loop.run_in_executor(None, _fetch_info), timeout=12)
            if meta:
                info["title"]     = meta.get("title") or info["title"]
                info["duration"]  = str(int((meta.get("duration") or 0) // 60)) + ":" + \
                                    str(int((meta.get("duration") or 0) % 60)).zfill(2)
                info["channel"]   = meta.get("uploader") or info["channel"]
                info["thumbnail"] = meta.get("thumbnail") or info["thumbnail"]
        except Exception:
            pass
    else:
        info = await _search_yt(query)

    if not info or not info.get("vid_id"):
        return await searching.edit_text(
            f"<blockquote>{_EM['err']} ɴᴏ ʀᴇsᴜʟᴛs ꜰᴏᴜɴᴅ ꜰᴏʀ: <b>{query}</b></blockquote>"
        )

    key = searching.id
    _pending[key] = info

    caption = (
        f"<blockquote>"
        f"{_EM['audio']} <b>{info['title']}</b>\n"
        f"{_EM['dot']} ᴄʜᴀɴɴᴇʟ: {info['channel']}\n"
        f"{_EM['dot']} ᴅᴜʀᴀᴛɪᴏɴ: {info['duration']}\n\n"
        f"ᴄʜᴏᴏsᴇ ǫᴜᴀʟɪᴛʏ ↓"
        f"</blockquote>"
    )

    try:
        if info.get("thumbnail"):
            await searching.delete()
            picker = await message.reply_photo(
                photo=info["thumbnail"],
                caption=caption,
                reply_markup=_quality_markup(key),
                has_spoiler=True,
            )
            _pending[key]["picker_id"] = picker.id
        else:
            await searching.edit_text(caption, reply_markup=_quality_markup(key))
    except Exception:
        await searching.edit_text(caption, reply_markup=_quality_markup(key))


@app.on_callback_query(
    filters.regex(r"^sdl_(-?\d+)_(a128|a_best|v360|v720|cancel)$") & ~BANNED_USERS
)
async def song_dl_cb(client, cb: CallbackQuery):
    m = re.match(r"^sdl_(-?\d+)_(a128|a_best|v360|v720|cancel)$", cb.data)
    if not m:
        return await cb.answer()

    key = int(m.group(1))
    quality = m.group(2)
    info = _pending.get(key)

    if quality == "cancel":
        _pending.pop(key, None)
        try:
            await cb.message.delete()
        except Exception:
            await cb.answer("ᴄᴀɴᴄᴇʟʟᴇᴅ ✓")
        return

    if not info:
        return await cb.answer("⚠️ Session expired. Send /song again.", show_alert=True)

    await cb.answer(f"⬇️ Downloading {_QUALITY_LABELS.get(quality, quality)} …")

    vid_id = info["vid_id"]
    title = info["title"]

    try:
        await cb.message.edit_caption(
            f"<blockquote>{_EM['wait']} ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ {_QUALITY_LABELS.get(quality,'')}\n"
            f"{_EM['dot']} <b>{title}</b>\nᴘʟᴇᴀsᴇ ᴡᴀɪᴛ...</blockquote>"
        )
    except Exception:
        try:
            await cb.message.edit_text(
                f"<blockquote>{_EM['wait']} ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ...</blockquote>"
            )
        except Exception:
            pass

    loop = asyncio.get_running_loop()
    try:
        file_path = await asyncio.wait_for(
            loop.run_in_executor(None, _dl_yt, vid_id, quality),
            timeout=180,
        )
    except Exception:
        file_path = None

    if not file_path or not os.path.exists(file_path):
        try:
            await cb.message.edit_text(
                f"<blockquote>{_EM['err']} ᴅᴏᴡɴʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ. ᴛʀʏ ᴀɴᴏᴛʜᴇʀ ǫᴜᴀʟɪᴛʏ ᴏʀ <code>/song</code> ᴀɢᴀɪɴ.</blockquote>"
            )
        except Exception:
            pass
        return

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 48:
        try:
            await cb.message.edit_text(
                f"<blockquote>{_EM['err']} ꜰɪʟᴇ ᴛᴏᴏ ʟᴀʀɢᴇ ({file_size_mb:.1f} ᴍʙ). ᴛʀʏ ᴀ ʟᴏᴡᴇʀ ǫᴜᴀʟɪᴛʏ.</blockquote>"
            )
        except Exception:
            pass
        os.remove(file_path)
        return

    caption_send = (
        f"<blockquote>"
        f"{_EM['ok']} <b>{title}</b>\n"
        f"{_EM['dot']} ǫᴜᴀʟɪᴛʏ: {_QUALITY_LABELS.get(quality,'')}\n"
        f"{_EM['dot']} sɪᴢᴇ: {file_size_mb:.1f} ᴍʙ"
        f"</blockquote>"
    )

    try:
        if quality in _IS_VIDEO:
            await cb.message.reply_video(
                video=file_path,
                caption=caption_send,
                supports_streaming=True,
                has_spoiler=True,
            )
        else:
            await cb.message.reply_audio(
                audio=file_path,
                caption=caption_send,
                title=title,
                performer="KHUSHI Bot",
            )
        try:
            await cb.message.delete()
        except Exception:
            pass
        _pending.pop(key, None)
    except Exception as e:
        try:
            await cb.message.edit_text(
                f"<blockquote>{_EM['err']} sᴇɴᴅ ꜰᴀɪʟᴇᴅ: {type(e).__name__}</blockquote>"
            )
        except Exception:
            pass
    finally:
        try:
            os.remove(file_path)
        except Exception:
            pass
