import asyncio
import os
from datetime import datetime, timedelta
from typing import Union

from ntgcalls import TelegramServerError, ConnectionError as NTgConnectionError
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, ChatAdminRequired, ChannelInvalid, ChannelPrivate
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.exceptions import NoActiveGroupCall
from pytgcalls.types import AudioQuality, ChatUpdate, MediaStream, StreamEnded, Update, VideoQuality

import config
from strings import get_string
from ANNIEMUSIC import LOGGER, YouTube, app
from ANNIEMUSIC.misc import db
from ANNIEMUSIC.utils.cookie_handler import COOKIE_PATH
from ANNIEMUSIC.utils.database import (
    add_active_chat,
    add_active_video_chat,
    get_lang,
    get_loop,
    group_assistant,
    is_autoend,
    is_autoplay,
    is_thumb_enabled,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
    set_loop,
)
from ANNIEMUSIC.utils.exceptions import AssistantErr
from ANNIEMUSIC.utils.formatters import check_duration, seconds_to_min, speed_converter
from ANNIEMUSIC.utils.inline import stream_markup, stream_markup_timer, add_to_channel_markup, InlineKeyboardButton as StyledBtn
from ANNIEMUSIC.utils.stream.autoclear import auto_clean
from ANNIEMUSIC.utils.thumbnails import get_thumb
from ANNIEMUSIC.utils.errors import capture_internal_err, send_large_error

THUMB_OFF_VIDEO_URL = "https://files.catbox.moe/4vr2jc.mp4"

autoend = {}
counter = {}
autoplay_history: dict[int, list] = {}  # per-chat played video IDs history

_CDN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.youtube.com/",
    "Origin": "https://www.youtube.com",
}


def _needs_ytdlp(path: str) -> bool:
    """Check if the path needs yt-dlp processing (YouTube URLs only)."""
    if not path:
        return False
    if os.path.exists(path):
        return False  # local file → FFmpeg handles directly
    return "youtube.com" in path or "youtu.be" in path


def _is_cdn_url(path: str) -> bool:
    """Check if the path is a direct CDN/remote URL (not local, not YouTube)."""
    if not path or os.path.exists(path):
        return False
    return path.startswith("http") and not _needs_ytdlp(path)


def dynamic_media_stream(path: str, video: bool = False, ffmpeg_params: str = None) -> MediaStream:
    ytdlp_args = None
    headers = None

    if _needs_ytdlp(path):
        ytdlp_args = "--js-runtimes node"
        if COOKIE_PATH.exists():
            ytdlp_args += f" --cookies {COOKIE_PATH}"
    elif _is_cdn_url(path):
        headers = _CDN_HEADERS

    if video:
        return MediaStream(
            media_path=path,
            audio_parameters=AudioQuality.MEDIUM,
            video_parameters=VideoQuality.HD_720p,
            audio_flags=MediaStream.Flags.AUTO_DETECT,
            video_flags=MediaStream.Flags.AUTO_DETECT,
            headers=headers,
            ffmpeg_parameters=ffmpeg_params or None,
            ytdlp_parameters=ytdlp_args,
        )
    else:
        return MediaStream(
            media_path=path,
            audio_parameters=AudioQuality.STUDIO,
            audio_flags=MediaStream.Flags.AUTO_DETECT,
            video_flags=MediaStream.Flags.IGNORE,
            headers=headers,
            ffmpeg_parameters=ffmpeg_params or None,
            ytdlp_parameters=ytdlp_args,
        )

async def _clear_(chat_id: int) -> None:
    popped = db.pop(chat_id, None)
    if popped:
        await auto_clean(popped)
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)
    await set_loop(chat_id, 0)

class Call:
    def __init__(self):
        self.one = None
        self.two = None
        self.three = None
        self.four = None
        self.five = None
        self.active_calls: set[int] = set()

    def setup_clients(self, userbot) -> None:
        """Initialize PyTgCalls using the shared Userbot Pyrogram clients.
        This avoids AUTH_KEY_DUPLICATED by reusing a single connection per session."""
        self.one = PyTgCalls(userbot.one) if userbot.one else None
        self.two = PyTgCalls(userbot.two) if userbot.two else None
        self.three = PyTgCalls(userbot.three) if userbot.three else None
        self.four = PyTgCalls(userbot.four) if userbot.four else None
        self.five = PyTgCalls(userbot.five) if userbot.five else None


    @capture_internal_err
    async def pause_stream(self, chat_id: int) -> None:
        assistant = await group_assistant(self, chat_id)
        await assistant.pause(chat_id)

    @capture_internal_err
    async def resume_stream(self, chat_id: int) -> None:
        assistant = await group_assistant(self, chat_id)
        await assistant.resume(chat_id)

    @capture_internal_err
    async def mute_stream(self, chat_id: int) -> None:
        assistant = await group_assistant(self, chat_id)
        await assistant.mute(chat_id)

    @capture_internal_err
    async def unmute_stream(self, chat_id: int) -> None:
        assistant = await group_assistant(self, chat_id)
        await assistant.unmute(chat_id)

    @capture_internal_err
    async def stop_stream(self, chat_id: int) -> None:
        assistant = await group_assistant(self, chat_id)
        await _clear_(chat_id)
        if chat_id not in self.active_calls:
            return
        try:
            await assistant.leave_call(chat_id)
        except Exception:
            pass
        finally:
            self.active_calls.discard(chat_id)

    @capture_internal_err
    async def stop_or_autoplay(self, chat_id: int, last_song: dict) -> None:
        """Called after skip when queue is empty.
        If autoplay is ON → trigger autoplay using last played song as context.
        If autoplay is OFF → stop stream and leave VC normally.
        """
        from ANNIEMUSIC.utils.database import is_autoplay
        if last_song and await is_autoplay(chat_id):
            # Re-insert the last song so play() can pop it and use it for autoplay search
            if not db.get(chat_id):
                db[chat_id] = [last_song]
            assistant = await group_assistant(self, chat_id)
            await self.play(assistant, chat_id)
        else:
            await self.stop_stream(chat_id)

    @capture_internal_err
    async def force_stop_stream(self, chat_id: int) -> None:
        assistant = await group_assistant(self, chat_id)
        try:
            check = db.get(chat_id)
            if check:
                check.pop(0)
        except (IndexError, KeyError):
            pass
        await remove_active_video_chat(chat_id)
        await remove_active_chat(chat_id)
        # Don't fully leave the call - just pause and clear queue for forceplay to work
        # This allows seamless track switching without admin requirement issues
        if chat_id in self.active_calls:
            try:
                await assistant.pause(chat_id)
            except Exception:
                pass
        db[chat_id] = []


    @capture_internal_err
    async def skip_stream(self, chat_id: int, link: str, video: Union[bool, str] = None, image: Union[bool, str] = None) -> None:
        assistant = await group_assistant(self, chat_id)
        stream = dynamic_media_stream(path=link, video=bool(video))
        await assistant.play(chat_id, stream)

    @capture_internal_err
    async def vc_users(self, chat_id: int) -> list:
        assistant = await group_assistant(self, chat_id)
        participants = await assistant.get_participants(chat_id)
        return [p.user_id for p in participants if not p.is_muted]

    @capture_internal_err
    async def seek_stream(self, chat_id: int, file_path: str, to_seek: str, duration: str, mode: str) -> None:
        assistant = await group_assistant(self, chat_id)
        ffmpeg_params = f"-ss {to_seek} -to {duration}"
        is_video = mode == "video"
        stream = dynamic_media_stream(path=file_path, video=is_video, ffmpeg_params=ffmpeg_params)
        await assistant.play(chat_id, stream)

    @capture_internal_err
    async def speedup_stream(self, chat_id: int, file_path: str, speed: float, playing: list) -> None:
        if not isinstance(playing, list) or not playing or not isinstance(playing[0], dict):
            raise AssistantErr("Invalid stream info for speedup.")

        assistant = await group_assistant(self, chat_id)
        base = os.path.basename(file_path)
        chatdir = os.path.join("playback", str(speed))
        os.makedirs(chatdir, exist_ok=True)
        out = os.path.join(chatdir, base)

        if not os.path.exists(out):
            vs = str(2.0 / float(speed))
            cmd = f"ffmpeg -i {file_path} -filter:v setpts={vs}*PTS -filter:a atempo={speed} {out}"
            proc = await asyncio.create_subprocess_shell(cmd, stdin=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc.communicate()

        dur = int(await asyncio.get_event_loop().run_in_executor(None, check_duration, out))
        played, con_seconds = speed_converter(playing[0]["played"], speed)
        duration_min = seconds_to_min(dur)
        is_video = playing[0]["streamtype"] == "video"
        ffmpeg_params = f"-ss {played} -to {duration_min}"
        stream = dynamic_media_stream(path=out, video=is_video, ffmpeg_params=ffmpeg_params)

        if chat_id in db and db[chat_id] and db[chat_id][0].get("file") == file_path:
            await assistant.play(chat_id, stream)
        else:
            raise AssistantErr("Stream mismatch during speedup.")

        db[chat_id][0].update({
            "played": con_seconds,
            "dur": duration_min,
            "seconds": dur,
            "speed_path": out,
            "speed": speed,
            "old_dur": db[chat_id][0].get("dur"),
            "old_second": db[chat_id][0].get("seconds"),
        })


    @capture_internal_err
    async def stream_call(self, link: str) -> None:
        assistant = await group_assistant(self, config.LOGGER_ID)
        try:
            await assistant.play(config.LOGGER_ID, MediaStream(link))
            await asyncio.sleep(8)
        except TelegramServerError:
            pass
        except Exception:
            pass
        finally:
            try:
                await assistant.leave_call(config.LOGGER_ID)
            except:
                pass

    @capture_internal_err
    async def join_call(
        self,
        chat_id: int,
        original_chat_id: int,
        link: str,
        video: Union[bool, str] = None,
        image: Union[bool, str] = None,
    ) -> None:
        assistant = await group_assistant(self, chat_id)
        lang = await get_lang(chat_id)
        _ = get_string(lang)

        # Log what we're streaming for debugging
        is_url = link.startswith("http")
        if is_url:
            LOGGER(__name__).info(
                f"[PLAY] chat={chat_id} | CDN URL stream | video={bool(video)}"
            )
        else:
            size = os.path.getsize(link) if os.path.exists(link) else -1
            LOGGER(__name__).info(
                f"[PLAY] chat={chat_id} | file={link} | size={size}B | video={bool(video)}"
            )

        # Auto-convert cached webm to m4a before playing (better VC compatibility)
        if os.path.exists(link) and link.endswith(".webm"):
            from ANNIEMUSIC.utils.downloader import _convert_webm_to_m4a, extract_video_id
            vid = extract_video_id(link)
            LOGGER(__name__).info(f"[PLAY] Converting cached webm→m4a for better VC compat | {vid}")
            converted = await _convert_webm_to_m4a(link, vid)
            if converted:
                link = converted
                LOGGER(__name__).info(f"[PLAY] Using converted file: {link}")
            stream = dynamic_media_stream(path=link, video=bool(video))
        else:
            stream = dynamic_media_stream(path=link, video=bool(video))

        # ── Pre-warm: resolve peer on the assistant's internal Pyrogram client ──
        # After bot restart, the PyTgCalls client hasn't cached this chat's peer.
        # Resolving it now prevents PeerIdInvalid on the first play attempt.
        try:
            _pyrogram_client = getattr(assistant, '_app', None) or getattr(assistant, 'mtproto_client', None)
            if _pyrogram_client:
                await _pyrogram_client.resolve_peer(chat_id)
                LOGGER(__name__).info(f"[PLAY] Peer pre-warmed for chat={chat_id}")
        except Exception as _pw_err:
            LOGGER(__name__).debug(f"[PLAY] Peer pre-warm skipped: {_pw_err}")

        for attempt in range(3):
            try:
                await assistant.play(chat_id, stream)
                break
            except NoActiveGroupCall:
                # No VC open — try creating one via bot account, same as ChatAdminRequired path
                LOGGER(__name__).warning(
                    f"[PLAY] NoActiveGroupCall — trying to create VC via bot for chat={chat_id}"
                )
                if chat_id in self.active_calls:
                    break
                try:
                    import random as _random
                    from pyrogram.raw import functions as _rf
                    _peer = await app.resolve_peer(chat_id)
                    await app.invoke(
                        _rf.phone.CreateGroupCall(
                            peer=_peer,
                            random_id=_random.randint(10000, 9999999),
                        )
                    )
                    await asyncio.sleep(2)
                    LOGGER(__name__).info(f"[PLAY] VC created. Retrying play for chat={chat_id}")
                    await assistant.play(chat_id, stream)
                    break
                except Exception as nag_err:
                    LOGGER(__name__).error(f"[PLAY] VC create after NoActiveGroupCall failed: {nag_err}")
                    raise AssistantErr(_["call_8"])
            except ChatAdminRequired:
                if chat_id in self.active_calls:
                    break
                # Assistant lacks "Manage Voice Chats" admin — try creating VC via bot account first
                LOGGER(__name__).warning(
                    f"[PLAY] ChatAdminRequired — trying to create VC via bot for chat={chat_id}"
                )
                try:
                    import random as _random
                    from pyrogram.raw import functions as _rf
                    _peer = await app.resolve_peer(chat_id)
                    await app.invoke(
                        _rf.phone.CreateGroupCall(
                            peer=_peer,
                            random_id=_random.randint(10000, 9999999),
                        )
                    )
                    await asyncio.sleep(2)
                    LOGGER(__name__).info(f"[PLAY] VC created via bot. Retrying assistant.play for chat={chat_id}")
                    await assistant.play(chat_id, stream)
                    break
                except Exception as cge:
                    LOGGER(__name__).error(f"[PLAY] Bot-create VC also failed for chat={chat_id}: {cge}")
                    raise AssistantErr(
                        "<b>ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ</b>\n\n"
                        "<blockquote>ᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ᴀ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ɪɴ ᴛʜᴇ ɢʀᴏᴜᴘ ꜰɪʀsᴛ, ᴏʀ ɢɪᴠᴇ ᴛʜᴇ ᴀssɪsᴛᴀɴᴛ ᴀᴄᴄᴏᴜɴᴛ <b>Mᴀɴᴀɢᴇ Vᴏɪᴄᴇ Cʜᴀᴛs</b> ᴀᴅᴍɪɴ ᴘᴇʀᴍɪssɪᴏɴ.</blockquote>"
                    )
            except TelegramServerError as tse:
                LOGGER(__name__).warning(
                    f"[PLAY] TelegramServerError attempt {attempt+1}/3 | "
                    f"chat={chat_id} | link={link[:80]} | err={tse}"
                )
                if attempt < 2:
                    # On first retry: if cached webm file exists, delete it so next play re-downloads in m4a
                    if attempt == 0 and os.path.exists(link) and link.endswith(".webm"):
                        LOGGER(__name__).warning(f"[PLAY] Deleting bad webm cache: {link}")
                        try:
                            os.remove(link)
                        except Exception:
                            pass
                    # Leave call cleanly + clear stale peer/connection cache
                    try:
                        await assistant.leave_call(chat_id)
                    except Exception:
                        pass
                    # Clear stale peer cache so next attempt gets a fresh peer lookup
                    try:
                        assistant._cache_user_peer.pop(chat_id, None)
                        assistant._wait_connect.pop(chat_id, None)
                    except Exception:
                        pass
                    wait_sec = 5 if attempt == 0 else 10
                    LOGGER(__name__).info(f"[PLAY] Waiting {wait_sec}s before retry {attempt+2}/3")
                    await asyncio.sleep(wait_sec)
                    continue
                # All retries failed — try VC reset as last resort
                LOGGER(__name__).warning(f"[PLAY] All retries failed. Attempting VC reset for chat={chat_id}")
                try:
                    await assistant.leave_call(chat_id, close=True)
                    await asyncio.sleep(3)
                    # Recreate voice chat via raw API
                    import random as _random
                    from pyrogram.raw import functions as _rf, types as _rt
                    _peer = await app.resolve_peer(chat_id)
                    await app.invoke(
                        _rf.phone.CreateGroupCall(
                            peer=_peer,
                            random_id=_random.randint(10000, 9999999),
                        )
                    )
                    await asyncio.sleep(3)
                    LOGGER(__name__).info(f"[PLAY] VC reset done. Final play attempt for chat={chat_id}")
                    await assistant.play(chat_id, stream)
                    self.active_calls.add(chat_id)
                    await add_active_chat(chat_id)
                    await music_on(chat_id)
                    if video:
                        await add_active_video_chat(chat_id)
                    return
                except Exception as reset_err:
                    LOGGER(__name__).error(f"[PLAY] VC reset failed for chat={chat_id}: {reset_err}")
                raise AssistantErr(_["call_10"])
            except NTgConnectionError:
                LOGGER(__name__).warning(
                    f"[PLAY] NTgConnectionError | chat={chat_id} — leaving and retrying"
                )
                try:
                    await assistant.leave_call(chat_id)
                    await asyncio.sleep(2)
                    await assistant.play(chat_id, stream)
                    break
                except Exception as e:
                    LOGGER(__name__).error(f"[PLAY] NTgConnectionError retry failed: {e}")
                    pass
            except FloodWait as fw:
                wait_sec = fw.value + 3
                if attempt < 2:
                    await asyncio.sleep(wait_sec)
                    continue
                raise AssistantErr(
                    f"<emoji id='5040042498634810056'>❌</emoji> <b>ᴛᴇʟᴇɢʀᴀᴍ ғʟᴏᴏᴅ ᴡᴀɪᴛ</b>\n\n"
                    f"<blockquote>"
                    f"<emoji id='5123230779593196220'>⏰</emoji> ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ <b>{wait_sec}s</b> ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ."
                    f"</blockquote>"
                )
            except ChannelInvalid:
                raise AssistantErr(
                    "<b>ᴀssɪsᴛᴀɴᴛ ᴄᴀɴɴᴏᴛ ᴊᴏɪɴ ᴛʜɪs ɢʀᴏᴜᴘ.</b>\n\n"
                    "<blockquote>ᴘʟᴇᴀsᴇ ᴀᴅᴅ ᴛʜᴇ ᴀssɪsᴛᴀɴᴛ ᴀᴄᴄᴏᴜɴᴛ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ.</blockquote>"
                )
            except ChannelPrivate:
                raise AssistantErr(
                    "<b>ᴀssɪsᴛᴀɴᴛ ɪs ɴᴏᴛ ᴀ ᴍᴇᴍʙᴇʀ ᴏꜰ ᴛʜɪs ɢʀᴏᴜᴘ.</b>\n\n"
                    "<blockquote>"
                    "ᴘʟᴇᴀsᴇ <b>ᴀᴅᴅ</b> ᴛʜᴇ ᴀssɪsᴛᴀɴᴛ ᴀᴄᴄᴏᴜɴᴛ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ.\n"
                    "ɪꜰ ᴀssɪsᴛᴀɴᴛ ɪs ᴀʟʀᴇᴀᴅʏ ɪɴ ɢʀᴏᴜᴘ, ʀᴇᴍᴏᴠᴇ ᴀɴᴅ ʀᴇ-ᴀᴅᴅ ɪᴛ."
                    "</blockquote>"
                )
            except Exception as e:
                LOGGER(__name__).warning(
                    f"[PLAY] Unexpected error attempt {attempt+1}/3 | chat={chat_id} | {type(e).__name__}: {e}"
                )
                if attempt < 2:
                    # Retry unknown errors — often peer-resolution or transient Telegram issues
                    try:
                        await assistant.leave_call(chat_id)
                    except Exception:
                        pass
                    wait_sec = 3 if attempt == 0 else 5
                    LOGGER(__name__).info(f"[PLAY] Retrying in {wait_sec}s for chat={chat_id}")
                    await asyncio.sleep(wait_sec)
                    continue
                raise AssistantErr(
                    f"ᴜɴᴀʙʟᴇ ᴛᴏ ᴊᴏɪɴ ᴛʜᴇ ɢʀᴏᴜᴘ ᴄᴀʟʟ.\nRᴇᴀsᴏɴ: {e}"
                )
        self.active_calls.add(chat_id)
        await add_active_chat(chat_id)
        await music_on(chat_id)
        if video:
            await add_active_video_chat(chat_id)

        if await is_autoend():
            counter[chat_id] = {}
            users = len(await assistant.get_participants(chat_id))
            if users == 1:
                autoend[chat_id] = datetime.now() + timedelta(minutes=1)


    @capture_internal_err
    async def play(self, client, chat_id: int) -> None:
        check = db.get(chat_id)
        popped = None
        loop = await get_loop(chat_id)
        try:
            if loop == 0:
                popped = check.pop(0)
            else:
                loop = loop - 1
                await set_loop(chat_id, loop)
            await auto_clean(popped)
            if not check:
                # ── Autoplay: find & play a related song ───────────────────────
                if popped and await is_autoplay(chat_id):
                    try:
                        import random as _random
                        last_title = popped.get("title", "")
                        last_vidid = popped.get("vidid", "")
                        original_chat_id = popped.get("chat_id", chat_id)
                        from youtubesearchpython.__future__ import VideosSearch
                        import config as _cfg
                        from ANNIEMUSIC.utils.formatters import time_to_seconds as _tts

                        # Build / update per-chat history (keep last 25 songs)
                        _hist = autoplay_history.setdefault(chat_id, [])
                        if last_vidid and last_vidid not in _hist:
                            _hist.append(last_vidid)
                        if len(_hist) > 25:
                            _hist.pop(0)

                        # Keywords that identify compilations/jukeboxes — skip them
                        _ap_skip_kw = {
                            "jukebox", "playlist", "non stop", "nonstop",
                            "mashup", "part 1", "part 2", "part-1", "part-2",
                            "vol.", "vol ", "top 10", "top 20", "top 50",
                            "best of", "hits of", "collection", "compilation",
                            "audio jukebox", "video jukebox", "full album",
                            "all songs", "back to back", "evergreen",
                            "jhankar", "ringtone",
                        }

                        def _is_single_song(title: str, dur_secs: int) -> bool:
                            tl = title.lower()
                            for kw in _ap_skip_kw:
                                if kw in tl:
                                    return False
                            return 60 <= dur_secs <= 600  # 1–10 minutes

                        # Build individual-song focused queries
                        _suffixes = [
                            "new song", "latest song", "official video",
                            "new hindi song", "hit song", "official audio",
                            "song 2025", "new release", "latest hit",
                        ]
                        _words = [w for w in last_title.split() if len(w) > 3]
                        _base = _random.choice(_words) if _words else (
                            last_title.split()[0] if last_title else "hindi"
                        )
                        # Try up to 3 different queries to maximise variety
                        all_candidates: list = []
                        for _attempt in range(3):
                            _query = f"{_base} {_random.choice(_suffixes)}"
                            try:
                                _res = await VideosSearch(_query, limit=15).next()
                                all_candidates += (_res.get("result") or [])
                            except Exception:
                                pass

                        # Deduplicate by video id
                        seen_ids: set = set()
                        unique_candidates = []
                        for _item in all_candidates:
                            _vid = _item.get("id", "")
                            if _vid and _vid not in seen_ids:
                                seen_ids.add(_vid)
                                unique_candidates.append(_item)

                        _random.shuffle(unique_candidates)

                        # Prefer individual songs (≤10 min, no compilation keywords)
                        chosen = None
                        fallback = None
                        for item in unique_candidates:
                            vid = item.get("id", "")
                            dur_raw = item.get("duration") or ""
                            ititle  = item.get("title", "")
                            if not vid or vid in _hist or not dur_raw:
                                continue
                            try:
                                dur_s = _tts(dur_raw)
                            except Exception:
                                dur_s = 0
                            if dur_s > _cfg.DURATION_LIMIT:
                                continue
                            if _is_single_song(ititle, dur_s):
                                chosen = item
                                break
                            elif fallback is None:
                                fallback = item
                        if not chosen:
                            chosen = fallback

                        if chosen:
                            ap_vidid   = chosen.get("id")
                            ap_title   = chosen.get("title", "Unknown")
                            ap_dur     = chosen.get("duration") or "Unknown"
                            ap_title_short = ap_title[:35] + "..." if len(ap_title) > 35 else ap_title

                            # Use download pipeline instead of yt-dlp subprocess
                            # — more reliable, uses SmartYTDL + all fallbacks
                            from ANNIEMUSIC.utils.downloader import download_audio_concurrent
                            ap_file = await download_audio_concurrent(
                                f"https://www.youtube.com/watch?v={ap_vidid}"
                            )
                            if ap_file:
                                ap_stream = dynamic_media_stream(
                                    path=ap_file, video=False
                                )
                                ap_played = False
                                try:
                                    await client.play(chat_id, ap_stream)
                                    ap_played = True
                                except Exception as _play_err:
                                    LOGGER(__name__).warning(f"Autoplay client.play error: {_play_err}")

                                if not ap_played:
                                    return

                                try:
                                    ap_sec = _tts(ap_dur) - 3
                                except Exception:
                                    ap_sec = 0

                                db[chat_id] = [{
                                    "title":      ap_title,
                                    "dur":        ap_dur,
                                    "streamtype": "audio",
                                    "by":         "Annie AutoPlay",
                                    "user_id":    0,
                                    "chat_id":    original_chat_id,
                                    "file":       ap_file,
                                    "vidid":      ap_vidid,
                                    "seconds":    ap_sec,
                                    "played":     0,
                                }]
                                await add_active_chat(chat_id)

                                # Track chosen song in history to prevent repeat
                                if ap_vidid not in _hist:
                                    _hist.append(ap_vidid)
                                if len(_hist) > 25:
                                    _hist.pop(0)

                                language = await get_lang(chat_id)
                                _lang = get_string(language)
                                try:
                                    _BEAR = "<emoji id='5042192219960771668'>🧸</emoji>"
                                    _TIME = "<emoji id='4979027931234830344'>⏳</emoji>"
                                    _DOT  = "<emoji id='5972072533833289156'>🔹</emoji>"
                                    _AROW = (
                                        "<emoji id='5042192219960771668'>🧸</emoji>"
                                        "<emoji id='5210820276748566172'>🔤</emoji>"
                                        "<emoji id='5213301251722203632'>🔤</emoji>"
                                        "<emoji id='5213301251722203632'>🔤</emoji>"
                                        "<emoji id='5211032856154885824'>🔤</emoji>"
                                        "<emoji id='5213337333742454261'>🔤</emoji>"
                                    )
                                    btn = stream_markup_timer(
                                        _lang, chat_id,
                                        "0:00", ap_dur,
                                        autoplay_on=True,
                                    )
                                    _ap_caption = (
                                        f"<blockquote>"
                                        f"┌────── ˹ ᴀᴜᴛᴏᴘʟᴀʏ ˼─── ⏤‌‌●\n"
                                        f"┆{_BEAR} <b>ᴛɪᴛʟᴇ :</b> "
                                        f"<a href='https://www.youtube.com/watch?v={ap_vidid}'>"
                                        f"{ap_title_short}</a>\n"
                                        f"┆{_TIME} <b>ᴅᴜʀᴀᴛɪᴏɴ :</b> {ap_dur}\n"
                                        f"┆{_DOT} <b>ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ :</b> ᴀɴɴɪᴇ ᴀᴜᴛᴏᴘʟᴀʏ\n"
                                        f"└──────────────────────●"
                                        f"</blockquote>\n"
                                        f"<blockquote>{_AROW}</blockquote>"
                                    )
                                    _ap_markup = InlineKeyboardMarkup(btn)
                                    thumb_on = await is_thumb_enabled()
                                    if thumb_on:
                                        img = await get_thumb(ap_vidid)
                                        ap_msg = await app.send_photo(
                                            chat_id=original_chat_id,
                                            photo=img,
                                            caption=_ap_caption,
                                            reply_markup=_ap_markup,
                                            has_spoiler=True,
                                        )
                                    else:
                                        ap_msg = await app.send_message(
                                            chat_id=original_chat_id,
                                            text=f'<a href="{THUMB_OFF_VIDEO_URL}">\u200C</a>{_ap_caption}',
                                            reply_markup=_ap_markup,
                                            parse_mode=ParseMode.HTML,
                                            invert_media=True,
                                            disable_web_page_preview=False,
                                        )
                                    db[chat_id][0]["mystic"] = ap_msg
                                except Exception:
                                    pass
                                return
                            else:
                                LOGGER(__name__).warning(f"Autoplay: download failed for {ap_vidid}")
                                return
                    except Exception as ap_err:
                        LOGGER(__name__).warning(f"Autoplay error: {ap_err}")
                # ── Normal end: clear and leave ────────────────────────────────
                await _clear_(chat_id)
                if chat_id in self.active_calls:
                    try:
                        await client.leave_call(chat_id)
                    except NoActiveGroupCall:
                        pass
                    except Exception:
                        pass
                    finally:
                        self.active_calls.discard(chat_id)

                try:
                    language = await get_lang(chat_id)
                    _ = get_string(language)
                except:
                    _ = get_string("en")
                
                try:
                    await app.send_message(
                        chat_id,
                        text=(
                            "<emoji id='5463107823946717464'>🎵</emoji>"
                            " <b>ᴀɴɴɪᴇ ✘ ᴍᴜsɪᴄ</b> "
                            "<emoji id='5463107823946717464'>🎵</emoji>\n"
                            "<b>┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄</b>\n"
                            "<blockquote>"
                            "<emoji id='5039827436737397847'>✨</emoji>"
                            " <b>ᴀʟʟ sᴏɴɢs ғɪɴɪsʜᴇᴅ!</b>"
                            " <b>ʙᴏᴛ ʟᴇғᴛ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ.</b>\n\n"
                            "<emoji id='5042334757040423886'>⚡️</emoji>"
                            " <b>ᴘʟᴀʏ ᴀɢᴀɪɴ ᴀɴᴅ ᴇɴᴊᴏʏ sᴏɴɢs!</b>"
                            "</blockquote>"
                        ),
                        reply_markup=add_to_channel_markup(_, app.username),
                    )
                except:
                    pass
                return
        except:
            try:
                await _clear_(chat_id)
                return await client.leave_call(chat_id)
            except:
                return
        else:
            queued = check[0]["file"]
            language = await get_lang(chat_id)
            _ = get_string(language)
            title = (check[0]["title"]).title()
            user = check[0]["by"]
            original_chat_id = check[0]["chat_id"]
            streamtype = check[0]["streamtype"]
            videoid = check[0]["vidid"]
            db[chat_id][0]["played"] = 0

            exis = (check[0]).get("old_dur")
            if exis:
                db[chat_id][0]["dur"] = exis
                db[chat_id][0]["seconds"] = check[0]["old_second"]
                db[chat_id][0]["speed_path"] = None
                db[chat_id][0]["speed"] = 1.0

            video = True if str(streamtype) == "video" else False

            _thumb_on = await is_thumb_enabled()

            if "live_" in queued:
                n, link = await YouTube.video(videoid, True)
                if n == 0:
                    return await app.send_message(original_chat_id, text=_["call_6"])

                stream = dynamic_media_stream(path=link, video=video)
                try:
                    await client.play(chat_id, stream)
                except Exception:
                    return await app.send_message(original_chat_id, text=_["call_6"])

                button = stream_markup(_, chat_id, autoplay_on=await is_autoplay(chat_id))
                _cap = _["stream_1"].format(
                    f"https://t.me/{app.username}?start=info_{videoid}",
                    title[:23],
                    check[0]["dur"],
                    user,
                )
                if _thumb_on:
                    img = await get_thumb(videoid)
                    run = await app.send_photo(
                        chat_id=original_chat_id,
                        photo=img,
                        caption=_cap,
                        reply_markup=InlineKeyboardMarkup(button),
                        has_spoiler=True,
                    )
                else:
                    run = await app.send_message(
                        chat_id=original_chat_id,
                        text=f'<a href="{THUMB_OFF_VIDEO_URL}">\u200C</a>{_cap}',
                        reply_markup=InlineKeyboardMarkup(button),
                        parse_mode=ParseMode.HTML,
                        invert_media=True,
                        disable_web_page_preview=False,
                    )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"

            elif "vid_" in queued:
                mystic = await app.send_message(original_chat_id, _["call_7"])
                try:
                    file_path, direct = await YouTube.download(
                        videoid,
                        mystic,
                        videoid=True,
                        video=True if str(streamtype) == "video" else False,
                    )
                except:
                    return await mystic.edit_text(
                        _["call_6"], disable_web_page_preview=True
                    )

                stream = dynamic_media_stream(path=file_path, video=video)
                try:
                    await client.play(chat_id, stream)
                except:
                    return await app.send_message(original_chat_id, text=_["call_6"])

                button = stream_markup(_, chat_id, autoplay_on=await is_autoplay(chat_id))
                await mystic.delete()
                _cap = _["stream_1"].format(
                    f"https://t.me/{app.username}?start=info_{videoid}",
                    title[:23],
                    check[0]["dur"],
                    user,
                )
                if _thumb_on:
                    img = await get_thumb(videoid)
                    run = await app.send_photo(
                        chat_id=original_chat_id,
                        photo=img,
                        caption=_cap,
                        reply_markup=InlineKeyboardMarkup(button),
                        has_spoiler=True,
                    )
                else:
                    run = await app.send_message(
                        chat_id=original_chat_id,
                        text=f'<a href="{THUMB_OFF_VIDEO_URL}">\u200C</a>{_cap}',
                        reply_markup=InlineKeyboardMarkup(button),
                        parse_mode=ParseMode.HTML,
                        invert_media=True,
                        disable_web_page_preview=False,
                    )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"

            elif "index_" in queued:
                stream = dynamic_media_stream(path=videoid, video=video)
                try:
                    await client.play(chat_id, stream)
                except:
                    return await app.send_message(original_chat_id, text=_["call_6"])

                button = stream_markup(_, chat_id, autoplay_on=await is_autoplay(chat_id))
                if _thumb_on:
                    run = await app.send_photo(
                        chat_id=original_chat_id,
                        photo=config.STREAM_IMG_URL,
                        caption=_["stream_2"].format(user),
                        reply_markup=InlineKeyboardMarkup(button),
                        has_spoiler=True,
                    )
                else:
                    run = await app.send_message(
                        chat_id=original_chat_id,
                        text=f'<a href="{THUMB_OFF_VIDEO_URL}">\u200C</a>{_["stream_2"].format(user)}',
                        reply_markup=InlineKeyboardMarkup(button),
                        parse_mode=ParseMode.HTML,
                        invert_media=True,
                        disable_web_page_preview=False,
                    )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"

            else:
                stream = dynamic_media_stream(path=queued, video=video)
                try:
                    await client.play(chat_id, stream)
                except:
                    return await app.send_message(original_chat_id, text=_["call_6"])

                if videoid == "telegram":
                    button = stream_markup(_, chat_id, autoplay_on=await is_autoplay(chat_id))
                    _cap = _["stream_1"].format(
                        config.SUPPORT_CHAT, title[:23], check[0]["dur"], user
                    )
                    if _thumb_on:
                        run = await app.send_photo(
                            chat_id=original_chat_id,
                            photo=(
                                config.TELEGRAM_AUDIO_URL
                                if str(streamtype) == "audio"
                                else config.TELEGRAM_VIDEO_URL
                            ),
                            caption=_cap,
                            reply_markup=InlineKeyboardMarkup(button),
                            has_spoiler=True,
                        )
                    else:
                        run = await app.send_message(
                            chat_id=original_chat_id,
                            text=f'<a href="{THUMB_OFF_VIDEO_URL}">\u200C</a>{_cap}',
                            reply_markup=InlineKeyboardMarkup(button),
                            parse_mode=ParseMode.HTML,
                            invert_media=True,
                            disable_web_page_preview=False,
                        )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "tg"

                elif videoid == "soundcloud":
                    button = stream_markup(_, chat_id, autoplay_on=await is_autoplay(chat_id))
                    _cap = _["stream_1"].format(
                        config.SUPPORT_CHAT, title[:23], check[0]["dur"], user
                    )
                    if _thumb_on:
                        run = await app.send_photo(
                            chat_id=original_chat_id,
                            photo=config.SOUNCLOUD_IMG_URL,
                            caption=_cap,
                            reply_markup=InlineKeyboardMarkup(button),
                            has_spoiler=True,
                        )
                    else:
                        run = await app.send_message(
                            chat_id=original_chat_id,
                            text=f'<a href="{THUMB_OFF_VIDEO_URL}">\u200C</a>{_cap}',
                            reply_markup=InlineKeyboardMarkup(button),
                            parse_mode=ParseMode.HTML,
                            invert_media=True,
                            disable_web_page_preview=False,
                        )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "tg"

                else:
                    button = stream_markup(_, chat_id, autoplay_on=await is_autoplay(chat_id))
                    _cap = _["stream_1"].format(
                        f"https://t.me/{app.username}?start=info_{videoid}",
                        title[:23],
                        check[0]["dur"],
                        user,
                    )
                    try:
                        if _thumb_on:
                            img = await get_thumb(videoid)
                            run = await app.send_photo(
                                chat_id=original_chat_id,
                                photo=img,
                                caption=_cap,
                                reply_markup=InlineKeyboardMarkup(button),
                                has_spoiler=True,
                            )
                        else:
                            run = await app.send_message(
                                chat_id=original_chat_id,
                                text=f'<a href="{THUMB_OFF_VIDEO_URL}">\u200C</a>{_cap}',
                                reply_markup=InlineKeyboardMarkup(button),
                                parse_mode=ParseMode.HTML,
                                invert_media=True,
                                disable_web_page_preview=False,
                            )
                    except FloodWait as e:
                        LOGGER(__name__).warning(f"FloodWait: Sleeping for {e.value}")
                        await asyncio.sleep(e.value)
                        if _thumb_on:
                            img = await get_thumb(videoid)
                            run = await app.send_photo(
                                chat_id=original_chat_id,
                                photo=img,
                                caption=_cap,
                                reply_markup=InlineKeyboardMarkup(button),
                                has_spoiler=True,
                            )
                        else:
                            run = await app.send_message(
                                chat_id=original_chat_id,
                                text=f'<a href="{THUMB_OFF_VIDEO_URL}">\u200C</a>{_cap}',
                                reply_markup=InlineKeyboardMarkup(button),
                                parse_mode=ParseMode.HTML,
                                invert_media=True,
                                disable_web_page_preview=False,
                            )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "stream"


    async def start(self) -> None:
        LOGGER(__name__).info("Starting PyTgCalls Clients...")
        from pyrogram.errors import AuthKeyDuplicated, AuthKeyUnregistered

        async def start_client(client, index):
            if client is None:
                return
            try:
                await client.start()
            except FloodWait as e:
                LOGGER(__name__).warning(f"FloodWait in Call {index}. Waiting {e.value}s...")
                await asyncio.sleep(e.value)
                await client.start()
            except AuthKeyDuplicated:
                LOGGER(__name__).error(
                    f"Client {index} in Call: AUTH_KEY_DUPLICATED — session already in use. "
                    f"Generate a new session string for STRING{index}."
                )
            except AuthKeyUnregistered:
                LOGGER(__name__).error(
                    f"Client {index} in Call: AuthKeyUnregistered — session is invalid/expired. "
                    f"Generate a new session string for STRING{index}."
                )
            except Exception as e:
                LOGGER(__name__).error(f"Failed to start Client {index} in Call: {e}")

        await start_client(self.one, 1)
        await start_client(self.two, 2)
        await start_client(self.three, 3)
        await start_client(self.four, 4)
        await start_client(self.five, 5)

    @capture_internal_err
    async def ping(self) -> str:
        pings = []
        if config.STRING1:
            pings.append(self.one.ping)
        if config.STRING2:
            pings.append(self.two.ping)
        if config.STRING3:
            pings.append(self.three.ping)
        if config.STRING4:
            pings.append(self.four.ping)
        if config.STRING5:
            pings.append(self.five.ping)
        return str(round(sum(pings) / len(pings), 3)) if pings else "0.0"

    @capture_internal_err
    async def decorators(self) -> None:
        assistants = list(filter(None, [self.one, self.two, self.three, self.four, self.five]))

        CRITICAL = (
            ChatUpdate.Status.KICKED
            | ChatUpdate.Status.LEFT_GROUP
            | ChatUpdate.Status.CLOSED_VOICE_CHAT
            | ChatUpdate.Status.DISCARDED_CALL
            | ChatUpdate.Status.BUSY_CALL
        )

        async def unified_update_handler(client, update: Update) -> None:
            try:
                if isinstance(update, ChatUpdate):
                    status = update.status
                    if (status & ChatUpdate.Status.LEFT_CALL) or (status & CRITICAL):
                        await self.stop_stream(update.chat_id)
                        return

                elif isinstance(update, StreamEnded):
                    if update.stream_type == StreamEnded.Type.AUDIO:
                        assistant = await group_assistant(self, update.chat_id)
                        await self.play(assistant, update.chat_id)

            except Exception:
                import sys, traceback
                exc_type, exc_obj, exc_tb = sys.exc_info()
                full_trace = "".join(traceback.format_exception(exc_type, exc_obj, exc_tb))
                caption = (
                    f"🚨 <b>Stream Update Error</b>\n"
                    f"📍 <b>Update Type:</b> <code>{type(update).__name__}</code>\n"
                    f"📍 <b>Error Type:</b> <code>{exc_type.__name__}</code>"
                )
                filename = f"update_error_{getattr(update, 'chat_id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                await send_large_error(full_trace, caption, filename)

        for assistant in assistants:
            assistant.on_update()(unified_update_handler)


JARVIS = Call()