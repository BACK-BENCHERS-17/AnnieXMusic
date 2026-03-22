import re
import os
import asyncio
import traceback

from pyrogram import Client, filters, enums
from pyrogram.types import Message

from ANNIEMUSIC import app

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
    r"(?i)\b(" + "|".join(re.escape(kw.strip()) for kw in NSFW_KEYWORDS) + r")\b"
)

NSFW_EXPOSED_CLASSES = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "ANUS_EXPOSED",
    "BUTTOCKS_EXPOSED",
}

try:
    from nudenet import NudeDetector
    _detector = NudeDetector()
    _NUDENET_OK = True
except Exception:
    _detector = None
    _NUDENET_OK = False


def _has_nsfw(text: str) -> bool:
    if not text:
        return False
    return bool(NSFW_PATTERN.search(text))


def _get_file_id(message: Message):
    if message.photo:
        return message.photo.file_id
    if message.sticker:
        return message.sticker.file_id
    if message.animation:
        return message.animation.file_id
    if message.video:
        return message.video.file_id
    if message.document:
        return message.document.file_id
    return None


async def _is_visual_nsfw(client: Client, file_id: str) -> bool:
    if not _NUDENET_OK or not file_id:
        return False
    file_path = None
    try:
        file_path = await client.download_media(file_id)
        if not file_path or not os.path.exists(file_path):
            return False
        detections = _detector.detect(file_path)
        for det in detections:
            cls   = det.get("class", "")
            score = det.get("score", 0)
            if cls in NSFW_EXPOSED_CLASSES and score >= 0.5:
                return True
        return False
    except Exception:
        traceback.print_exc()
        return False
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
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


@app.on_message(
    ~filters.bot,
    group=-5,
)
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

    # ── 2. Stickers — all blocked in groups; keyword check in DMs ───────
    if message.sticker:
        if is_group:
            return await _try_delete(message, "sticker (not allowed in this group)")
        else:
            set_name = (message.sticker.set_name or "").lower()
            emoji    = (message.sticker.emoji    or "").lower()
            nsfw_sticker_kws = [
                "nsfw", "adult", "sex", "porn", "nude", "lewd", "hentai",
                "xxx", "erotic", "18", "drug", "weed",
            ]
            if any(k in set_name for k in nsfw_sticker_kws):
                return await _try_delete(message, "NSFW sticker pack")
            if _has_nsfw(emoji) or _has_nsfw(set_name):
                return await _try_delete(message, "NSFW sticker")

    # ── 3. Visual NSFW scan — photos, videos, animations, documents ──────
    if message.photo or message.video or message.animation or message.document:
        file_id = _get_file_id(message)
        if file_id:
            unsafe = await _is_visual_nsfw(client, file_id)
            if unsafe:
                return await _try_delete(message, "18+ visual content")
