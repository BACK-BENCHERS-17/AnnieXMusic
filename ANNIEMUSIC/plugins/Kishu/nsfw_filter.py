import re
import asyncio

from pyrogram import Client, filters, enums
from pyrogram.types import Message

from ANNIEMUSIC import app

NSFW_KEYWORDS = [
    # 18+ / adult
    "sex", "sexy", "nude", "naked", "porn", "pornography", "xxx", "adult",
    "hentai", "boobs", "boob", "tits", "tit", "nipple", "nipples", "pussy",
    "vagina", "penis", "dick", "cock", "ass", "anal", "blowjob", "handjob",
    "masturbat", "orgasm", "erotic", "nudes", "nsfw", "onlyfans", "escort",
    "prostitut", "rape", "molest", "harassment", "slutty", "slut", "bitch",
    "whore", "stripper", "strip club", "camgirl", "cam girl", "sexting",
    "sexual", "intercourse", "fornication", "lust", "lusty", "horny",
    "18+", "x-rated", "rated x", "adult content", "explicit", "lewd",
    # drugs / illegal
    "drug", "drugs", "cocaine", "heroin", "meth", "methamphetamine", "lsd",
    "marijuana", "weed", "ganja", "crack", "mdma", "ecstasy", "opium",
    "cannabis", "hashish", "hash", "smuggl", "traffick", "terror", "terrorist",
    "bomb", "explosive", "weapon", "murder", "kill", "suicide", "pedophil",
    "child abuse", "cp ", " cp", "illegal", "darkweb", "dark web",
    "ketamine", "xanax abuse", "overdose", "drug dealer", "narcotics",
    # urdu/hindi slang (romanized)
    "chut", "lund", "gaand", "bur", "randi", "harami", "maa ki", "behen ki",
    "bhosad", "madarchod", "behenchod", "bhosdike", "lawda", "lauda",
    "chutiya", "gandu", "saala", "sexy video", "sexy photo", "sexy pic",
    "nangi", "nanga", "nangai", "jism", "jisam",
]

NSFW_PATTERN = re.compile(
    r"(?i)\b(" + "|".join(re.escape(kw.strip()) for kw in NSFW_KEYWORDS) + r")\b"
)


def _has_nsfw(text: str) -> bool:
    if not text:
        return False
    return bool(NSFW_PATTERN.search(text))


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

    # ── 1. Check plain text / commands ──────────────────────────────────
    text = (
        message.text
        or message.caption
        or ""
    )
    if _has_nsfw(text):
        return await _try_delete(message, "18+ / illegal / drug-related content")

    # ── 2. Check stickers ────────────────────────────────────────────────
    if message.sticker:
        sticker = message.sticker
        set_name = (sticker.set_name or "").lower()
        emoji    = (sticker.emoji or "").lower()
        nsfw_sticker_keywords = [
            "nsfw", "adult", "sex", "porn", "nude", "lewd", "hentai",
            "xxx", "erotic", "18", "drug", "weed",
        ]
        if any(k in set_name for k in nsfw_sticker_keywords):
            return await _try_delete(message, "NSFW sticker pack")
        if _has_nsfw(emoji) or _has_nsfw(set_name):
            return await _try_delete(message, "NSFW sticker")

    # ── 3. Check photos / videos / documents by caption ─────────────────
    if message.photo or message.video or message.document or message.animation:
        caption = message.caption or ""
        if _has_nsfw(caption):
            return await _try_delete(message, "NSFW media caption")
