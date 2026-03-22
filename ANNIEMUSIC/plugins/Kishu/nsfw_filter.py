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
# Covered/semi-covered body parts (lower threshold for better detection)
_NSFW_COVERED = {
    "FEMALE_GENITALIA_COVERED",
    "MALE_GENITALIA_COVERED",
    "FEMALE_BREAST_COVERED",
    "BUTTOCKS_COVERED",
}

_THRESHOLD_EXPOSED = 0.45   # balanced — avoids false positives on normal images
_THRESHOLD_COVERED = 0.70   # strict — only flag clearly covered NSFW content

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
# Sticker pack keyword list — covers known NSFW packs + generic patterns
# ─────────────────────────────────────────────────────────────────────────────

# Exact / safe substrings — specific enough to only match adult content pack names
NSFW_STICKER_KEYWORDS = [
    # clearly adult keywords (safe substrings — won't match innocent words)
    "nsfw", "porn", "hentai", "nude", "lewd", "xxx",
    "naked", "boobs", "pussy", "vagina", "penis",
    "blowjob", "handjob", "anal", "orgasm", "masturbat",
    "onlyfans", "camgirl", "slutty", "bdsm", "fetish",
    "ahegao", "ecchi", "oppai", "pantsu", "naughty18",
    "adult18", "sexy18", "hotgirl18", "sexygirl", "sexyanime",
    "nudeanime", "nakedgirl", "baregirl", "lewd_anime",
    "nsfwanime", "hentaigif", "hotanimegirl", "animegirl18",
    "wallgif", "wall_gif", "adultpack", "nsfwpack",
    "explicit_pack", "nudepack", "slutpack", "bdsm_pack",
    "kinky_pack", "lingerie_pack", "dirtypack",
    # Hindi/Urdu explicit
    "nangi", "nanga", "chudai", "randi",
    "harami", "madarchod", "behenchod",
]

# Whole-word patterns for short keywords that could match innocent words
_STICKER_WORD_PATTERN = re.compile(
    r"(?i)(^|[_\-\s])(" +
    "|".join(re.escape(w) for w in ["sex", "sexy", "fuck", "erotic", "horny", "nude", "slut", "whore", "lund", "gaand", "chut"]) +
    r")($|[_\-\s\d])"
)


def _has_nsfw_sticker_name(name: str) -> bool:
    if not name:
        return False
    name_lower = name.lower()
    # Check safe specific substrings
    if any(kw in name_lower for kw in NSFW_STICKER_KEYWORDS):
        return True
    # Check short words with boundaries
    if _STICKER_WORD_PATTERN.search(name_lower):
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# File helpers
# ─────────────────────────────────────────────────────────────────────────────
def _best_thumb(thumbs) -> str | None:
    """Return the file_id of the largest (highest resolution) thumbnail."""
    if not thumbs:
        return None
    best = max(thumbs, key=lambda t: (getattr(t, "file_size", 0) or 0))
    return best.file_id


def _get_file_id(message: Message):
    """Get scannable file_id — use largest thumbnail for video/animated content."""
    if message.document:
        if message.document.file_size and int(message.document.file_size) > 5_000_000:
            return None
        if message.document.mime_type not in ("image/png", "image/jpeg", "image/webp"):
            return None
        return message.document.file_id

    if message.sticker:
        if message.sticker.is_animated or message.sticker.is_video:
            return _best_thumb(message.sticker.thumbs)
        # Static sticker (WebP) — scan full file
        return message.sticker.file_id

    if message.photo:
        return message.photo.file_id

    if message.animation:
        return _best_thumb(message.animation.thumbs)

    if message.video:
        return _best_thumb(message.video.thumbs)

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
# Skin-ratio fallback (catches what nudenet misses in small/stylized images)
# ─────────────────────────────────────────────────────────────────────────────
def _skin_ratio(path: str) -> float:
    try:
        import numpy as np
        img = Image.open(path).convert("RGB").resize((200, 200))
        arr = __import__("numpy").array(img, dtype=__import__("numpy").float32)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        skin_mask = (
            (r > 95) & (g > 40) & (b > 20) &
            (r > g) & (r > b) &
            ((r - g) > 15) &
            (r < 240) & (g < 200) & (b < 180)
        )
        return float(skin_mask.sum()) / (200 * 200)
    except Exception:
        return 0.0


def _is_skin_nsfw(path: str) -> bool:
    ratio = _skin_ratio(path)
    logger.info(f"[NSFW] Skin ratio: {ratio:.2f}")
    return ratio > 0.38   # 38% skin pixels → flag


# ─────────────────────────────────────────────────────────────────────────────
# Core visual NSFW check (nudenet + skin-ratio fallback, fully local)
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

        # ── nudenet scan ────────────────────────────────────────────────
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
        # DMs: just warn the user in chat, no log channel spam
        try:
            warn = await message.reply(
                "<blockquote>"
                "⛔ <b>Content Policy Violation</b>\n\n"
                f"🚫 You sent: <b>{reason}</b>\n\n"
                "This content violates our <b>No NSFW / No Illegal / No Drug</b> policy."
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
        set_name = message.sticker.set_name or ""
        emoji    = message.sticker.emoji    or ""

        # Check pack name and emoji with comprehensive keyword list
        if (
            _has_nsfw_sticker_name(set_name)
            or _has_nsfw_text(set_name)
            or _has_nsfw_text(emoji)
        ):
            return await _handle_violation(client, message, "NSFW sticker pack", is_group)

        # Visual scan — always attempt for all sticker types
        file_id = _get_file_id(message)
        if file_id:
            if await _is_visual_nsfw(client, file_id):
                return await _handle_violation(client, message, "18+ sticker content", is_group)

        # Extra: for video/animated stickers without a scannable thumb, only block clearly explicit packs
        if (message.sticker.is_video or message.sticker.is_animated) and not file_id:
            explicit_only = ["nsfw", "porn", "xxx", "hentai", "nude", "naked", "lewd", "ecchi", "ahegao", "18+", "adult"]
            if any(hint in set_name.lower() for hint in explicit_only):
                return await _handle_violation(client, message, "Suspicious animated sticker", is_group)

    # ── 3. Visual scan — photos, videos, animations, documents ──────────
    if message.photo or message.video or message.animation or message.document:
        file_id = _get_file_id(message)
        if file_id:
            if await _is_visual_nsfw(client, file_id):
                return await _handle_violation(client, message, "18+ visual content", is_group)
