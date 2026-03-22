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
from config import LOGGER_ID

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

# Classes that trigger NSFW — exposed body parts (lower threshold)
_NSFW_EXPOSED = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "ANUS_EXPOSED",
    "BUTTOCKS_EXPOSED",
}
# Covered/semi-covered body parts (higher threshold to reduce false positives)
_NSFW_COVERED = {
    "FEMALE_GENITALIA_COVERED",
    "MALE_GENITALIA_COVERED",
    "FEMALE_BREAST_COVERED",
    "BUTTOCKS_COVERED",
}

_THRESHOLD_EXPOSED = 0.35   # more sensitive for explicit content
_THRESHOLD_COVERED = 0.60   # stricter for covered/partial content

# In-memory hash cache to avoid re-scanning same files
_nsfw_hash_cache: dict[str, bool] = {}

# ─────────────────────────────────────────────────────────────────────────────
# Keyword filter (text / captions / sticker pack names)
# ─────────────────────────────────────────────────────────────────────────────
NSFW_KEYWORDS = [
    "sex", "sexy", "nude", "naked", "porn", "pornography", "xxx", "adult",
    "hentai", "boobs", "boob", "tits", "tit", "nipple", "nipples", "pussy",
    "vagina", "penis", "dick", "cock", "ass", "anal", "blowjob", "handjob",
    "masturbat", "orgasm", "erotic", "nudes", "nsfw", "onlyfans", "escort",
    "prostitut", "rape", "molest", "harassment", "slutty", "slut", "bitch",
    "whore", "stripper", "strip club", "camgirl", "cam girl", "sexting",
    "sexual", "intercourse", "fornication", "lust", "lusty", "horny",
    "18+", "x-rated", "rated x", "adult content", "explicit", "lewd",
    "drug", "drugs", "cocaine", "heroin", "meth", "methamphetamine", "lsd",
    "marijuana", "weed", "ganja", "crack", "mdma", "ecstasy", "opium",
    "cannabis", "hashish", "hash", "smuggl", "traffick", "terror", "terrorist",
    "bomb", "explosive", "weapon", "murder", "kill", "suicide", "pedophil",
    "child abuse", "cp ", " cp", "illegal", "darkweb", "dark web",
    "ketamine", "xanax abuse", "overdose", "drug dealer", "narcotics",
    "chut", "lund", "gaand", "bur", "randi", "harami", "maa ki", "behen ki",
    "bhosad", "madarchod", "behenchod", "bhosdike", "lawda", "lauda",
    "chutiya", "gandu", "saala", "sexy video", "sexy photo", "sexy pic",
    "nangi", "nanga", "nangai", "jism", "jisam",
]

NSFW_PATTERN = re.compile(
    r"(?i)\b(" + "|".join(re.escape(k.strip()) for k in NSFW_KEYWORDS) + r")\b"
)


def _has_nsfw_text(text: str) -> bool:
    return bool(NSFW_PATTERN.search(text)) if text else False


# ─────────────────────────────────────────────────────────────────────────────
# File helpers
# ─────────────────────────────────────────────────────────────────────────────
def _get_file_id(message: Message):
    """Get scannable file_id — use thumbnail for video/animated stickers."""
    if message.document:
        if message.document.file_size and int(message.document.file_size) > 5_000_000:
            return None
        if message.document.mime_type not in ("image/png", "image/jpeg", "image/webp"):
            return None
        return message.document.file_id

    if message.sticker:
        if message.sticker.is_animated or message.sticker.is_video:
            thumbs = message.sticker.thumbs
            return thumbs[0].file_id if thumbs else None
        return message.sticker.file_id

    if message.photo:
        return message.photo.file_id

    if message.animation:
        thumbs = message.animation.thumbs
        return thumbs[0].file_id if thumbs else None

    if message.video:
        thumbs = message.video.thumbs
        return thumbs[0].file_id if thumbs else None

    return None


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(4096):
            h.update(chunk)
    return h.hexdigest()


def _to_png(path: str) -> str:
    """Convert any image to PNG for consistent nudenet processing."""
    try:
        img = Image.open(path).convert("RGB")
        png_path = path + ".png"
        img.save(png_path, "PNG")
        return png_path
    except Exception as e:
        logger.error(f"Image conversion failed: {e}")
        return path


# ─────────────────────────────────────────────────────────────────────────────
# Core visual NSFW check (nudenet, fully local)
# ─────────────────────────────────────────────────────────────────────────────
async def _is_visual_nsfw(tg_client: Client, file_id: str) -> bool:
    if not _NUDE_OK:
        logger.warning("NudeDetector not available, skipping visual scan.")
        return False

    path = None
    png_path = None
    try:
        path = await tg_client.download_media(file_id)
        if not path or not os.path.exists(path):
            logger.warning(f"Download failed for file_id: {file_id}")
            return False

        logger.info(f"[NSFW] Downloaded: {path} ({os.path.getsize(path)} bytes)")

        # Check cache
        file_hash = _file_hash(path)
        if file_hash in _nsfw_hash_cache:
            logger.info(f"[NSFW] Cache hit: {_nsfw_hash_cache[file_hash]}")
            return _nsfw_hash_cache[file_hash]

        # Convert to PNG for consistent processing
        png_path = _to_png(path)

        # Run nudenet
        detections = _detector.detect(png_path)
        logger.info(f"[NSFW] Detections: {detections}")

        is_nsfw = any(
            (
                det.get("class") in _NSFW_EXPOSED and det.get("score", 0) >= _THRESHOLD_EXPOSED
            ) or (
                det.get("class") in _NSFW_COVERED and det.get("score", 0) >= _THRESHOLD_COVERED
            )
            for det in detections
        )

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
# Delete / warn handler
# ─────────────────────────────────────────────────────────────────────────────
async def _handle_violation(client: Client, message: Message, reason: str, is_group: bool):
    if is_group:
        try:
            await message.delete()
            logger.info(f"[NSFW] Deleted group message. Reason: {reason}")
        except Exception as e:
            logger.error(f"[NSFW] Could not delete group message: {e}")
        try:
            alert = await message.chat.send_message(
                "<blockquote>"
                "⛔ <b>Content Removed</b>\n\n"
                f"🚫 Reason: <b>{reason}</b>\n\n"
                "This group enforces a strict <b>No NSFW / No Illegal / No Drug</b> policy."
                "</blockquote>\n"
                "<i>This notice will be deleted in 8 seconds.</i>",
                parse_mode=ParseMode.HTML,
            )
            await asyncio.sleep(8)
            await alert.delete()
        except Exception:
            pass
    else:
        # DMs: Telegram does not allow bots to delete user messages in private chats
        try:
            user = message.from_user
            uid = user.id if user else "N/A"
            mention = user.mention if user else "Unknown"
            await client.forward_messages(LOGGER_ID, message.chat.id, message.id)
            await client.send_message(
                LOGGER_ID,
                "<blockquote>"
                f"⚠️ <b>NSFW Detected in DM</b>\n\n"
                f"👤 User: {mention} (<code>{uid}</code>)\n"
                f"📌 Reason: <b>{reason}</b>"
                "</blockquote>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        try:
            warn = await message.reply(
                "<blockquote>"
                "⛔ <b>Content Policy Violation</b>\n\n"
                f"🚫 You sent: <b>{reason}</b>\n\n"
                "This content violates our <b>No NSFW / No Illegal / No Drug</b> policy.\n"
                "Your message has been <b>reported to admins</b> for review."
                "</blockquote>\n"
                "<i>This notice will be deleted in 10 seconds.</i>",
                parse_mode=ParseMode.HTML,
            )
            await asyncio.sleep(10)
            await warn.delete()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Main handler — permanently ON, no toggle
# ─────────────────────────────────────────────────────────────────────────────
@app.on_message(~filters.bot, group=-5)
async def nsfw_guard(client: Client, message: Message):
    if not message or not message.chat:
        return

    is_group = message.chat.type in (
        enums.ChatType.GROUP,
        enums.ChatType.SUPERGROUP,
    )

    # ── 1. Text / caption keyword check ────────────────────────────────
    text = message.text or message.caption or ""
    if _has_nsfw_text(text):
        return await _handle_violation(client, message, "18+ / illegal / drug content in text", is_group)

    # ── 2. Stickers — keyword check + visual scan ───────────────────────
    if message.sticker:
        set_name = (message.sticker.set_name or "").lower()
        emoji    = (message.sticker.emoji    or "").lower()
        kws = [
            "nsfw", "adult", "sex", "porn", "nude", "lewd", "hentai",
            "xxx", "erotic", "18", "drug", "weed", "naked", "boob",
        ]
        if any(k in set_name for k in kws) or _has_nsfw_text(set_name) or _has_nsfw_text(emoji):
            return await _handle_violation(client, message, "NSFW sticker pack", is_group)
        file_id = _get_file_id(message)
        if file_id:
            if await _is_visual_nsfw(client, file_id):
                return await _handle_violation(client, message, "18+ sticker content", is_group)

    # ── 3. Visual scan — photos, videos, animations, documents ──────────
    if message.photo or message.video or message.animation or message.document:
        file_id = _get_file_id(message)
        if file_id:
            if await _is_visual_nsfw(client, file_id):
                return await _handle_violation(client, message, "18+ visual content", is_group)
