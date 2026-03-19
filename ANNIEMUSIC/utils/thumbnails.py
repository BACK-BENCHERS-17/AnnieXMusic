import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch
from config import YOUTUBE_IMG_URL
from ANNIEMUSIC.core.dir import CACHE_DIR

W, H = 1280, 720

CYAN       = (0, 220, 255)
MAGENTA    = (255, 30, 180)
WHITE      = (255, 255, 255)
OFF_WHITE  = (230, 230, 245)
SOFT_GRAY  = (165, 165, 185)
LIVE_RED   = (255, 70, 70)
VIEW_RED   = (180, 20, 20)
DARK_BG    = (10, 6, 20, 255)

_FONT_BOLD = "ANNIEMUSIC/assets/thumb/font2.ttf"
_FONT_REG  = "ANNIEMUSIC/assets/thumb/font.ttf"


def _load_fonts():
    try:
        return (
            ImageFont.truetype(_FONT_BOLD, 42),   # [0] title large
            ImageFont.truetype(_FONT_BOLD, 22),   # [1] badge / label key
            ImageFont.truetype(_FONT_REG,  20),   # [2] meta value
            ImageFont.truetype(_FONT_REG,  17),   # [3] small
            ImageFont.truetype(_FONT_BOLD, 21),   # [4] watermark
            ImageFont.truetype(_FONT_BOLD, 28),   # [5] channel
            ImageFont.truetype(_FONT_REG,  16),   # [6] tiny
        )
    except OSError:
        d = ImageFont.load_default()
        return d, d, d, d, d, d, d


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


def _glow_layer(base, x1, y1, x2, y2, color_rgba, radius=20, blur=24):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(
        [x1, y1, x2, y2], radius=radius, fill=color_rgba
    )
    return Image.alpha_composite(base, layer.filter(ImageFilter.GaussianBlur(blur)))


async def get_thumb(videoid: str) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_v9.png")
    if os.path.exists(cache_path):
        return cache_path

    try:
        results_data = await VideosSearch(
            f"https://www.youtube.com/watch?v={videoid}", limit=1
        ).next()
        data      = (results_data.get("result") or [{}])[0]
        title     = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
        thumbnail = (data.get("thumbnails") or [{}])[0].get("url") or YOUTUBE_IMG_URL
        duration  = data.get("duration")
        views     = (data.get("viewCount") or {}).get("short") or "Unknown"
        channel   = (data.get("channel") or {}).get("name") or "YouTube"
    except Exception:
        title, thumbnail, duration, views, channel = (
            "Unsupported Title", YOUTUBE_IMG_URL, None, "Unknown", "YouTube"
        )

    is_live      = not duration or str(duration).strip().lower() in {"", "live", "live now"}
    duration_txt = "● LIVE" if is_live else (duration or "—")

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
    font_title, font_badge, font_meta, font_small, font_wm, font_channel, font_tiny = fonts

    raw = Image.open(thumb_path).resize((W, H)).convert("RGBA")

    # ── Background: heavy blur + darken + warm tint ────────────────────────────
    bg = ImageEnhance.Brightness(
        raw.filter(ImageFilter.GaussianBlur(34))
    ).enhance(0.22).convert("RGBA")
    bg = ImageEnhance.Color(bg).enhance(1.8)

    dark_overlay = Image.new("RGBA", (W, H), (8, 4, 18, 215))
    bg = Image.alpha_composite(bg, dark_overlay)

    # Radial warm glow (center-left, behind album art area)
    glow_c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_c)
    for i in range(12, 0, -1):
        t  = i / 12
        rx = int(380 * t)
        ry = int(310 * t)
        gd.ellipse([300 - rx, 360 - ry, 300 + rx, 360 + ry],
                   fill=(90, 20, 50, int(50 * t)))
    bg = Image.alpha_composite(bg, glow_c.filter(ImageFilter.GaussianBlur(18)))

    # Right-side warm glow
    glow_r = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gdr = ImageDraw.Draw(glow_r)
    for i in range(10, 0, -1):
        t  = i / 10
        rx = int(260 * t)
        ry = int(200 * t)
        gdr.ellipse([980 - rx, 300 - ry, 980 + rx, 300 + ry],
                    fill=(20, 10, 60, int(40 * t)))
    bg = Image.alpha_composite(bg, glow_r.filter(ImageFilter.GaussianBlur(16)))

    draw = ImageDraw.Draw(bg)

    # ── Neon top border ────────────────────────────────────────────────────────
    for thick, alpha in [(24, 30), (10, 80), (3, 255)]:
        ln = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ln).line([(0, 0), (W, 0)], fill=(*CYAN, alpha), width=thick)
        bg = Image.alpha_composite(bg, ln)

    # ── Neon bottom border ─────────────────────────────────────────────────────
    for thick, alpha in [(20, 30), (8, 80), (3, 255)]:
        ln = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ln).line([(0, H - 1), (W, H - 1)], fill=(*MAGENTA, alpha), width=thick)
        bg = Image.alpha_composite(bg, ln)

    draw = ImageDraw.Draw(bg)

    # Corner accent dots
    for cx, cy, col in [(0, 0, CYAN), (W, 0, MAGENTA), (0, H, MAGENTA), (W, H, CYAN)]:
        draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=col)

    # ══════════════════════════════════════════════════════════════════════════
    # LEFT PANEL — Large album art (image-2 style)
    # ══════════════════════════════════════════════════════════════════════════
    TX, TY, TW, TH, TR = 50, 88, 500, 500, 28

    # Warm glow behind art
    bg = _glow_layer(bg, TX - 22, TY - 22, TX + TW + 22, TY + TH + 22,
                     (*MAGENTA, 40), radius=TR + 14, blur=32)

    # Outer magenta ring
    ring1 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ring1).rounded_rectangle(
        [TX - 6, TY - 6, TX + TW + 6, TY + TH + 6],
        radius=TR + 6, outline=(*MAGENTA, 210), width=3)
    bg = Image.alpha_composite(bg, ring1)

    # Inner subtle cyan ring
    ring2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ring2).rounded_rectangle(
        [TX - 12, TY - 12, TX + TW + 12, TY + TH + 12],
        radius=TR + 12, outline=(*CYAN, 70), width=1)
    bg = Image.alpha_composite(bg, ring2)

    # Paste album art
    thumb_img = raw.resize((TW, TH))
    t_mask = Image.new("L", (TW, TH), 0)
    ImageDraw.Draw(t_mask).rounded_rectangle((0, 0, TW, TH), radius=TR, fill=255)
    bg.paste(thumb_img, (TX, TY), t_mask)
    draw = ImageDraw.Draw(bg)

    # "NOW PLAYING" badge — top-left of art
    np_txt = "♫  NOW PLAYING"
    np_w   = int(font_tiny.getlength(np_txt)) + 18
    np_x, np_y = TX + 14, TY + 14
    draw.rounded_rectangle([np_x, np_y, np_x + np_w, np_y + 26],
                           radius=6, fill=(0, 0, 0, 175))
    draw.text((np_x + 9, np_y + 5), np_txt, fill=(*CYAN, 255), font=font_tiny)

    # Views badge — bottom-left of art (image-2 red pill style)
    views_txt = f"  {views} Views  "
    vb_w = int(font_tiny.getlength(views_txt)) + 6
    vb_x, vb_y = TX + 14, TY + TH - 42
    draw.rounded_rectangle([vb_x, vb_y, vb_x + vb_w, vb_y + 28],
                           radius=8, fill=(*VIEW_RED, 230))
    draw.text((vb_x + 9, vb_y + 6), views_txt.strip(), fill=WHITE, font=font_tiny)

    # ══════════════════════════════════════════════════════════════════════════
    # RIGHT PANEL — Info (image-2 style)
    # ══════════════════════════════════════════════════════════════════════════
    IX, IY = 590, 88
    IW     = W - IX - 28

    # Semi-transparent dark panel
    panel = Image.new("RGBA", (IW + 16, 508), (10, 6, 26, 185))
    p_mask = Image.new("L", (IW + 16, 508), 0)
    ImageDraw.Draw(p_mask).rounded_rectangle((0, 0, IW + 16, 508), radius=22, fill=255)
    bg.paste(panel, (IX - 14, IY - 14), p_mask)

    # Left cyan accent bar
    for thick, alpha in [(22, 28), (10, 70), (3, 255)]:
        bar = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(bar).line(
            [(IX - 16, IY - 2), (IX - 16, IY + 474)],
            fill=(*CYAN, alpha), width=thick)
        bg = Image.alpha_composite(bg, bar)

    draw = ImageDraw.Draw(bg)

    # ── "NOW PLAYING" small label
    draw.text((IX, IY + 6), "NOW PLAYING", fill=(*SOFT_GRAY, 195), font=font_tiny)

    # Underline below label
    lbl_w = int(font_tiny.getlength("NOW PLAYING"))
    draw.line([(IX, IY + 26), (IX + lbl_w + 20, IY + 26)],
              fill=(*CYAN, 110), width=1)

    # ── Title (big bold white)
    title_y = IY + 38
    title_line = trim_to_width(title, font_title, IW - 4)
    draw.text((IX + 2, title_y + 2), title_line, fill=(0, 0, 0, 100), font=font_title)
    draw.text((IX, title_y), title_line, fill=WHITE, font=font_title)

    # ── Thin divider
    div1_y = title_y + 60
    draw.line([(IX, div1_y), (IX + IW - 8, div1_y)],
              fill=(60, 40, 95, 200), width=1)

    # ── Channel / Artist
    ch_y  = div1_y + 16
    ch_tx = trim_to_width(f"◈  {channel}", font_channel, IW - 8)
    draw.text((IX, ch_y), ch_tx, fill=(*CYAN, 220), font=font_channel)

    # ── Duration row
    row1_y = ch_y + 52
    draw.text((IX, row1_y), "Duration :", fill=(*SOFT_GRAY, 200), font=font_badge)
    dur_col = LIVE_RED if is_live else OFF_WHITE
    draw.text((IX + 132, row1_y), duration_txt, fill=dur_col, font=font_badge)

    # ── Views row
    row2_y = row1_y + 38
    draw.text((IX, row2_y), "Views :", fill=(*SOFT_GRAY, 200), font=font_badge)
    draw.text((IX + 132, row2_y), f"{views} views", fill=OFF_WHITE, font=font_badge)

    # ── Divider before progress bar
    div2_y = row2_y + 44
    draw.line([(IX, div2_y), (IX + IW - 8, div2_y)],
              fill=(60, 40, 95, 200), width=1)

    # ── Progress bar (image-2 style)
    PBX    = IX
    PBY    = div2_y + 20
    PB_W   = IW - 14
    PB_H   = 7
    PLAYED = int(PB_W * 0.08)   # small amount — just started

    # Track background
    draw.rounded_rectangle([PBX, PBY, PBX + PB_W, PBY + PB_H],
                           radius=4, fill=(38, 28, 68, 255))

    # Gradient fill cyan → magenta
    if PLAYED > 0:
        grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd3  = ImageDraw.Draw(grad)
        for i in range(PLAYED):
            t = i / max(PLAYED - 1, 1)
            r = int(0   + 255 * t)
            g = int(220 - 190 * t)
            b = int(255 - 75  * t)
            gd3.line([(PBX + i, PBY), (PBX + i, PBY + PB_H)], fill=(r, g, b, 255))
        bg = Image.alpha_composite(bg, grad)
        draw = ImageDraw.Draw(bg)

    # Playhead dot
    dot_x = PBX + PLAYED
    dot_y = PBY + PB_H // 2
    for r_sz, alp in [(17, 40), (10, 100)]:
        g_dot = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g_dot).ellipse(
            [dot_x - r_sz, dot_y - r_sz, dot_x + r_sz, dot_y + r_sz],
            fill=(*CYAN, alp))
        bg = Image.alpha_composite(bg, g_dot.filter(ImageFilter.GaussianBlur(4)))
    draw = ImageDraw.Draw(bg)
    draw.ellipse([dot_x - 8, dot_y - 8, dot_x + 8, dot_y + 8], fill=WHITE)
    draw.ellipse([dot_x - 4, dot_y - 4, dot_x + 4, dot_y + 4], fill=(*CYAN, 210))

    # Timestamps
    tm_y = PBY + 13
    draw.text((PBX, tm_y), "00:00", fill=SOFT_GRAY, font=font_tiny)
    end_w = int(font_tiny.getlength(duration_txt))
    draw.text((PBX + PB_W - end_w, tm_y), duration_txt,
              fill=LIVE_RED if is_live else SOFT_GRAY, font=font_tiny)

    # ── Platform badge
    plat_y = PBY + 36
    badge  = "▶  YouTube"
    bw     = int(font_tiny.getlength(badge)) + 22
    draw.rounded_rectangle([IX, plat_y, IX + bw, plat_y + 24],
                           radius=7, fill=(0, 120, 255, 215))
    draw.text((IX + 11, plat_y + 4), badge, fill=WHITE, font=font_tiny)

    # ══════════════════════════════════════════════════════════════════════════
    # TOP-RIGHT — Bot avatar (no username, no label below)
    # ══════════════════════════════════════════════════════════════════════════
    avatar_path = (
        "ANNIEMUSIC/assets/bot_pfp.png"
        if os.path.isfile("ANNIEMUSIC/assets/bot_pfp.png")
        else "ANNIEMUSIC/assets/upic.png"
    )
    AV   = 90
    AV_X = W - AV - 22
    AV_Y = 16

    if os.path.isfile(avatar_path):
        try:
            av   = _circle_avatar(Image.open(avatar_path), AV)
            cx2  = AV_X + AV // 2
            cy2  = AV_Y + AV // 2

            # Outer glow rings
            for ring_r, ring_a, blur in [(AV + 26, 40, 16), (AV + 12, 85, 8)]:
                rg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(rg).ellipse(
                    [cx2 - ring_r // 2, cy2 - ring_r // 2,
                     cx2 + ring_r // 2, cy2 + ring_r // 2],
                    fill=(*CYAN, ring_a))
                bg = Image.alpha_composite(bg, rg.filter(ImageFilter.GaussianBlur(blur)))

            draw = ImageDraw.Draw(bg)
            draw.ellipse([AV_X - 5, AV_Y - 5, AV_X + AV + 5, AV_Y + AV + 5],
                         outline=(*CYAN, 255), width=3)
            draw.ellipse([AV_X - 9, AV_Y - 9, AV_X + AV + 9, AV_Y + AV + 9],
                         outline=(*MAGENTA, 120), width=1)
            bg.paste(av, (AV_X, AV_Y), av)
            draw = ImageDraw.Draw(bg)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # BOTTOM — Watermark + decorative divider
    # ══════════════════════════════════════════════════════════════════════════
    dv_y = H - 54
    draw.line([(80, dv_y), (W - 80, dv_y)], fill=(70, 0, 90, 130), width=1)
    for dot_cx, dot_col in [(78, CYAN), (W - 78, MAGENTA)]:
        draw.ellipse([dot_cx - 4, dv_y - 4, dot_cx + 4, dv_y + 4], fill=dot_col)

    wm   = "✦  MADE BY KHUSHI  ✦"
    wm_w = int(font_wm.getlength(wm))
    wm_x = (W - wm_w) // 2
    wm_y = H - 40
    draw.text((wm_x + 2, wm_y + 2), wm, fill=(*MAGENTA, 40), font=font_wm)
    draw.text((wm_x, wm_y), wm, fill=(*MAGENTA, 255), font=font_wm)

    # Subtle corner grid lines (top-left accent)
    for i in range(1, 6):
        off = i * 26
        draw.line([(off, 0), (0, off)], fill=(*CYAN, 15), width=1)

    # ── Cleanup + save ─────────────────────────────────────────────────────────
    try:
        os.remove(thumb_path)
    except OSError:
        pass

    bg.convert("RGB").save(cache_path)
    return cache_path
