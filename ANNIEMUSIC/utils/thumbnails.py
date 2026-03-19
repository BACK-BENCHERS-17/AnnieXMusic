import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch
from config import YOUTUBE_IMG_URL, BOT_USERNAME
from ANNIEMUSIC.core.dir import CACHE_DIR

W, H = 1280, 720

# ── Colour palette ────────────────────────────────────────────────────────────
CYAN        = (0, 230, 255)
PINK        = (255, 60, 180)
PURPLE      = (140, 60, 255)
WHITE       = (255, 255, 255)
GOLD        = (255, 210, 60)
DARK_BG     = (8, 6, 18)
GLASS_BG    = (18, 14, 40, 210)

_FONT_BOLD = "ANNIEMUSIC/assets/thumb/font2.ttf"
_FONT_REG  = "ANNIEMUSIC/assets/thumb/font.ttf"


def _load_fonts():
    try:
        return (
            ImageFont.truetype(_FONT_BOLD, 42),   # [0] title
            ImageFont.truetype(_FONT_REG,  22),   # [1] meta
            ImageFont.truetype(_FONT_BOLD, 20),   # [2] credit / watermark
            ImageFont.truetype(_FONT_REG,  18),   # [3] small
            ImageFont.truetype(_FONT_BOLD, 30),   # [4] platform badge
        )
    except OSError:
        d = ImageFont.load_default()
        return d, d, d, d, d


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


def _draw_rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill,
                           outline=outline, width=width)


def _neon_glow(base, xy, radius, color, blur_radius=18, alpha=80):
    """Draw a soft neon glow layer behind a rounded rect."""
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x1, y1, x2, y2 = xy
    ImageDraw.Draw(glow).rounded_rectangle(
        [x1 - 14, y1 - 14, x2 + 14, y2 + 14],
        radius=radius + 10, fill=(*color, alpha)
    )
    return Image.alpha_composite(base, glow.filter(ImageFilter.GaussianBlur(blur_radius)))


async def get_thumb(videoid: str) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_v20.png")
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
    duration_txt = "🔴  LIVE" if is_live else (duration or "—")

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
    font_title, font_meta, font_credit, font_small, font_badge = fonts

    raw = Image.open(thumb_path).resize((W, H)).convert("RGBA")

    # ══════════════════════════════════════════════════════════════════════
    # BACKGROUND — heavily blurred + darkened for contrast
    # ══════════════════════════════════════════════════════════════════════
    bg = ImageEnhance.Brightness(
        raw.filter(ImageFilter.GaussianBlur(28))
    ).enhance(0.35).convert("RGBA")

    # Deep dark gradient overlay (left transparent → right very dark)
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(grad)
    for x in range(W):
        alpha = int(200 * (x / W) ** 0.7)
        gd.line([(x, 0), (x, H)], fill=(6, 4, 16, alpha))
    bg = Image.alpha_composite(bg, grad)

    # Subtle vignette
    vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd  = ImageDraw.Draw(vig)
    for i in range(100, 0, -1):
        a = int(180 * (1 - i / 100) ** 1.8)
        vd.rectangle([i, i, W - i, H - i], outline=(0, 0, 0, a), width=1)
    bg = Image.alpha_composite(bg, vig)

    # ══════════════════════════════════════════════════════════════════════
    # LEFT — ALBUM ART with multi-color neon glow
    # ══════════════════════════════════════════════════════════════════════
    ART_W, ART_H = 560, 560
    ART_X = 50
    ART_Y = (H - ART_H) // 2

    # Layered glow: cyan outer, pink inner
    for color, blur, alpha in [(CYAN, 40, 22), (PINK, 24, 38), (PURPLE, 14, 55)]:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle(
            [ART_X - 20, ART_Y - 20, ART_X + ART_W + 20, ART_Y + ART_H + 20],
            radius=32, fill=(*color, alpha)
        )
        bg = Image.alpha_composite(bg, glow.filter(ImageFilter.GaussianBlur(blur)))

    # Double border ring (pink outer, cyan inner)
    border_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(border_layer)
    bd.rounded_rectangle(
        [ART_X - 7, ART_Y - 7, ART_X + ART_W + 7, ART_Y + ART_H + 7],
        radius=32, outline=(*PINK, 200), width=4
    )
    bd.rounded_rectangle(
        [ART_X - 2, ART_Y - 2, ART_X + ART_W + 2, ART_Y + ART_H + 2],
        radius=28, outline=(*CYAN, 160), width=2
    )
    bg = Image.alpha_composite(bg, border_layer)

    # Paste rounded album art
    art = raw.resize((ART_W, ART_H))
    mask = Image.new("L", (ART_W, ART_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, ART_W, ART_H), radius=28, fill=255)
    bg.paste(art, (ART_X, ART_Y), mask)

    # ══════════════════════════════════════════════════════════════════════
    # RIGHT — GLASSMORPHISM INFO PANEL
    # ══════════════════════════════════════════════════════════════════════
    PANEL_X  = ART_X + ART_W + 50
    PANEL_Y  = 80
    PANEL_W  = W - PANEL_X - 40
    PANEL_H  = H - 160
    PANEL_R  = 28

    # Glass panel glow
    gl_glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl_glow).rounded_rectangle(
        [PANEL_X - 10, PANEL_Y - 10, PANEL_X + PANEL_W + 10, PANEL_Y + PANEL_H + 10],
        radius=PANEL_R + 8, fill=(*CYAN, 12)
    )
    bg = Image.alpha_composite(bg, gl_glow.filter(ImageFilter.GaussianBlur(18)))

    # Glass fill
    glass = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glass).rounded_rectangle(
        [PANEL_X, PANEL_Y, PANEL_X + PANEL_W, PANEL_Y + PANEL_H],
        radius=PANEL_R, fill=(15, 12, 35, 195)
    )
    bg = Image.alpha_composite(bg, glass)

    # Glass top border (cyan gradient line)
    border_glass = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bgd = ImageDraw.Draw(border_glass)
    bgd.rounded_rectangle(
        [PANEL_X, PANEL_Y, PANEL_X + PANEL_W, PANEL_Y + PANEL_H],
        radius=PANEL_R, outline=(*CYAN, 90), width=2
    )
    bg = Image.alpha_composite(bg, border_glass)

    draw = ImageDraw.Draw(bg)

    # ── ♫ Music Note accent ──────────────────────────────────────────────
    draw.text((PANEL_X + 20, PANEL_Y + 20), "♫", fill=(*CYAN, 220), font=font_badge)

    # ── Platform badge ───────────────────────────────────────────────────
    badge_txt = "YOUTUBE"
    badge_w = int(font_small.getlength(badge_txt)) + 24
    draw.rounded_rectangle(
        [PANEL_X + PANEL_W - badge_w - 16, PANEL_Y + 18,
         PANEL_X + PANEL_W - 16, PANEL_Y + 40],
        radius=10, fill=(*PINK, 200)
    )
    draw.text(
        (PANEL_X + PANEL_W - badge_w - 4, PANEL_Y + 20),
        badge_txt, fill=WHITE, font=font_small
    )

    # ── Title ────────────────────────────────────────────────────────────
    title_y = PANEL_Y + 68
    title_line = trim_to_width(title, font_title, PANEL_W - 24)
    draw.text((PANEL_X + 20, title_y), title_line, fill=WHITE, font=font_title)

    # Thin cyan underline below title
    tlen = int(font_title.getlength(title_line))
    draw.line(
        [(PANEL_X + 20, title_y + 48), (PANEL_X + 20 + min(tlen, PANEL_W - 24), title_y + 48)],
        fill=(*CYAN, 180), width=2
    )

    # ── Views row ────────────────────────────────────────────────────────
    views_y = title_y + 62
    draw.text((PANEL_X + 20, views_y), "👁  " + views + " views", fill=(*CYAN, 220), font=font_meta)

    # ── Duration row ─────────────────────────────────────────────────────
    dur_y = views_y + 36
    draw.text((PANEL_X + 20, dur_y), "⏱  " + duration_txt, fill=(*PINK, 230), font=font_meta)

    # ── Divider ──────────────────────────────────────────────────────────
    div_y = dur_y + 46
    for ix in range(PANEL_W - 40):
        alpha = int(130 * abs(1 - 2 * ix / (PANEL_W - 40)))
        draw.point((PANEL_X + 20 + ix, div_y), fill=(*CYAN, alpha))

    # ── Now Playing label ────────────────────────────────────────────────
    np_y = div_y + 16
    draw.text((PANEL_X + 20, np_y), "▶  NOW PLAYING", fill=(*GOLD, 230), font=font_credit)

    # ── Equalizer bars decoration ────────────────────────────────────────
    eq_x = PANEL_X + PANEL_W - 80
    eq_y = np_y
    bars = [18, 28, 14, 34, 22, 12, 30]
    for i, bar_h in enumerate(bars):
        bx = eq_x + i * 9
        eq_color = CYAN if i % 2 == 0 else PINK
        draw.rectangle(
            [bx, eq_y + 34 - bar_h, bx + 5, eq_y + 34],
            fill=(*eq_color, 220)
        )

    # ── Static progress bar drawn on thumbnail ───────────────────────────
    pb_y = np_y + 52
    pb_x1, pb_x2 = PANEL_X + 20, PANEL_X + PANEL_W - 20
    pb_track_y = pb_y + 8

    # Track background
    draw.rounded_rectangle(
        [pb_x1, pb_track_y, pb_x2, pb_track_y + 6],
        radius=3, fill=(50, 45, 80, 200)
    )
    # Filled 45% as static preview
    pb_fill_end = int(pb_x1 + (pb_x2 - pb_x1) * 0.45)
    draw.rounded_rectangle(
        [pb_x1, pb_track_y, pb_fill_end, pb_track_y + 6],
        radius=3, fill=(*CYAN, 255)
    )
    # Knob
    knob_x = pb_fill_end
    draw.ellipse([knob_x - 7, pb_track_y - 4, knob_x + 7, pb_track_y + 10],
                 fill=(*WHITE, 255))

    # ── Bot username ─────────────────────────────────────────────────────
    bname_y = pb_y + 34
    _uname = f"@{BOT_USERNAME}" if BOT_USERNAME else "@ANNIEXMUSICxBOT"
    draw.text((PANEL_X + 20, bname_y), _uname, fill=(*CYAN, 210), font=font_credit)

    # ── Developer credit ─────────────────────────────────────────────────
    dev_txt = "Dev :- @PGL_B4CHI"
    dev_w   = int(font_credit.getlength(dev_txt))
    draw.text(
        (PANEL_X + PANEL_W - dev_w - 20, bname_y),
        dev_txt, fill=(*GOLD, 235), font=font_credit
    )

    # ══════════════════════════════════════════════════════════════════════
    # TOP-LEFT — Bot avatar circle
    # ══════════════════════════════════════════════════════════════════════
    avatar_path = (
        "ANNIEMUSIC/assets/bot_pfp.png"
        if os.path.isfile("ANNIEMUSIC/assets/bot_pfp.png")
        else "ANNIEMUSIC/assets/upic.png"
    )
    AV   = 68
    AV_X = 18
    AV_Y_pos = 18

    if os.path.isfile(avatar_path):
        try:
            av  = _circle_avatar(Image.open(avatar_path), AV)
            cx2 = AV_X + AV // 2
            cy2 = AV_Y_pos + AV // 2

            for ring_r, ring_a, blur in [(AV + 24, 35, 16), (AV + 10, 70, 7)]:
                rg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(rg).ellipse(
                    [cx2 - ring_r // 2, cy2 - ring_r // 2,
                     cx2 + ring_r // 2, cy2 + ring_r // 2],
                    fill=(*CYAN, ring_a)
                )
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
