import re
import httpx
from typing import Optional

BAD_KEYWORDS = [
    "porn", "pornhub", "xvideos", "xnxx", "xxx", "sex", "nude", "naked",
    "18+", "adult", "hentai", "nsfw", "erotic", "explicit",
    "blowjob", "handjob", "boobs", "pussy", "dick", "cock", "ass",
    "sexy", "hot girl", "hot video", "bf video", "gf video",
    "rape", "mms", "viral sex", "blue film", "b grade",
    "drug", "drugs", "cocaine", "heroin", "weed", "ganja", "marijuana",
    "meth", "opium", "charas", "smack", "narcotics", "afeem",
    "mdma", "lsd", "ecstasy", "crack", "hash", "bhang",
    "smuggling", "trafficking", "darkweb", "darknet",
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


async def analyze_image_url(image_url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.deepai.org/api/nsfw-detector",
                data={"image": image_url},
                headers={"api-key": "quickstart-QUdJIGlzIGNvbWluZy4uLi4K"},
            )
            if resp.status_code != 200:
                return False
            data = resp.json()
            output = data.get("output", {})
            nsfw_score = output.get("nsfw_score", 0)
            if isinstance(nsfw_score, (int, float)) and nsfw_score > 0.65:
                return True
    except Exception:
        pass
    return False


async def analyze_image_bytes(image_bytes: bytes, filename: str = "image.jpg") -> bool:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.deepai.org/api/nsfw-detector",
                files={"image": (filename, image_bytes, "image/jpeg")},
                headers={"api-key": "quickstart-QUdJIGlzIGNvbWluZy4uLi4K"},
            )
            if resp.status_code != 200:
                return False
            data = resp.json()
            output = data.get("output", {})
            nsfw_score = output.get("nsfw_score", 0)
            if isinstance(nsfw_score, (int, float)) and nsfw_score > 0.65:
                return True
    except Exception:
        pass
    return False
