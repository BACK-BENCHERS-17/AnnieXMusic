import re
import os
import io
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
# NudeDetector setup
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

_THRESHOLD_EXPOSED = 0.50
_THRESHOLD_COVERED = 0.65
_SKIN_RATIO_FALLBACK = 0.48

_nsfw_hash_cache: dict[str, bool] = {}

# ─────────────────────────────────────────────────────────────────────────────
# OCR setup — extract text from images to detect drug/NSFW text in photos
# ─────────────────────────────────────────────────────────────────────────────
_OCR_OK = False
try:
    import pytesseract
    _tess_bin = "/home/runner/.nix-profile/bin/tesseract"
    if os.path.isfile(_tess_bin):
        pytesseract.pytesseract.tesseract_cmd = _tess_bin
    _OCR_OK = True
    logger.info("pytesseract OCR loaded.")
except Exception:
    logger.warning("pytesseract not available — OCR-based image text scan disabled.")

def _ocr_text_from_image(path: str) -> str:
    """Extract visible text from an image file using OCR."""
    if not _OCR_OK:
        return ""
    try:
        import pytesseract
        img = Image.open(path).convert("RGB")
        img = img.resize((800, 800), Image.LANCZOS)
        text = pytesseract.image_to_string(img, timeout=5)
        return text.strip()
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Keywords — explicit / illegal content + drugs (English + Hindi + Urdu)
# ─────────────────────────────────────────────────────────────────────────────
NSFW_KEYWORDS = [
    # ── 18+ / Adult content ──────────────────────────────────────────────────
    "nude", "naked", "porn", "pornography", "xxx", "hentai",
    "blowjob", "handjob", "masturbat", "orgasm", "erotic",
    "nudes", "nsfw", "onlyfans", "camgirl", "cam girl", "sexting",
    "intercourse", "x-rated", "adult content", "lewd",
    "pedophil", "child abuse", "cp video", "child porn",
    "vagina", "penis", "nipple", "nipples", "pussy",
    "boobs", "boob", "tits", "tit", "ass",
    "sex tape", "sex video", "nude video", "naked video",
    "hot girl nude", "hot girl naked",
    "rape", "molest",
    # ── Drug keywords — English ───────────────────────────────────────────────
    "cocaine", "heroin", "methamphetamine", "meth crystal", "crystal meth",
    "fentanyl", "mdma pill", "ecstasy pill", "lsd blotter",
    "opium den", "hashish oil", "ketamine powder",
    "narcotics", "drug dealer", "drug lord",
    "darkweb", "dark web",
    "trafficking", "traffick",
    "crack cocaine", "buy cocaine", "sell cocaine",
    "smack drug", "speed drug", "ice drug",
    "drug deal", "buy drugs", "sell drugs",
    "drug supply", "drug pack",
    "coke powder", "snow drug",
    "opioid", "overdose",
    "pill press", "drug lab",
    # ── Drug keywords — Hindi / Urdu / Street slang ────────────────────────
    "charas", "nasha", "afeem", "afim",
    "smack nasha", "herokeen", "hero in",
    "ganja deal", "bhaang deal",
    "smackiya", "nashedi",
    "dava bech", "nasha bech", "drug bech",
    "nasha kharid", "drug kharid",
    "whitener nasha", "solution nasha",
    "sulfa nasha", "nashe ki goli",
    "nasha pack", "nasha supli",
    # ── Hindi / Urdu abusive / explicit ──────────────────────────────────────
    "chut", "lund", "gaand", "randi", "madarchod", "behenchod",
    "bhosdike", "lawda", "lauda", "chutiya", "gandu",
    "nangi", "nanga", "nangai", "bhosad", "harami",
    "maa ki aankh", "bhen ke lode", "teri maa ki",
    "chudai", "chodo", "chod do", "chudwa",
    "ladki nangi", "aurat nangi",
]

NSFW_PATTERN = re.compile(
    r"(?i)\b(" + "|".join(re.escape(k.strip()) for k in NSFW_KEYWORDS) + r")\b"
)

# ─────────────────────────────────────────────────────────────────────────────
# Drug-specific keyword set for OCR text in images
# These are stricter since they only fire from extracted image text
# ─────────────────────────────────────────────────────────────────────────────
_DRUG_KEYWORDS_STRICT = [
    "cocaine", "heroin", "methamphetamine", "crystal meth", "fentanyl",
    "mdma", "ecstasy", "lsd", "ketamine", "crack cocaine",
    "opioid", "narcotics", "drug deal", "buy drugs", "sell drugs",
    "drug lord", "drug dealer", "overdose", "dark web", "darkweb",
    "charas", "afeem", "nasha bech", "drug bech", "nasha kharid",
    "cocaine for sale", "heroin for sale", "drugs for sale",
    "drug supply", "smack drug",
]
_DRUG_OCR_PATTERN = re.compile(
    r"(?i)\b(" + "|".join(re.escape(k) for k in _DRUG_KEYWORDS_STRICT) + r")\b"
)


def _has_nsfw_text(text: str) -> bool:
    return bool(NSFW_PATTERN.search(text)) if text else False


def _has_drug_text(text: str) -> bool:
    """Check for drug-promotion specific text (used for OCR image scan)."""
    return bool(_DRUG_OCR_PATTERN.search(text)) if text else False


# ─────────────────────────────────────────────────────────────────────────────
# Sticker pack / GIF pack name keywords — NSFW + Drug packs
# ─────────────────────────────────────────────────────────────────────────────
NSFW_STICKER_KEYWORDS = [
    # Adult/NSFW sticker packs
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
    # Drug sticker packs
    "cocaine", "heroin", "drug", "drugs", "weed_deal",
    "drugpack", "nashapack", "cocainesticker",
    "dealer", "highlife", "druglife", "drugseller",
    "charaspack", "ganjadealer",
]

_STICKER_WORD_PATTERN = re.compile(
    r"(?i)(^|[_\-\s])(" +
    "|".join(re.escape(w) for w in [
        "sex", "sexy", "fuck", "erotic", "horny",
        "nude", "slut", "whore", "lund", "gaand", "chut",
        "drug", "cocaine", "heroin", "dealer", "nasha",
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
        size = getattr(message.animation, "file_size", None) or 0
        if size <= 5_000_000:
            return message.animation.file_id
        return _best_thumb(message.animation.thumbs)
    if message.video:
        return _best_thumb(message.video.thumbs)
    return None


def _get_video_thumb_file_id(message: Message) -> str | None:
    """Get the best thumbnail file_id for a video."""
    if message.video and message.video.thumbs:
        return _best_thumb(message.video.thumbs)
    return None


def _collect_all_text(message: Message) -> str:
    """Collect ALL text associated with a message — text, caption, file name, forward info."""
    parts = []
    if message.text:
        parts.append(message.text)
    if message.caption:
        parts.append(message.caption)
    if message.document and message.document.file_name:
        parts.append(message.document.file_name)
    if message.video and message.video.file_name:
        parts.append(message.video.file_name)
    if message.animation and message.animation.file_name:
        parts.append(message.animation.file_name)
    if message.forward_from_chat and message.forward_from_chat.title:
        parts.append(message.forward_from_chat.title)
    if message.forward_sender_name:
        parts.append(message.forward_sender_name)
    return " ".join(parts)


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
# Core visual NSFW check — NudeNet + skin ratio + OCR drug text
# ─────────────────────────────────────────────────────────────────────────────
async def _is_visual_nsfw(tg_client: Client, file_id: str) -> tuple[bool, str]:
    """
    Returns (is_nsfw, reason).
    Checks:
    1. NudeNet AI — adult/18+ body detection
    2. Skin ratio fallback — high skin exposure
    3. OCR text scan — drug/illegal text visible in image
    """
    if not _NUDE_OK:
        return False, ""
    path = None
    png_path = None
    try:
        path = await tg_client.download_media(file_id)
        if not path or not os.path.exists(path):
            return False, ""
        logger.info(f"[NSFW] Downloaded: {path} ({os.path.getsize(path)} bytes)")

        file_hash = _file_hash(path)
        if file_hash in _nsfw_hash_cache:
            cached = _nsfw_hash_cache[file_hash]
            return cached, ("18+ visual content" if cached else "")

        png_path = _to_png(path)

        # ── Step 1: NudeNet adult content detection ───────────────────────
        detections = _detector.detect(png_path)
        logger.info(f"[NSFW] Detections: {detections}")
        is_nsfw = any(
            (det.get("class") in _NSFW_EXPOSED and det.get("score", 0) >= _THRESHOLD_EXPOSED)
            or (det.get("class") in _NSFW_COVERED and det.get("score", 0) >= _THRESHOLD_COVERED)
            for det in detections
        )
        reason = "18+ adult content detected in image" if is_nsfw else ""

        # ── Step 2: Skin ratio fallback ───────────────────────────────────
        if not is_nsfw:
            try:
                with open(png_path or path, "rb") as f:
                    img_bytes = f.read()
                ratio = _skin_ratio(img_bytes)
                logger.info(f"[NSFW] Skin ratio: {ratio:.2f}")
                if ratio >= _SKIN_RATIO_FALLBACK:
                    is_nsfw = True
                    reason = "Excessive skin exposure detected in image"
                    logger.info("[NSFW] Flagged by skin ratio")
            except Exception:
                pass

        # ── Step 3: OCR — detect drug/illegal text in image ───────────────
        if not is_nsfw and _OCR_OK:
            try:
                ocr_text = _ocr_text_from_image(png_path or path)
                if ocr_text:
                    logger.info(f"[NSFW] OCR text: {ocr_text[:200]}")
                    if _has_drug_text(ocr_text):
                        is_nsfw = True
                        reason = "Drug-related text found in image"
                        logger.info("[NSFW] Flagged by OCR drug text detection")
                    elif _has_nsfw_text(ocr_text):
                        is_nsfw = True
                        reason = "Explicit content text found in image"
                        logger.info("[NSFW] Flagged by OCR NSFW text detection")
            except Exception:
                logger.warning(f"[NSFW] OCR scan failed: {traceback.format_exc()}")

        _nsfw_hash_cache[file_hash] = is_nsfw
        logger.info(f"[NSFW] Final result: {'NSFW' if is_nsfw else 'SAFE'} | {reason}")
        return is_nsfw, reason

    except Exception:
        logger.error(f"[NSFW] Visual scan error:\n{traceback.format_exc()}")
        return False, ""
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

    # ── 1. All text associated with message (text, caption, filename, forward) ─
    all_text = _collect_all_text(message)
    if all_text and _has_nsfw_text(all_text):
        return await _handle_violation(
            client, message, "Explicit / drug-related content in message text", is_group
        )

    # ── 2. Stickers ──────────────────────────────────────────────────────────
    if message.sticker:
        set_name = message.sticker.set_name or ""
        emoji    = message.sticker.emoji    or ""
        if (
            _has_nsfw_sticker_name(set_name)
            or _has_nsfw_text(set_name)
            or _has_nsfw_text(emoji)
        ):
            return await _handle_violation(client, message, "NSFW / drug-related sticker pack", is_group)
        file_id = _get_file_id(message)
        if file_id:
            is_bad, reason = await _is_visual_nsfw(client, file_id)
            if is_bad:
                return await _handle_violation(client, message, reason or "18+ sticker content", is_group)
        if (message.sticker.is_video or message.sticker.is_animated) and not file_id:
            explicit_only = [
                "nsfw", "porn", "xxx", "hentai", "nude", "naked", "lewd", "ecchi", "ahegao",
                "cocaine", "heroin", "drug", "drugs",
            ]
            if any(hint in set_name.lower() for hint in explicit_only):
                return await _handle_violation(client, message, "Explicit animated sticker", is_group)

    # ── 3. Photos ─────────────────────────────────────────────────────────────
    if message.photo:
        file_id = _get_file_id(message)
        if file_id:
            is_bad, reason = await _is_visual_nsfw(client, file_id)
            if is_bad:
                return await _handle_violation(client, message, reason or "18+ photo content", is_group)

    # ── 4. GIFs / Animations ──────────────────────────────────────────────────
    if message.animation:
        anim = message.animation
        anim_name = (getattr(anim, "file_name", "") or "").lower()
        if _has_nsfw_text(anim_name):
            return await _handle_violation(client, message, "Explicit GIF filename", is_group)
        file_id = _get_file_id(message)
        if file_id:
            is_bad, reason = await _is_visual_nsfw(client, file_id)
            if is_bad:
                return await _handle_violation(client, message, reason or "18+ GIF content", is_group)

    # ── 5. Videos ─────────────────────────────────────────────────────────────
    if message.video:
        vid = message.video
        vid_name = (getattr(vid, "file_name", "") or "").lower()
        if _has_nsfw_text(vid_name):
            return await _handle_violation(client, message, "Explicit video filename", is_group)
        thumb_file_id = _get_video_thumb_file_id(message)
        if thumb_file_id:
            is_bad, reason = await _is_visual_nsfw(client, thumb_file_id)
            if is_bad:
                return await _handle_violation(client, message, reason or "18+ video content", is_group)

    # ── 6. Documents (images/videos sent as files) ────────────────────────────
    if message.document:
        doc = message.document
        doc_name = (doc.file_name or "").lower()
        if _has_nsfw_text(doc_name):
            return await _handle_violation(client, message, "Explicit document filename", is_group)
        file_id = _get_file_id(message)
        if file_id:
            is_bad, reason = await _is_visual_nsfw(client, file_id)
            if is_bad:
                return await _handle_violation(client, message, reason or "18+ document content", is_group)

    # ── 7. Voice notes / Audio — check caption only (already done above) ──────
    # Caption check was already covered in Step 1 (all_text)
