import re
import io
from typing import Optional

BAD_KEYWORDS = [
    "porn", "pornhub", "xvideos", "xnxx", "xxx", "sex", "nude", "naked",
    "18+", "adult", "hentai", "nsfw", "erotic", "explicit",
    "blowjob", "handjob", "boobs", "pussy", "dick", "cock",
    "sexy video", "hot girl", "hot video", "bf video", "gf video",
    "rape", "mms", "viral sex", "blue film", "b grade",
    "drug", "drugs", "cocaine", "heroin", "weed", "ganja", "marijuana",
    "meth", "opium", "charas", "smack", "narcotics", "afeem",
    "mdma", "lsd", "ecstasy", "crack", "hash", "bhang",
    "smuggling", "trafficking",
]

_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in BAD_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def is_bad_text(text: str) -> Optional[str]:
    if not text:
        return None
    match = _PATTERN.search(text)
    if match:
        return match.group(0)
    return None


def _skin_ratio(image_bytes: bytes) -> float:
    try:
        from PIL import Image
        import numpy as np

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((200, 200))
        arr = np.array(img, dtype=np.float32)

        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

        skin_mask = (
            (r > 95) & (g > 40) & (b > 20) &
            (r > g) & (r > b) &
            ((r - g) > 15) &
            (r < 240) & (g < 200) & (b < 180)
        )

        ratio = float(skin_mask.sum()) / (200 * 200)
        return ratio
    except Exception:
        return 0.0


def analyze_image_bytes(image_bytes: bytes) -> bool:
    ratio = _skin_ratio(image_bytes)
    return ratio > 0.45
