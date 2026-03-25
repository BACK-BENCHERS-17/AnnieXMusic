import re
import os
import asyncio
import hashlib
import traceback
import logging

from PIL import Image
from nudenet import NudeDetector
from pyrogram import Client, filters, enums
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from ANNIEMUSIC import app
from ANNIEMUSIC.utils.database import is_content_guard_on
from ANNIEMUSIC.utils.content_filter import _skin_ratio

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Nudenet setup
# ─────────────────────────────────────────────────────────────────────────────
try:
    _detector = NudeDetector()
    _NUDE_OK = True
    logger.info("NudeDetector loaded successfully.")
except Exception as e:
    _detector = None
    _NUDE_OK = False
    logger.error(f"NudeDetector failed to load: {e}")

_NSFW_EXPOSED = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "ANUS_EXPOSED",
    "BUTTOCKS_EXPOSED",
}
_NSFW_COVERED = {
    "FEMALE_GENITALIA_COVERED",
    "MALE_GENITALIA_COVERED",
    "FEMALE_BREAST_COVERED",
    "BUTTOCKS_COVERED",
}

_THRESHOLD_EXPOSED = 0.45
_THRESHOLD_COVERED = 0.55

_SKIN_RATIO_FALLBACK = 0.38

_nsfw_hash_cache: dict[str, bool] = {}

# ─────────────────────────────────────────────────────────────────────────────
# Keywords — only clearly explicit / illegal
# ─────────────────────────────────────────────────────────────────────────────
NSFW_KEYWORDS = [
    "nude", "naked", "porn", "pornography", "xxx", "hentai",
    "blowjob", "handjob", "masturbat", "orgasm", "erotic",
    "nudes", "nsfw", "onlyfans", "camgirl", "cam girl", "sexting",
    "intercourse", "18+", "x-rated", "adult content", "lewd",
    "pedophil", "child abuse",
    "vagina", "penis", "nipple", "nipples", "pussy",
    "boobs", "boob", "tits", "tit",
    "cocaine", "heroin", "methamphetamine", "mdma", "ecstasy",
    "opium", "hashish", "ketamine", "narcotics", "drug dealer",
    "darkweb", "dark web", "traffick",
    "chut", "lund", "gaand", "randi", "madarchod", "behenchod",
    "bhosdike", "lawda", "lauda", "chutiya", "gandu",
    "nangi", "nanga", "nangai", "bhosad", "harami",
]

NSFW_PATTERN = re.compile(
    r"(?i)\b(" + "|".join(re.escape(k.strip()) for k in NSFW_KEYWORDS) + r")\b"
)


def _has_nsfw_text(text: str) -> bool:
    return bool(NSFW_PATTERN.search(text)) if text else False


NSFW_STICKER_KEYWORDS = [
    "nsfw", "porn", "hentai", "nude", "lewd", "xxx",
    "naked", "boobs", "pussy", "vagina", "penis",
    "blowjob", "handjob", "anal", "orgasm", "masturbat",
    "onlyfans", "camgirl", "bdsm", "fetish",
    "ahegao", "ecchi", "oppai", "pantsu",
    "adult18", "sexy18", "hotgirl18", "sexygirl", "sexyanime",
    "nudeanime", "nakedgirl", "baregirl", "lewd_anime",
    "nsfwanime", "hentaigif", "hotanimegirl", "animegirl18",
    "adultpack", "nsfwpack", "explicit_pack", "nudepack",
    "slutpack", "bdsm_pack", "kinky_pack", "dirtypack",
    "nangi", "nanga", "chudai", "randi",
    "madarchod", "behenchod",
]

_STICKER_WORD_PATTERN = re.compile(
    r"(?i)(^|[_\-\s])(" +
    "|".join(re.escape(w) for w in [
        "sex", "sexy", "fuck", "erotic", "horny",
        "nude", "slut", "whore", "lund", "gaand", "chut"
    ]) +
    r")($|[_\-\s\d])"
)


def _has_nsfw_sticker_name(name: str) -> bool:
    if not name:
        return False
    name_lower = name.lower()
    if any(kw in name_lower for kw in NSFW_STICKER_KEYWORDS):
        return True
    if _STICKER_WORD_PATTERN.search(name_lower):
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# File helpers
# ─────────────────────────────────────────────────────────────────────────────
def _best_thumb(thumbs) -> str | None:
    if not thumbs:
        return None
    best = max(thumbs, key=lambda t: (getattr(t, "file_size", 0) or 0))
    return best.file_id


def _get_file_id(message: Message):
    if message.document:
        if message.document.file_size and int(message.document.file_size) > 5_000_000:
            return None
        allowed_mime = ("image/png", "image/jpeg", "image/webp", "image/gif", "video/mp4")
        if message.document.mime_type not in allowed_mime:
            return None
        return message.document.file_id
    if message.sticker:
        if message.sticker.is_animated or message.sticker.is_video:
            return _best_thumb(message.sticker.thumbs)
        return message.sticker.file_id
    if message.photo:
        return message.photo.file_id
    if message.animation:
        # Check actual animation file if small enough (GIF/mp4), else use thumbnail
        size = getattr(message.animation, "file_size", None) or 0
        if size <= 5_000_000:
            return message.animation.file_id
        return _best_thumb(message.animation.thumbs)
    if message.video:
        return _best_thumb(message.video.thumbs)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public helper — check a LOCAL image file (used by stream.py)
# ─────────────────────────────────────────────────────────────────────────────
def is_thumb_nsfw_local(img_path: str) -> bool:
    if not _NUDE_OK or not img_path or not os.path.exists(img_path):
        return False
    png_path = None
    try:
        png_path = _to_png(img_path)
        detections = _detector.detect(png_path)
        logger.info(f"[NSFW-THUMB] Detections for {img_path}: {detections}")
        return any(
            (det.get("class") in _NSFW_EXPOSED and det.get("score", 0) >= _THRESHOLD_EXPOSED)
            or (det.get("class") in _NSFW_COVERED and det.get("score", 0) >= _THRESHOLD_COVERED)
            for det in detections
        )
    except Exception:
        logger.error(f"[NSFW-THUMB] Error:\n{traceback.format_exc()}")
        return False
    finally:
        if png_path and png_path != img_path and os.path.exists(png_path):
            try:
                os.remove(png_path)
            except Exception:
                pass


def has_nsfw_text(text: str) -> bool:
    return _has_nsfw_text(text)


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(4096):
            h.update(chunk)
    return h.hexdigest()


def _to_png(path: str) -> str:
    try:
        img = Image.open(path).convert("RGB")
        png_path = path + ".png"
        img.save(png_path, "PNG")
        return png_path
    except Exception as e:
        logger.error(f"Image conversion failed: {e}")
        return path


# ─────────────────────────────────────────────────────────────────────────────
# Core visual NSFW check
# ─────────────────────────────────────────────────────────────────────────────
async def _is_visual_nsfw(tg_client: Client, file_id: str) -> bool:
    if not _NUDE_OK:
        return False
    path = None
    png_path = None
    try:
        path = await tg_client.download_media(file_id)
        if not path or not os.path.exists(path):
            return False
        logger.info(f"[NSFW] Downloaded: {path} ({os.path.getsize(path)} bytes)")
        file_hash = _file_hash(path)
        if file_hash in _nsfw_hash_cache:
            return _nsfw_hash_cache[file_hash]
        png_path = _to_png(path)
        detections = _detector.detect(png_path)
        logger.info(f"[NSFW] Detections: {detections}")
        is_nsfw = any(
            (det.get("class") in _NSFW_EXPOSED and det.get("score", 0) >= _THRESHOLD_EXPOSED)
            or (det.get("class") in _NSFW_COVERED and det.get("score", 0) >= _THRESHOLD_COVERED)
            for det in detections
        )
        # Fallback: if NudeDetector missed it, use skin ratio check
        if not is_nsfw:
            try:
                with open(png_path or path, "rb") as f:
                    img_bytes = f.read()
                ratio = _skin_ratio(img_bytes)
                logger.info(f"[NSFW] Skin ratio fallback: {ratio:.2f}")
                if ratio >= _SKIN_RATIO_FALLBACK:
                    is_nsfw = True
                    logger.info("[NSFW] Flagged by skin ratio fallback")
            except Exception:
                pass
        _nsfw_hash_cache[file_hash] = is_nsfw
        logger.info(f"[NSFW] Result: {'NSFW' if is_nsfw else 'SAFE'}")
        return is_nsfw
    except Exception:
        logger.error(f"[NSFW] Visual scan error:\n{traceback.format_exc()}")
        return False
    finally:
        for p in [path, png_path]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


# ─────────────────────────────────────────────────────────────────────────────
# Violation handler — group: delete + alert | DM: warn only
# ─────────────────────────────────────────────────────────────────────────────
_GROUP_ALERT = (
    "<blockquote>"
    "⛔ <b>ᴄᴏɴᴛᴇɴᴛ ʀᴇᴍᴏᴠᴇᴅ</b>\n\n"
    "🚫 <b>Reason :</b> {reason}\n\n"
    "🛡 This group has <b>NSFW / Illegal / Drug</b> content protection enabled.\n"
    "ℹ️ Use <code>/nsfw off</code> to disable."
    "</blockquote>\n"
    "<i>⏳ This notice will be deleted in 8 seconds.</i>"
)

_DM_ALERT = (
    "<blockquote>"
    "⛔ <b>ᴄᴏɴᴛᴇɴᴛ ᴘᴏʟɪᴄʏ ᴠɪᴏʟᴀᴛɪᴏɴ</b>\n\n"
    "🚫 <b>Reason :</b> {reason}\n\n"
    "🛡 This bot does <b>not</b> allow NSFW, explicit, illegal, or drug-related content."
    "</blockquote>\n"
    "<i>⏳ This warning will be deleted in 10 seconds.</i>"
)


async def _handle_violation(client: Client, message: Message, reason: str, is_group: bool):
    if is_group:
        try:
            await message.delete()
            logger.info(f"[NSFW] Deleted group message. Reason: {reason}")
        except Exception as e:
            logger.warning(f"[NSFW] Could not delete: {e}")
            return
        try:
            alert = await message.chat.send_message(
                _GROUP_ALERT.format(reason=reason),
                parse_mode=ParseMode.HTML,
            )
            await asyncio.sleep(8)
            await alert.delete()
        except Exception:
            pass
    else:
        try:
            warn = await message.reply(
                _DM_ALERT.format(reason=reason),
                parse_mode=ParseMode.HTML,
            )
            await asyncio.sleep(10)
            await warn.delete()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Main handler — groups + DMs, ON by default, skip only if explicitly disabled
# ─────────────────────────────────────────────────────────────────────────────
@app.on_message(~filters.bot, group=-5)
async def nsfw_guard(client: Client, message: Message):
    if not message or not message.chat:
        return

    is_group = message.chat.type in (
        enums.ChatType.GROUP,
        enums.ChatType.SUPERGROUP,
    )
    is_private = message.chat.type == enums.ChatType.PRIVATE

    if not is_group and not is_private:
        return

    # Skip if explicitly disabled for this chat
    try:
        if not await is_content_guard_on(message.chat.id):
            return
    except Exception:
        pass  # Default to ON (safe) when DB fails

    # ── 1. Text / caption keyword check ─────────────────────────────────
    text = message.text or message.caption or ""
    if _has_nsfw_text(text):
        return await _handle_violation(client, message, "Explicit / illegal content in text", is_group)

    # ── 2. Stickers ───────────────────────────────────────────────────────
    if message.sticker:
        set_name = message.sticker.set_name or ""
        emoji    = message.sticker.emoji    or ""
        if (
            _has_nsfw_sticker_name(set_name)
            or _has_nsfw_text(set_name)
            or _has_nsfw_text(emoji)
        ):
            return await _handle_violation(client, message, "NSFW sticker pack", is_group)
        file_id = _get_file_id(message)
        if file_id:
            if await _is_visual_nsfw(client, file_id):
                return await _handle_violation(client, message, "18+ sticker content", is_group)
        if (message.sticker.is_video or message.sticker.is_animated) and not file_id:
            explicit_only = ["nsfw", "porn", "xxx", "hentai", "nude", "naked", "lewd", "ecchi", "ahegao"]
            if any(hint in set_name.lower() for hint in explicit_only):
                return await _handle_violation(client, message, "Explicit animated sticker", is_group)

    # ── 3. Photos, videos, animations, documents ─────────────────────────
    if message.photo or message.video or message.animation or message.document:
        file_id = _get_file_id(message)
        if file_id:
            if await _is_visual_nsfw(client, file_id):
                return await _handle_violation(client, message, "18+ visual content", is_group)
