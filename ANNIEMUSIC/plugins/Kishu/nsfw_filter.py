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
from ANNIEMUSIC.utils.database import is_content_guard_on, is_global_nsfw_off
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

# ── Official NudeNet all_labels (18 classes from PyPI docs) ──────────────────
# Reference: https://pypi.org/project/nudenet/
# Only EXPOSED classes are used for NSFW detection.
# COVERED classes (FEMALE_BREAST_COVERED, BUTTOCKS_COVERED, etc.) are NOT
# NSFW by themselves — they cause massive false positives on swimwear,
# anime/cartoon art, and normal stickers. Official examples only check EXPOSED.

_NSFW_EXPOSED = {
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "ANUS_EXPOSED",
    "BUTTOCKS_EXPOSED",
}
# COVERED classes intentionally NOT used — per official NudeNet usage docs,
# covered content is not NSFW. Causes false positives on normal stickers.

# Standard threshold per official NudeNet community examples
_THRESHOLD_EXPOSED = 0.60        # for photos/videos/GIFs
_THRESHOLD_STICKER_EXPOSED = 0.70  # stricter for stickers (anime/cartoon art)
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
        allowed_mime = (
            "image/png", "image/jpeg", "image/webp", "image/gif",
            "video/mp4", "video/webm",
        )
        if message.document.mime_type not in allowed_mime:
            return None
        return message.document.file_id
    if message.sticker:
        if message.sticker.is_animated:
            # TGS (Lottie) — can't decode frames, use thumbnail only
            return _best_thumb(message.sticker.thumbs)
        if message.sticker.is_video:
            # WebM video sticker — download actual file for frame scan (≤5 MB)
            size = getattr(message.sticker, "file_size", None) or 0
            if size <= 5_000_000:
                return message.sticker.file_id
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
        # Return actual video file_id if small enough for frame extraction
        size = getattr(message.video, "file_size", None) or 0
        if size <= 10_000_000:
            return message.video.file_id
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
            det.get("class") in _NSFW_EXPOSED and det.get("score", 0) >= _THRESHOLD_EXPOSED
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
# Frame extraction — images / GIFs (PIL) / videos & webm (ffmpeg)
# ─────────────────────────────────────────────────────────────────────────────
_VIDEO_EXTS = {".mp4", ".webm", ".avi", ".mov", ".mkv", ".3gp", ".flv"}


def _extract_video_frames_sync(path: str, max_frames: int = 6) -> list[str]:
    """Extract evenly-spaced frames from a video/webm file using ffmpeg."""
    import subprocess
    import glob as _glob
    frames = []
    out_base = path + "_vf"
    try:
        cmd = [
            "ffmpeg", "-y", "-i", path,
            "-vf", "fps=1,scale=640:-2",
            "-vframes", str(max_frames),
            f"{out_base}%03d.png",
        ]
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        frames = sorted(_glob.glob(f"{out_base}*.png"))[:max_frames]
        logger.info(f"[NSFW] Extracted {len(frames)} video frames from {path}")
    except Exception as e:
        logger.warning(f"[NSFW] ffmpeg frame extract failed: {e}")
    return frames


def _extract_frames_from_path(path: str, max_frames: int = 6) -> list[str]:
    """
    Smart frame extractor.
    - Single image → 1 PNG
    - GIF / APNG / multi-frame → up to max_frames evenly spaced PNGs
    - Video / WebM → ffmpeg extracts up to max_frames PNGs
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in _VIDEO_EXTS:
        return _extract_video_frames_sync(path, max_frames)

    frames = []
    try:
        img = Image.open(path)
        n_frames = getattr(img, "n_frames", 1)
        if n_frames == 1:
            png = path + "_chk.png"
            img.convert("RGB").save(png, "PNG")
            return [png]
        # Multi-frame (GIF, APNG, etc.)
        step = max(1, n_frames // max_frames)
        for i in range(0, n_frames, step):
            if len(frames) >= max_frames:
                break
            try:
                img.seek(i)
                fp = f"{path}_frame{i}.png"
                img.convert("RGB").save(fp, "PNG")
                frames.append(fp)
            except EOFError:
                break
        logger.info(f"[NSFW] Extracted {len(frames)} GIF frames from {path}")
    except Exception as e:
        logger.warning(f"[NSFW] Frame extract (PIL) failed: {e} — fallback to _to_png")
        fallback = _to_png(path)
        if fallback and os.path.exists(fallback):
            frames = [fallback]
    return frames


def _check_frames_nudenet(frame_paths: list[str], sticker_mode: bool = False) -> tuple[bool, str]:
    """Run NudeNet on a list of frame PNGs. Returns (is_nsfw, reason) on first hit.

    Per official NudeNet docs (pypi.org/project/nudenet), only EXPOSED classes
    are checked. COVERED classes are intentionally skipped — they are NOT NSFW
    and cause false positives on normal stickers, anime, swimwear, etc.

    sticker_mode=True uses a stricter threshold (0.70 vs 0.60) to further
    reduce false positives on cartoon/anime sticker art.
    """
    threshold = _THRESHOLD_STICKER_EXPOSED if sticker_mode else _THRESHOLD_EXPOSED
    for fp in frame_paths:
        if not os.path.exists(fp):
            continue
        try:
            detections = _detector.detect(fp)
            logger.info(f"[NSFW] Frame {fp} detections: {detections}")
            for det in detections:
                cls = det.get("class", "")
                score = det.get("score", 0)
                if cls in _NSFW_EXPOSED and score >= threshold:
                    return True, f"18+ explicit content detected ({cls}: {score:.2f})"
        except Exception:
            logger.warning(f"[NSFW] NudeNet failed on frame {fp}")
    return False, ""


# ─────────────────────────────────────────────────────────────────────────────
# Core visual NSFW check — supports images, GIFs, videos, video stickers
# ─────────────────────────────────────────────────────────────────────────────
async def _is_visual_nsfw(tg_client: Client, file_id: str, sticker_mode: bool = False) -> tuple[bool, str]:
    """
    Returns (is_nsfw, reason).
    Checks all media types:
    - Images        → NudeNet + skin ratio + OCR
    - GIFs          → NudeNet on multiple extracted frames
    - Videos / WebM → NudeNet on ffmpeg-extracted frames
    - Video stickers → same as video

    sticker_mode=True applies stricter thresholds and only checks fully exposed
    content — prevents false positives on anime/cartoon stickers.
    """
    if not _NUDE_OK:
        return False, ""
    path = None
    extracted_frames: list[str] = []
    try:
        path = await tg_client.download_media(file_id)
        if not path or not os.path.exists(path):
            return False, ""
        logger.info(f"[NSFW] Downloaded: {path} ({os.path.getsize(path)} bytes)")

        file_hash = _file_hash(path)
        if file_hash in _nsfw_hash_cache:
            cached = _nsfw_hash_cache[file_hash]
            return cached, ("18+ visual content (cached)" if cached else "")

        # ── Extract frames based on media type ───────────────────────────
        extracted_frames = await asyncio.get_event_loop().run_in_executor(
            None, _extract_frames_from_path, path
        )
        if not extracted_frames:
            logger.warning(f"[NSFW] No frames extracted from {path}")
            _nsfw_hash_cache[file_hash] = False
            return False, ""

        # ── Step 1: NudeNet on all frames ────────────────────────────────
        # NudeNet is the authoritative check. If it ran successfully and found
        # nothing, the content is SAFE — we do NOT override with skin ratio.
        # Skin ratio causes massive false positives on anime/cartoon/portrait
        # stickers and thumbnails that have skin-colored art.
        is_nsfw, reason = await asyncio.get_event_loop().run_in_executor(
            None, _check_frames_nudenet, extracted_frames, sticker_mode
        )

        # ── Step 2: OCR — drug/illegal text in first frame ───────────────
        if not is_nsfw and _OCR_OK:
            try:
                ocr_text = _ocr_text_from_image(extracted_frames[0])
                if ocr_text:
                    logger.info(f"[NSFW] OCR text: {ocr_text[:200]}")
                    if _has_drug_text(ocr_text):
                        is_nsfw = True
                        reason = "Drug-related text found in content"
                        logger.info("[NSFW] Flagged by OCR drug text")
                    elif _has_nsfw_text(ocr_text):
                        is_nsfw = True
                        reason = "Explicit content text found in content"
                        logger.info("[NSFW] Flagged by OCR NSFW text")
            except Exception:
                logger.warning(f"[NSFW] OCR scan failed: {traceback.format_exc()}")

        _nsfw_hash_cache[file_hash] = is_nsfw
        logger.info(f"[NSFW] Final result: {'NSFW' if is_nsfw else 'SAFE'} | {reason}")
        return is_nsfw, reason

    except Exception:
        logger.error(f"[NSFW] Visual scan error:\n{traceback.format_exc()}")
        return False, ""
    finally:
        cleanup = ([path] if path else []) + extracted_frames
        for p in cleanup:
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

    # Skip entirely if globally disabled by bot owner
    try:
        if await is_global_nsfw_off():
            return
    except Exception:
        pass

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
            is_bad, reason = await _is_visual_nsfw(client, file_id, sticker_mode=True)
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
        # _get_file_id returns actual video (≤10MB) for frame scan, else thumbnail
        file_id = _get_file_id(message)
        if not file_id:
            # Fallback: check thumbnail only if actual video is too large
            file_id = _get_video_thumb_file_id(message)
        if file_id:
            is_bad, reason = await _is_visual_nsfw(client, file_id)
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
