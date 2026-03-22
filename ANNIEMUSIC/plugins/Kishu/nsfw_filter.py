import re
import os
import asyncio
import hashlib
import traceback

import httpx
from PIL import Image
from lexica import AsyncClient
from pyrogram import Client, filters, enums
from pyrogram.types import Message

from ANNIEMUSIC import app

# ─────────────────────────────────────────────────────────────────────────────
# Keyword lists (text / caption filter)
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

# In-memory NSFW hash cache (sha256 → True/False)
_nsfw_hash_cache: dict[str, bool] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _has_nsfw(text: str) -> bool:
    return bool(NSFW_PATTERN.search(text)) if text else False


def _get_file_id(message: Message):
    if message.document:
        if message.document.file_size and int(message.document.file_size) > 5245728:
            return None
        if message.document.mime_type not in ("image/png", "image/jpeg"):
            return None
        return message.document.file_id

    if message.sticker:
        if message.sticker.is_animated or message.sticker.is_video:
            thumbs = message.sticker.thumbs
            if not thumbs:
                return None
            return thumbs[0].file_id
        return message.sticker.file_id

    if message.photo:
        return message.photo.file_id

    if message.animation:
        thumbs = message.animation.thumbs
        if not thumbs:
            return None
        return thumbs[0].file_id

    if message.video:
        thumbs = message.video.thumbs
        if not thumbs:
            return None
        return thumbs[0].file_id

    return None


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(4096):
            h.update(chunk)
    return h.hexdigest()


def _convert_to_png(path: str):
    try:
        img = Image.open(path)
        img.save(path, "PNG")
    except Exception:
        pass


async def _upload_to_telegraph(path: str) -> str | None:
    """Upload a file to graph.org and return its public URL."""
    try:
        async with httpx.AsyncClient(http2=True, timeout=20) as client:
            resp = await client.post(
                "https://graph.org/upload",
                files={"file": open(path, "rb")},
            )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if "error" in data:
            return None
        if isinstance(data, list) and data:
            return "https://graph.org" + data[0]["src"]
    except Exception:
        traceback.print_exc()
    finally:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
    return None


async def _lexica_check(img_url: str) -> bool | None:
    """Return True if NSFW, False if safe, None on API error."""
    try:
        client = AsyncClient()
        result = await client.AntiNsfw(img_url)
        await client.close()
        if result and result.get("code") == 2:
            sfw = result.get("content", {}).get("sfw")
            if sfw is True:
                return False
            if sfw is False:
                return True
    except Exception:
        traceback.print_exc()
    return None


async def _is_visual_nsfw(telegram_client: Client, file_id: str) -> bool:
    """Download media, upload to graph.org, check with Lexica AntiNsfw."""
    path = None
    try:
        path = await telegram_client.download_media(file_id)
        if not path or not os.path.exists(path):
            return False

        file_hash = _file_hash(path)
        if file_hash in _nsfw_hash_cache:
            if os.path.exists(path):
                os.remove(path)
            return _nsfw_hash_cache[file_hash]

        # Convert jpg/jpeg/webp → PNG for cleaner upload
        if any(path.endswith(ext) for ext in ("jpg", "jpeg", "webp")):
            _convert_to_png(path)

        # _upload_to_telegraph removes the file in its finally block
        img_url = await _upload_to_telegraph(path)
        path = None  # file already removed by upload function
        if not img_url:
            return False

        result = await _lexica_check(img_url)
        if result is None:
            return False

        _nsfw_hash_cache[file_hash] = result
        return result

    except Exception:
        traceback.print_exc()
        return False
    finally:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


async def _try_delete(message: Message, reason: str):
    try:
        await message.delete()
    except Exception:
        pass
    try:
        alert = await message.chat.send_message(
            f"⛔ **Content Removed**\n"
            f"A message containing **{reason}** has been automatically deleted.\n"
            f"This group has a strict **No NSFW / No Illegal Content** policy."
        )
        await asyncio.sleep(8)
        await alert.delete()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Main handler — always ON, no toggle
# ─────────────────────────────────────────────────────────────────────────────
@app.on_message(~filters.bot, group=-5)
async def nsfw_guard(client: Client, message: Message):
    if not message or not message.chat:
        return

    is_group = message.chat.type in (
        enums.ChatType.GROUP,
        enums.ChatType.SUPERGROUP,
    )

    # ── 1. Text / caption keyword check ─────────────────────────────────
    text = message.text or message.caption or ""
    if _has_nsfw(text):
        return await _try_delete(message, "18+ / illegal / drug-related content")

    # ── 2. Stickers ──────────────────────────────────────────────────────
    if message.sticker:
        if is_group:
            return await _try_delete(message, "sticker (not allowed in this group)")
        # DM: keyword check first, then visual scan
        set_name = (message.sticker.set_name or "").lower()
        emoji    = (message.sticker.emoji    or "").lower()
        kws = ["nsfw", "adult", "sex", "porn", "nude", "lewd", "hentai",
               "xxx", "erotic", "18", "drug", "weed"]
        if any(k in set_name for k in kws) or _has_nsfw(emoji) or _has_nsfw(set_name):
            return await _try_delete(message, "NSFW sticker pack")
        file_id = _get_file_id(message)
        if file_id:
            if await _is_visual_nsfw(client, file_id):
                return await _try_delete(message, "18+ sticker")

    # ── 3. Visual scan — photos, videos, animations, documents ───────────
    if message.photo or message.video or message.animation or message.document:
        file_id = _get_file_id(message)
        if file_id:
            if await _is_visual_nsfw(client, file_id):
                return await _try_delete(message, "18+ visual content")
