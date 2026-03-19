import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch
from config import YOUTUBE_IMG_URL, BOT_USERNAME
from ANNIEMUSIC.core.dir import CACHE_DIR

W, H = 1280, 720

CYAN     = (0, 220, 255)
WHITE    = (255, 255, 255)
YELLOW   = (255, 215, 0)
SOFT_BG  = (10, 8, 20)

_FONT_BOLD = "ANNIEMUSIC/assets/thumb/font2.ttf"
_FONT_REG  = "ANNIEMUSIC/assets/thumb/font.ttf"


def _load_fonts():
    try:
        return (
            ImageFont.truetype(_FONT_BOLD, 38),   # [0] title
            ImageFont.truetype(_FONT_REG,  20),   # [1] meta info
            ImageFont.truetype(_FONT_BOLD, 19),   # [2] dev credit / watermark
            ImageFont.truetype(_FONT_REG,  17),   # [3] small
        )
    except OSError:
        d = ImageFont.load_default()
        return d, d, d, d


def trim_to_width(text, font, max_w):
    if font.getlength(text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        if font.getlength(text[:i] + "…") <= max_w:
            return text[:i] + "…"
    return "…"


def _circle_avatar(img, size):
    img = img.resize((size, size)).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img


async def get_thumb(videoid: str) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_v10.png")
    if os.path.exists(cache_path):
        return cache_path

    # ── Fetch YouTube metadata ──────────────────────────────────────────────
    try:
        results_data = await VideosSearch(
            f"https://www.youtube.com/watch?v={videoid}", limit=1
        ).next()
        data      = (results_data.get("result") or [{}])[0]
        title     = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
        thumbnail = (data.get("thumbnails") or [{}])[0].get("url") or YOUTUBE_IMG_URL
        duration  = data.get("duration")
        views     = (data.get("viewCount") or {}).get("short") or "Unknown"
    except Exception:
        title, thumbnail, duration, views = (
            "Unsupported Title", YOUTUBE_IMG_URL, None, "Unknown"
        )

    is_live      = not duration or str(duration).strip().lower() in {"", "live", "live now"}
    duration_txt = "LIVE" if is_live else (duration or "—")

    # ── Download thumbnail ──────────────────────────────────────────────────
    thumb_path = os.path.join(CACHE_DIR, f"raw_{videoid}.png")
    downloaded = False
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(thumbnail) as resp:
                if resp.status == 200:
                    async with aiofiles.open(thumb_path, "wb") as f:
                        await f.write(await resp.read())
                    downloaded = True
    except Exception:
        pass

    if not downloaded:
        return YOUTUBE_IMG_URL

    fonts = _load_fonts()
    font_title, font_meta, font_credit, font_small = fonts

    raw = Image.open(thumb_path).resize((W, H)).convert("RGBA")

    # ══════════════════════════════════════════════════════════════════════
    # BACKGROUND — blurred + slightly darkened (image-1 style: bg IS the art)
    # ══════════════════════════════════════════════════════════════════════
    bg = ImageEnhance.Brightness(
        raw.filter(ImageFilter.GaussianBlur(20))
    ).enhance(0.55).convert("RGBA")

    # Subtle dark vignette overlay at edges
    vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd  = ImageDraw.Draw(vig)
    for i in range(80, 0, -1):
        a = int(160 * (1 - i / 80) ** 2)
        vd.rectangle([i, i, W - i, H - i], outline=(0, 0, 0, a), width=1)
    bg = Image.alpha_composite(bg, vig)

    # ══════════════════════════════════════════════════════════════════════
    # MAIN ALBUM ART — large, left-center (image-1 style)
    # ══════════════════════════════════════════════════════════════════════
    ART_W, ART_H = 680, 500
    ART_X = 30
    ART_Y = (H - ART_H) // 2 - 30   # slightly above center
    ART_R = 22

    # Outer cyan glow behind art
    for blur, alpha in [(36, 30), (20, 55), (10, 80)]:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle(
            [ART_X - 18, ART_Y - 18, ART_X + ART_W + 18, ART_Y + ART_H + 18],
            radius=ART_R + 12, fill=(*CYAN, alpha))
        bg = Image.alpha_composite(bg, glow.filter(ImageFilter.GaussianBlur(blur)))

    # Cyan border ring
    border = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle(
        [ART_X - 5, ART_Y - 5, ART_X + ART_W + 5, ART_Y + ART_H + 5],
        radius=ART_R + 5, outline=(*CYAN, 230), width=4)
    bg = Image.alpha_composite(bg, border)

    # Paste art with rounded mask
    art = raw.resize((ART_W, ART_H))
    mask = Image.new("L", (ART_W, ART_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, ART_W, ART_H), radius=ART_R, fill=255)
    bg.paste(art, (ART_X, ART_Y), mask)

    draw = ImageDraw.Draw(bg)

    # ══════════════════════════════════════════════════════════════════════
    # BOTTOM INFO BAR — full width dark strip (image-1 style)
    # ══════════════════════════════════════════════════════════════════════
    BAR_H  = 110
    BAR_Y  = H - BAR_H

    bar = Image.new("RGBA", (W, BAR_H), (6, 4, 16, 210))
    bg.paste(bar, (0, BAR_Y), bar)
    draw = ImageDraw.Draw(bg)

    # Thin cyan top edge of bar
    draw.line([(0, BAR_Y), (W, BAR_Y)], fill=(*CYAN, 180), width=2)

    # Title
    title_line = trim_to_width(title, font_title, W - 40)
    draw.text((22, BAR_Y + 10), title_line, fill=WHITE, font=font_title)

    # Meta info line (image-1 style: "YouTube : 471K views | Time : 9:47")
    meta = f"YouTube : {views} views  |  Time : {duration_txt}"
    draw.text((22, BAR_Y + 58), meta, fill=(*CYAN, 240), font=font_meta)

    # ══════════════════════════════════════════════════════════════════════
    # BOTTOM-LEFT — @username watermark (image-1 style, cyan text)
    # ══════════════════════════════════════════════════════════════════════
    _uname = f"@{BOT_USERNAME}" if BOT_USERNAME else "@ANNIEXMUSICxBOT"
    draw.text((18, BAR_Y + 84), _uname, fill=(*CYAN, 210), font=font_credit)

    # ══════════════════════════════════════════════════════════════════════
    # TOP-RIGHT — Dev credit (image-1 style: "Dev :- @BotUsername" in yellow)
    # ══════════════════════════════════════════════════════════════════════
    dev_txt = f"Dev :- @{BOT_USERNAME}" if BOT_USERNAME else "Dev :- @ANNIEXMUSICxBOT"
    dev_w   = int(font_credit.getlength(dev_txt))
    draw.text((W - dev_w - 18, 14), dev_txt, fill=(*YELLOW, 230), font=font_credit)

    # ══════════════════════════════════════════════════════════════════════
    # TOP-RIGHT — Bot avatar (small circle, top-right corner, no label)
    # ══════════════════════════════════════════════════════════════════════
    avatar_path = (
        "ANNIEMUSIC/assets/bot_pfp.png"
        if os.path.isfile("ANNIEMUSIC/assets/bot_pfp.png")
        else "ANNIEMUSIC/assets/upic.png"
    )
    AV   = 72
    AV_X = W - AV - 18
    AV_Y_pos = 42   # below dev credit text

    if os.path.isfile(avatar_path):
        try:
            av  = _circle_avatar(Image.open(avatar_path), AV)
            cx2 = AV_X + AV // 2
            cy2 = AV_Y_pos + AV // 2

            # Glow ring behind avatar
            for ring_r, ring_a, blur in [(AV + 22, 40, 14), (AV + 10, 80, 7)]:
                rg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(rg).ellipse(
                    [cx2 - ring_r // 2, cy2 - ring_r // 2,
                     cx2 + ring_r // 2, cy2 + ring_r // 2],
                    fill=(*CYAN, ring_a))
                bg = Image.alpha_composite(bg, rg.filter(ImageFilter.GaussianBlur(blur)))

            draw = ImageDraw.Draw(bg)
            draw.ellipse([AV_X - 4, AV_Y_pos - 4, AV_X + AV + 4, AV_Y_pos + AV + 4],
                         outline=(*CYAN, 240), width=3)
            bg.paste(av, (AV_X, AV_Y_pos), av)
            draw = ImageDraw.Draw(bg)
        except Exception:
            pass

    # ── Cleanup + save ─────────────────────────────────────────────────────
    try:
        os.remove(thumb_path)
    except OSError:
        pass

    bg.convert("RGB").save(cache_path)
    return cache_path
