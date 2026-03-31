import asyncio
import os
from datetime import datetime, timedelta
from typing import Union

from ntgcalls import TelegramServerError, ConnectionError as NTgConnectionError
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, ChatAdminRequired, ChannelInvalid, ChannelPrivate
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.exceptions import NoActiveGroupCall, MTProtoClientNotConnected
from pytgcalls.types import AudioQuality, ChatUpdate, MediaStream, StreamEnded, Update, VideoQuality

import config
from strings import get_string
from KHUSHI import LOGGER, YouTube, app
from KHUSHI.misc import db
from KHUSHI.utils.cookie_handler import COOKIE_PATH
from KHUSHI.utils.database import (
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
from KHUSHI.utils.exceptions import AssistantErr
from KHUSHI.utils.formatters import check_duration, seconds_to_min, speed_converter
from KHUSHI.utils.prefetch import trigger_prefetch, cancel_prefetch
from KHUSHI.utils.inline import stream_markup, stream_markup_timer, add_to_channel_markup, InlineKeyboardButton as StyledBtn
from KHUSHI.utils.stream.autoclear import auto_clean
from KHUSHI.utils.thumbnails import get_thumb
from KHUSHI.utils.errors import capture_internal_err, send_large_error
from KHUSHI.utils.raw_send import send_msg_invert_preview

THUMB_OFF_VIDEO_URL = "https://files.catbox.moe/4vr2jc.mp4"

autoend = {}
counter = {}
autoplay_history: dict[int, list] = {}  # per-chat played video IDs history

def _get_cdn_headers() -> dict:
    """Return CDN headers that match the current best SmartYTDL client (dynamic)."""
    try:
        from KHUSHI.utils.ytdl_smart import get_cdn_headers as _smart_headers
        return _smart_headers()
    except Exception:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 14; Oculus Quest 3) "
                "AppleWebKit/537.36 (KHTML, like Gecko) OculusBrowser/35.0.0 "
                "VR SamsungBrowser/4.0 Chrome/124.0.6367.118 Mobile Safari/537.36"
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
        headers = _get_cdn_headers()

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


def _check_connected(assistant) -> bool:
    """Return True if the PyTgCalls assistant's underlying Pyrogram client is connected."""
    try:
        pyrogram_client = getattr(assistant, '_app', None) or getattr(assistant, 'mtproto_client', None)
        if pyrogram_client is not None:
            return getattr(pyrogram_client, 'is_connected', False)
        # No way to check — assume connected
        return True
    except Exception:
        return True


# ── Related song picker (used when queue ends) ────────────────────────────────
_RECO_POOL = {
    "bollywood": [
        "Tum Hi Ho", "Channa Mereya", "Ae Dil Hai Mushkil", "Kesariya Brahmastra",
        "Phir Bhi Tumko Chaahunga", "Bekhayali", "Hawayein", "Pachtaoge",
        "Zaalima", "Tera Ban Jaunga", "Ik Vaari Aa Rockstar", "Kabira",
        "Tujhe Kitna Chahne Lage", "Ve Maahi", "Dil Diyan Gallan",
        "Agar Tum Saath Ho", "Khairiyat", "Hasi Ban Gaye", "Galliyan",
    ],
    "punjabi": [
        "Lahore Guru Randhawa", "Morni Banke", "Kala Chashma", "Proper Patola",
        "Illegal Weapon", "Jatt Da Muqabla", "Backbone", "Coka Sukh E",
        "Ban Ja Rani", "Naah Harrdy Sandhu", "Nach Punjaban", "Lover Diljit",
        "Yeah Baby Garry Sandhu", "Paani Paani Badshah", "Burjkhalifa",
        "Devil Karan Aujla", "Slowly Slowly Guru Randhawa", "Suit Suit",
    ],
    "hiphop": [
        "DIVINE Mirchi", "Emiway Machayenge", "MC Stan Insaan",
        "Gully Boy Asli Hip Hop", "Sher Aaya Sher", "Azadi Gully Boy",
        "With You AP Dhillon", "Excuses AP Dhillon", "Arjan Vailly Animal",
        "Softly Karan Aujla", "Not Ur Friend Karan Aujla",
    ],
    "sad": [
        "Judaai Atif Aslam", "Jo Bhi Main Rockstar", "Dil Ko Karar Aaya",
        "Woh Lamhe", "Teri Yaad Atif Aslam", "Kya Hua Tera Wada",
        "Phir Mohabbat", "Tera Hone Laga Hoon", "Ae Zindagi Gale Laga Le",
    ],
    "party": [
        "Balam Pichkari", "Sheila Ki Jawani", "Abhi Toh Party Shuru Hui Hai",
        "Kar Gayi Chull", "Nachde Ne Saare", "Gallan Goodiyaan",
        "Genda Phool Badshah", "Alcoholia", "Kamariya Mitron",
    ],
    "romantic": [
        "Pehla Nasha", "Dil Ko Maine Di Kasam", "Tera Zikr", "Hasi Ban Gaye",
        "Kuch Is Tarah Atif Aslam", "Aankhon Mein Teri", "Zindagi Do Pal Ki",
    ],
}

_HINDI_KEYWORDS = {"tum", "dil", "pyaar", "tera", "mera", "hai", "nahi", "aur", "main",
                   "hum", "kya", "ye", "yeh", "jaan", "zindagi", "aaja", "mere", "tu",
                   "tere", "sun", "aa", "kaho", "mujhe", "meri", "kuch"}
_PUNJABI_KEYWORDS = {"jatt", "punjabi", "ni", "vi", "das", "ik", "oye", "yaar", "pagg",
                     "nachi", "gabru", "bandhe", "kudi", "munda", "wala", "wali", "chandigarh"}
_HIPHOP_KEYWORDS = {"rap", "hip", "hop", "flow", "beat", "bars", "divine", "emiway",
                    "mc", "gully", "drip", "swag", "diss"}
_PARTY_KEYWORDS = {"party", "dance", "beat", "dj", "remix", "club", "nonstop", "mashup"}
_SAD_KEYWORDS = {"sad", "bekhayali", "judaai", "woh", "rona", "dard", "door", "alvida",
                 "tanha", "tanhai", "bewafa", "bichad"}


import random as _rnd


def _pick_related_songs(last_title: str, n: int = 4) -> list:
    tl = last_title.lower()
    words = set(tl.split())

    # Score each genre based on keyword overlap
    if words & _PUNJABI_KEYWORDS:
        primary = "punjabi"
    elif words & _HIPHOP_KEYWORDS:
        primary = "hiphop"
    elif words & _PARTY_KEYWORDS:
        primary = "party"
    elif words & _SAD_KEYWORDS:
        primary = "sad"
    elif words & _HINDI_KEYWORDS:
        primary = "bollywood"
    else:
        primary = "bollywood"

    primary_pool = _RECO_POOL[primary][:]
    # Mix in some from bollywood/punjabi for variety
    secondary = "punjabi" if primary != "punjabi" else "bollywood"
    mixed_pool = primary_pool + _rnd.sample(_RECO_POOL[secondary], min(4, len(_RECO_POOL[secondary])))

    # Remove the last played song if it's in the pool
    mixed_pool = [s for s in mixed_pool if last_title.lower() not in s.lower()]

    _rnd.shuffle(mixed_pool)
    return mixed_pool[:n]


class Call:
    def __init__(self):
        self.one = None
        self.two = None
        self.three = None
        self.four = None
        self.five = None
        self.active_calls: set[int] = set()
        # Store references to underlying Pyrogram clients for client recreation
        self._pyrogram_clients: dict[int, object] = {}

    def setup_clients(self, userbot) -> None:
        """Initialize PyTgCalls using the shared Userbot Pyrogram clients.
        This avoids AUTH_KEY_DUPLICATED by reusing a single connection per session."""
        if userbot.one:
            self._pyrogram_clients[1] = userbot.one
            self.one = PyTgCalls(userbot.one)
        if userbot.two:
            self._pyrogram_clients[2] = userbot.two
            self.two = PyTgCalls(userbot.two)
        if userbot.three:
            self._pyrogram_clients[3] = userbot.three
            self.three = PyTgCalls(userbot.three)
        if userbot.four:
            self._pyrogram_clients[4] = userbot.four
            self.four = PyTgCalls(userbot.four)
        if userbot.five:
            self._pyrogram_clients[5] = userbot.five
            self.five = PyTgCalls(userbot.five)

    def _recreate_pytgcalls(self, index: int) -> object:
        """Recreate a fresh PyTgCalls instance for a given assistant index.
        Used to recover from AUTH_KEY_DUPLICATED which leaves PyTgCalls in bad state."""
        pyrogram_client = self._pyrogram_clients.get(index)
        if pyrogram_client is None:
            return None
        new_client = PyTgCalls(pyrogram_client)
        if index == 1:
            self.one = new_client
        elif index == 2:
            self.two = new_client
        elif index == 3:
            self.three = new_client
        elif index == 4:
            self.four = new_client
        elif index == 5:
            self.five = new_client
        return new_client


    @capture_internal_err
    async def pause_stream(self, chat_id: int) -> None:
        assistant = await group_assistant(self, chat_id)
        try:
            await assistant.pause(chat_id)
        except MTProtoClientNotConnected:
            raise AssistantErr(
                "ᴀssɪsᴛᴀɴᴛ ᴅɪsᴄᴏɴɴᴇᴄᴛᴇᴅ.\n\n"
                "ᴘʟᴇᴀsᴇ ᴜsᴇ /stop ᴀɴᴅ /play ᴛᴏ ʀᴇsᴛᴀʀᴛ."
            )

    @capture_internal_err
    async def resume_stream(self, chat_id: int) -> None:
        assistant = await group_assistant(self, chat_id)
        try:
            await assistant.resume(chat_id)
        except MTProtoClientNotConnected:
            raise AssistantErr(
                "ᴀssɪsᴛᴀɴᴛ ᴅɪsᴄᴏɴɴᴇᴄᴛᴇᴅ.\n\n"
                "ᴘʟᴇᴀsᴇ ᴜsᴇ /stop ᴀɴᴅ /play ᴛᴏ ʀᴇsᴛᴀʀᴛ."
            )

    @capture_internal_err
    async def mute_stream(self, chat_id: int) -> None:
        assistant = await group_assistant(self, chat_id)
        try:
            await assistant.mute(chat_id)
        except MTProtoClientNotConnected:
            raise AssistantErr(
                "ᴀssɪsᴛᴀɴᴛ ᴅɪsᴄᴏɴɴᴇᴄᴛᴇᴅ.\n\n"
                "ᴘʟᴇᴀsᴇ ᴜsᴇ /stop ᴀɴᴅ /play ᴛᴏ ʀᴇsᴛᴀʀᴛ."
            )

    @capture_internal_err
    async def unmute_stream(self, chat_id: int) -> None:
        assistant = await group_assistant(self, chat_id)
        try:
            await assistant.unmute(chat_id)
        except MTProtoClientNotConnected:
            raise AssistantErr(
                "ᴀssɪsᴛᴀɴᴛ ᴅɪsᴄᴏɴɴᴇᴄᴛᴇᴅ.\n\n"
                "ᴘʟᴇᴀsᴇ ᴜsᴇ /stop ᴀɴᴅ /play ᴛᴏ ʀᴇsᴛᴀʀᴛ."
            )

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
        from KHUSHI.utils.database import is_autoplay
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
        try:
            assistant = await group_assistant(self, chat_id)
        except AssistantErr:
            assistant = None

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
        if assistant and chat_id in self.active_calls:
            try:
                await assistant.pause(chat_id)
            except Exception:
                pass
        cancel_prefetch(chat_id)
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
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-i", file_path,
                "-filter:v", f"setpts={vs}*PTS",
                "-filter:a", f"atempo={speed}",
                out,
                stdin=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
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
            from KHUSHI.utils.downloader import _convert_webm_to_m4a, extract_video_id
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
                    wait_sec = 1 if attempt == 0 else 2
                    LOGGER(__name__).info(f"[PLAY] Waiting {wait_sec}s before retry {attempt+2}/3")
                    await asyncio.sleep(wait_sec)
                    continue
                # All retries failed — try VC reset as last resort
                LOGGER(__name__).warning(f"[PLAY] All retries failed. Attempting VC reset for chat={chat_id}")
                try:
                    await assistant.leave_call(chat_id, close=True)
                    await asyncio.sleep(1)
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
                    await asyncio.sleep(1)
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
                    f"❌ <b>ᴛᴇʟᴇɢʀᴀᴍ ғʟᴏᴏᴅ ᴡᴀɪᴛ</b>\n\n"
                    f"<blockquote>"
                    f"⏰ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ <b>{wait_sec}s</b> ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ."
                    f"</blockquote>"
                )
            except ChannelInvalid:
                raise AssistantErr(
                    "<b>ᴀssɪsᴛᴀɴᴛ ᴄᴀɴɴᴏᴛ ᴊᴏɪɴ ᴛʜɪs ɢʀᴏᴜᴘ.</b>\n\n"
                    "<blockquote>ᴘʟᴇᴀsᴇ ᴀᴅᴅ ᴛʜᴇ ᴀssɪsᴛᴀɴᴛ ᴀᴄᴄᴏᴜɴᴛ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ.</blockquote>"
                )
            except ChannelPrivate:
                LOGGER(__name__).info(
                    f"[PLAY] ChannelPrivate — trying to auto-add assistant to chat={chat_id}"
                )
                _auto_joined = False
                try:
                    _asst_client = getattr(assistant, '_app', None)
                    _asst_id = None
                    if _asst_client:
                        _me = getattr(_asst_client, 'me', None)
                        if _me:
                            _asst_id = _me.id
                    if _asst_id:
                        await app.add_chat_members(chat_id, _asst_id)
                        LOGGER(__name__).info(
                            f"[PLAY] Assistant auto-added to chat={chat_id}. Retrying play."
                        )
                        await asyncio.sleep(2)
                        await assistant.play(chat_id, stream)
                        _auto_joined = True
                        break
                except Exception as _add_err:
                    LOGGER(__name__).warning(f"[PLAY] add_chat_members failed: {_add_err}")
                if not _auto_joined:
                    try:
                        _invite = await app.create_chat_invite_link(chat_id)
                        _asst_client = getattr(assistant, '_app', None)
                        if _asst_client:
                            await _asst_client.join_chat(_invite.invite_link)
                            LOGGER(__name__).info(
                                f"[PLAY] Assistant joined via invite link for chat={chat_id}. Retrying."
                            )
                            await asyncio.sleep(2)
                            await assistant.play(chat_id, stream)
                            _auto_joined = True
                            break
                    except Exception as _inv_err:
                        LOGGER(__name__).warning(f"[PLAY] Invite-link join failed: {_inv_err}")
                if not _auto_joined:
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
        trigger_prefetch(chat_id)

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
                        from KHUSHI.utils.formatters import time_to_seconds as _tts

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

                            # Fast path: CDN URL extraction → instant VC stream,
                            # background download caches for future plays
                            from KHUSHI.utils.downloader import fast_get_stream
                            ap_file = await fast_get_stream(ap_vidid)
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
                                    _BEAR = "🧸"
                                    _TIME = "⏳"
                                    _DOT  = "🔹"
                                    _AROW = (
                                        "🧸"
                                        "🔤"
                                        "🔤"
                                        "🔤"
                                        "🔤"
                                        "🔤"
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
                                        ap_msg = await send_msg_invert_preview(
                                            app,
                                            original_chat_id,
                                            text=f'<a href="{THUMB_OFF_VIDEO_URL}">\u200C</a>{_ap_caption}',
                                            reply_markup=_ap_markup,
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
                except Exception:
                    _ = get_string("en")

                try:
                    from pyrogram.types import InlineKeyboardMarkup
                    last_title = popped.get("title", "") if popped else ""
                    _sugg = _pick_related_songs(last_title, 4)

                    # Build 2-per-row song suggestion buttons
                    _rows = []
                    for _i in range(0, len(_sugg), 2):
                        _row = []
                        for _s in _sugg[_i:_i+2]:
                            _lbl = (_s[:21] + "…") if len(_s) > 21 else _s
                            _row.append(StyledBtn(
                                text=f"▶ {_lbl}",
                                callback_data=f"rp:{_s[:40]}",
                            ))
                        _rows.append(_row)
                    # Bottom row: add-me + close
                    _rows.append([
                        StyledBtn(
                            text="✚ ᴀᴅᴅ ᴍᴇ ʙᴀʙʏ ✚",
                            url=f"https://t.me/{app.username}?startgroup=true",
                            style="primary",
                        ),
                        StyledBtn(
                            text=_["CLOSE_BUTTON"],
                            callback_data="close",
                            style="danger",
                        ),
                    ])

                    _AROW = (
                        "🧸"
                        "🔤"
                        "🔤"
                        "🔤"
                        "🔤"
                        "🔤"
                    )
                    _last_short = (last_title[:32] + "…") if len(last_title) > 32 else last_title
                    _end_text = (
                        f"<blockquote>{_AROW}</blockquote>\n\n"
                        "<blockquote>"
                        "✨"
                        " <b>ǫᴜᴇᴜᴇ ᴇɴᴅᴇᴅ!</b>\n"
                        + (f"🔹 ʟᴀsᴛ: <b>{_last_short}</b>\n" if _last_short else "")
                        + "\n⚡️"
                        " <b>ʏᴏᴜ ᴍɪɢʜᴛ ʟɪᴋᴇ ᴛʜᴇꜱᴇ:</b>"
                        "</blockquote>"
                    )
                    await app.send_message(
                        chat_id,
                        text=_end_text,
                        reply_markup=InlineKeyboardMarkup(_rows),
                    )
                except Exception:
                    pass
                return
        except:
            # Always clean up active_calls regardless of whether leave_call succeeds.
            # Without this, a failed leave_call leaves the chat stuck in active_calls,
            # causing every subsequent /play to queue instead of joining fresh.
            try:
                await _clear_(chat_id)
            except Exception:
                pass
            try:
                await client.leave_call(chat_id)
            except Exception:
                pass
            self.active_calls.discard(chat_id)
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
                    await _clear_(chat_id)
                    try:
                        await client.leave_call(chat_id)
                    except Exception:
                        pass
                    self.active_calls.discard(chat_id)
                    return await app.send_message(original_chat_id, text=_["call_6"])

                stream = dynamic_media_stream(path=link, video=video)
                try:
                    await client.play(chat_id, stream)
                except Exception:
                    await _clear_(chat_id)
                    try:
                        await client.leave_call(chat_id)
                    except Exception:
                        pass
                    self.active_calls.discard(chat_id)
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
                except Exception:
                    await _clear_(chat_id)
                    try:
                        await client.leave_call(chat_id)
                    except Exception:
                        pass
                    self.active_calls.discard(chat_id)
                    return await mystic.edit_text(
                        _["call_6"], disable_web_page_preview=True
                    )

                stream = dynamic_media_stream(path=file_path, video=video)
                try:
                    await client.play(chat_id, stream)
                except Exception:
                    await _clear_(chat_id)
                    try:
                        await client.leave_call(chat_id)
                    except Exception:
                        pass
                    self.active_calls.discard(chat_id)
                    return await app.send_message(original_chat_id, text=_["call_6"])
                trigger_prefetch(chat_id)

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
                        disable_web_page_preview=False,
                    )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"

            elif "index_" in queued:
                stream = dynamic_media_stream(path=videoid, video=video)
                try:
                    await client.play(chat_id, stream)
                except Exception:
                    await _clear_(chat_id)
                    try:
                        await client.leave_call(chat_id)
                    except Exception:
                        pass
                    self.active_calls.discard(chat_id)
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
                    run = await send_msg_invert_preview(
                        app,
                        original_chat_id,
                        text=f'<a href="{THUMB_OFF_VIDEO_URL}">\u200C</a>{_["stream_2"].format(user)}',
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"

            else:
                stream = dynamic_media_stream(path=queued, video=video)
                try:
                    await client.play(chat_id, stream)
                except Exception:
                    await _clear_(chat_id)
                    try:
                        await client.leave_call(chat_id)
                    except Exception:
                        pass
                    self.active_calls.discard(chat_id)
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
                        run = await send_msg_invert_preview(
                            app,
                            original_chat_id,
                            text=f'<a href="{THUMB_OFF_VIDEO_URL}">\u200C</a>{_cap}',
                            reply_markup=InlineKeyboardMarkup(button),
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
                        run = await send_msg_invert_preview(
                            app,
                            original_chat_id,
                            text=f'<a href="{THUMB_OFF_VIDEO_URL}">\u200C</a>{_cap}',
                            reply_markup=InlineKeyboardMarkup(button),
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
                            run = await send_msg_invert_preview(
                                app,
                                original_chat_id,
                                text=f'<a href="{THUMB_OFF_VIDEO_URL}">\u200C</a>{_cap}',
                                reply_markup=InlineKeyboardMarkup(button),
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
                            run = await send_msg_invert_preview(
                                app,
                                original_chat_id,
                                text=f'<a href="{THUMB_OFF_VIDEO_URL}">\u200C</a>{_cap}',
                                reply_markup=InlineKeyboardMarkup(button),
                            )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "stream"


    async def start(self) -> None:
        LOGGER(__name__).info("Starting PyTgCalls Clients...")
        from pyrogram.errors import AuthKeyDuplicated, AuthKeyUnregistered

        async def _try_start_once(client, index) -> bool:
            """Try to start a single client. Returns True on success, False on failure."""
            if client is None:
                return False
            try:
                await client.start()
                LOGGER(__name__).info(f"Client {index} started successfully.")
                return True
            except FloodWait as e:
                LOGGER(__name__).warning(f"FloodWait in Call {index}. Waiting {e.value}s...")
                await asyncio.sleep(e.value)
                return False
            except AuthKeyDuplicated:
                LOGGER(__name__).warning(
                    f"Client {index}: AUTH_KEY_DUPLICATED — old session still alive."
                )
                try:
                    await client.stop()
                except Exception:
                    pass
                return False
            except AuthKeyUnregistered:
                LOGGER(__name__).error(
                    f"Client {index}: AuthKeyUnregistered — session is invalid/expired. "
                    f"Generate a new session string for STRING{index}."
                )
                return None  # None = permanent failure, don't retry
            except Exception as e:
                err_str = str(e)
                if "already running" in err_str:
                    try:
                        await client.stop()
                    except Exception:
                        pass
                    return False
                LOGGER(__name__).warning(f"Client {index} start failed: {e}")
                return False

        async def start_client_with_bg_retry(client, index):
            """Try to start client immediately; if AUTH_KEY_DUPLICATED, keep retrying in background."""
            if client is None:
                return

            result = await _try_start_once(client, index)

            if result is True:
                return  # Started OK
            if result is None:
                return  # Permanent failure (invalid session)

            # Transient failure (AUTH_KEY_DUPLICATED or "already running") — retry in background
            LOGGER(__name__).info(
                f"Client {index}: Starting background retry task (old session needs time to expire)..."
            )

            async def _bg_retry():
                from KHUSHI.core.userbot import assistants
                for attempt in range(20):  # retry up to 20 times, every 15s = max 5 min
                    await asyncio.sleep(15)
                    fresh = self._recreate_pytgcalls(index)
                    if fresh is None:
                        return
                    ok = await _try_start_once(fresh, index)
                    if ok is True:
                        LOGGER(__name__).info(
                            f"Client {index}: Background retry succeeded on attempt {attempt + 1}."
                        )
                        # Run post-start setup for this assistant
                        try:
                            from KHUSHI import userbot as _ub
                            asst_map = {1: _ub.one, 2: _ub.two, 3: _ub.three, 4: _ub.four, 5: _ub.five}
                            pyrogram_asst = asst_map.get(index)
                            if pyrogram_asst:
                                await _ub._setup_assistant(pyrogram_asst, index)
                        except Exception as se:
                            LOGGER(__name__).warning(f"Client {index}: post-start setup error: {se}")
                        # Re-register decorators so the new client gets stream update callbacks
                        try:
                            await self.decorators()
                        except Exception:
                            pass
                        return
                    if ok is None:
                        return  # Permanent failure — stop retrying
                    # ok is False — continue retrying
                LOGGER(__name__).error(
                    f"Client {index}: Background retry exhausted after 20 attempts. "
                    f"Generate a new session string for STRING{index}."
                )

            asyncio.create_task(_bg_retry())

        await start_client_with_bg_retry(self.one, 1)
        await start_client_with_bg_retry(self.two, 2)
        await start_client_with_bg_retry(self.three, 3)
        await start_client_with_bg_retry(self.four, 4)
        await start_client_with_bg_retry(self.five, 5)

    async def ping(self) -> str:
        pings = []
        pairs = [
            (config.STRING1, self.one),
            (config.STRING2, self.two),
            (config.STRING3, self.three),
            (config.STRING4, self.four),
            (config.STRING5, self.five),
        ]
        for string, client in pairs:
            if string and client is not None:
                try:
                    val = client.ping
                    if val is not None and val > 0:
                        pings.append(val)
                except Exception:
                    pass
        return str(round(sum(pings) / len(pings), 3)) if pings else "N/A"

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
                    chat_id = update.chat_id
                    # Handle both AUDIO and VIDEO stream endings
                    if update.stream_type in (StreamEnded.Type.AUDIO, StreamEnded.Type.VIDEO):
                        try:
                            assistant = await group_assistant(self, chat_id)
                        except AssistantErr:
                            # No connected assistant — force-clean the stuck state so
                            # the next /play doesn't get queued behind a ghost stream
                            LOGGER(__name__).warning(
                                f"[StreamEnded] No connected assistant for chat={chat_id}. "
                                f"Force-clearing stuck VC state."
                            )
                            await _clear_(chat_id)
                            self.active_calls.discard(chat_id)
                            return
                        except Exception as _ga_err:
                            LOGGER(__name__).error(
                                f"[StreamEnded] group_assistant failed for chat={chat_id}: {_ga_err}"
                            )
                            await _clear_(chat_id)
                            self.active_calls.discard(chat_id)
                            return

                        try:
                            await self.play(assistant, chat_id)
                        except Exception as _play_err:
                            # play() failed — ensure VC state is cleaned up completely
                            LOGGER(__name__).error(
                                f"[StreamEnded] play() failed for chat={chat_id}: {_play_err}. "
                                f"Force-clearing to prevent stuck state."
                            )
                            await _clear_(chat_id)
                            try:
                                await client.leave_call(chat_id)
                            except Exception:
                                pass
                            self.active_calls.discard(chat_id)

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