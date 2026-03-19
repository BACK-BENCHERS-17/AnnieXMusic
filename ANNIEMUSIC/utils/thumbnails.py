import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch
from config import YOUTUBE_IMG_URL
from ANNIEMUSIC.core.dir import CACHE_DIR

W, H = 1280, 720

# ── Neon color palette ─────────────────────────────────────────────────────────
CYAN       = (0, 255, 255)
MAGENTA    = (255, 0, 255)
WHITE      = (255, 255, 255)
NEON_BLUE  = (0, 160, 255)
NEON_PINK  = (255, 64, 180)
DARK_BG    = (6, 6, 22, 210)
SOFT_GRAY  = (170, 170, 195)
DIM_WHITE  = (210, 210, 230)
LIVE_RED   = (255, 70, 70)

# ── Font paths ─────────────────────────────────────────────────────────────────
_FONT_BOLD = "ANNIEMUSIC/assets/thumb/font2.ttf"
_FONT_REG  = "ANNIEMUSIC/assets/thumb/font.ttf"


def _load_fonts():
    try:
        return (
            ImageFont.truetype(_FONT_BOLD, 38),   # title
            ImageFont.truetype(_FONT_BOLD, 22),   # channel / badge
            ImageFont.truetype(_FONT_REG,  20),   # meta / time
            ImageFont.truetype(_FONT_REG,  17),   # small labels
            ImageFont.truetype(_FONT_BOLD, 21),   # watermark
        )
    except OSError:
        d = ImageFont.load_default()
        return d, d, d, d, d


def trim_to_width(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    if font.getlength(text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        if font.getlength(text[:i] + "…") <= max_w:
            return text[:i] + "…"
    return "…"


def _glow_layer(size, shape_fn, color_rgba, blur=18):
    """Return a blurred glow Image for neon effect."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    shape_fn(ImageDraw.Draw(layer), color_rgba)
    return layer.filter(ImageFilter.GaussianBlur(blur))


def _paste_glow(base: Image.Image, glow: Image.Image) -> Image.Image:
    return Image.alpha_composite(base, glow)


def _circle_avatar(img: Image.Image, size: int) -> Image.Image:
    img = img.resize((size, size)).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img


async def get_thumb(videoid: str) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_v6.png")
    if os.path.exists(cache_path):
        return cache_path

    # ── Fetch YouTube metadata ─────────────────────────────────────────────────
    try:
        results_data = await VideosSearch(
            f"https://www.youtube.com/watch?v={videoid}", limit=1
        ).next()
        data = (results_data.get("result") or [{}])[0]
        title    = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
        thumbnail= (data.get("thumbnails") or [{}])[0].get("url") or YOUTUBE_IMG_URL
        duration = data.get("duration")
        views    = (data.get("viewCount") or {}).get("short") or "Unknown Views"
        channel  = (data.get("channel") or {}).get("name") or "YouTube"
    except Exception:
        title, thumbnail, duration, views, channel = (
            "Unsupported Title", YOUTUBE_IMG_URL, None, "Unknown Views", "YouTube"
        )

    is_live      = not duration or str(duration).strip().lower() in {"", "live", "live now"}
    duration_txt = "● LIVE" if is_live else (duration or "Unknown")

    # ── Download video thumbnail ───────────────────────────────────────────────
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

    # ── Fonts ──────────────────────────────────────────────────────────────────
    font_title, font_channel, font_meta, font_small, font_wm = _load_fonts()

    # ── Base background: blurred + darkened ────────────────────────────────────
    raw  = Image.open(thumb_path).resize((W, H)).convert("RGBA")
    # Slightly less dark so background colors still show through
    bg   = ImageEnhance.Brightness(
               raw.filter(ImageFilter.GaussianBlur(22))
           ).enhance(0.35).convert("RGBA")
    # Boost contrast a little so it feels vivid
    bg = ImageEnhance.Color(bg).enhance(1.4)

    # Dark blue-tinted overlay (reduced opacity so bg is visible)
    overlay = Image.new("RGBA", (W, H), (4, 6, 28, 175))
    bg = Image.alpha_composite(bg, overlay)

    # ── Top neon bar (cyan) ────────────────────────────────────────────────────
    for thick, alpha in [(20, 40), (10, 90), (4, 255)]:
        glayer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glayer).line([(0, 0), (W, 0)], fill=(*CYAN, alpha), width=thick)
        bg = Image.alpha_composite(bg, glayer)

    # ── Bottom neon bar (magenta) ──────────────────────────────────────────────
    for thick, alpha in [(16, 40), (8, 90), (3, 255)]:
        glayer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glayer).line([(0, H - 1), (W, H - 1)], fill=(*MAGENTA, alpha), width=thick)
        bg = Image.alpha_composite(bg, glayer)

    draw = ImageDraw.Draw(bg)

    # ── Corner accent dots ─────────────────────────────────────────────────────
    for cx, cy, col in [(0, 0, CYAN), (W, 0, MAGENTA), (0, H, MAGENTA), (W, H, CYAN)]:
        draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=col)

    # ── Left panel: video thumbnail ────────────────────────────────────────────
    TX, TY, TW, TH, TR = 50, 155, 510, 322, 20

    # Glow behind thumbnail
    glow_fn = lambda d, col: d.rounded_rectangle(
        [TX - 12, TY - 12, TX + TW + 12, TY + TH + 12], radius=TR + 10, fill=col
    )
    bg = _paste_glow(bg, _glow_layer((W, H), glow_fn, (*CYAN, 55), blur=22))

    # Outer magenta ring
    glayer2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glayer2).rounded_rectangle(
        [TX - 4, TY - 4, TX + TW + 4, TY + TH + 4], radius=TR + 4,
        outline=(*MAGENTA, 180), width=2
    )
    bg = Image.alpha_composite(bg, glayer2)

    # Inner cyan ring
    glayer3 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glayer3).rounded_rectangle(
        [TX - 7, TY - 7, TX + TW + 7, TY + TH + 7], radius=TR + 7,
        outline=(*CYAN, 100), width=1
    )
    bg = Image.alpha_composite(bg, glayer3)

    # Paste actual thumbnail
    thumb_img = raw.resize((TW, TH))
    t_mask = Image.new("L", (TW, TH), 0)
    ImageDraw.Draw(t_mask).rounded_rectangle((0, 0, TW, TH), radius=TR, fill=255)
    bg.paste(thumb_img, (TX, TY), t_mask)
    draw = ImageDraw.Draw(bg)

    # "NOW PLAYING" badge on thumbnail
    badge_txt = "♪  NOW PLAYING"
    bw = int(font_small.getlength(badge_txt)) + 20
    bx, by = TX + 14, TY + TH - 36
    draw.rounded_rectangle([bx, by, bx + bw, by + 24], radius=6, fill=(0, 0, 0, 160))
    draw.text((bx + 10, by + 3), badge_txt, fill=(*CYAN, 255), font=font_small)

    # ── Right info panel ───────────────────────────────────────────────────────
    IX, IY = 600, 148
    IW = 630

    # Dark info panel bg
    info_bg = Image.new("RGBA", (IW, 420), (8, 8, 28, 175))
    ip_mask = Image.new("L", (IW, 420), 0)
    ImageDraw.Draw(ip_mask).rounded_rectangle((0, 0, IW, 420), radius=22, fill=255)
    bg.paste(info_bg, (IX - 18, IY - 18), ip_mask)
    draw = ImageDraw.Draw(bg)

    # Left cyan accent line
    for thick, alpha in [(18, 35), (8, 80), (3, 255)]:
        glayer4 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glayer4).line(
            [(IX - 20, IY), (IX - 20, IY + 385)], fill=(*CYAN, alpha), width=thick
        )
        bg = Image.alpha_composite(bg, glayer4)
    draw = ImageDraw.Draw(bg)

    # ── Platform badge ──────────────────────────────────────────────────────────
    badge = "▶  YouTube"
    bw2 = int(font_small.getlength(badge)) + 22
    draw.rounded_rectangle([IX, IY, IX + bw2, IY + 26], radius=7,
                            fill=(0, 140, 255, 210))
    draw.text((IX + 11, IY + 4), badge, fill=WHITE, font=font_small)

    # ── Song title ──────────────────────────────────────────────────────────────
    title_y = IY + 40
    title_display = trim_to_width(title, font_title, IW - 10)
    # Subtle glow
    for dx, dy, alpha in [(2, 2, 50), (0, 0, 255)]:
        col = (*CYAN, alpha) if alpha < 100 else WHITE
        draw.text((IX + dx, title_y + dy), title_display, fill=col, font=font_title)

    # ── Channel ─────────────────────────────────────────────────────────────────
    ch_y = title_y + 52
    draw.text((IX, ch_y), f"◈  {channel}", fill=(*CYAN, 230), font=font_channel)

    # ── Views + Duration ────────────────────────────────────────────────────────
    meta_y = ch_y + 36
    draw.text((IX, meta_y), f"👁  {views}", fill=SOFT_GRAY, font=font_meta)
    dur_x = IX + int(font_meta.getlength(f"👁  {views}")) + 30
    dur_col = LIVE_RED if is_live else SOFT_GRAY
    draw.text((dur_x, meta_y), f"⏱  {duration_txt}", fill=dur_col, font=font_meta)

    # Divider
    div_y = meta_y + 34
    draw.line([(IX, div_y), (IX + IW - 30, div_y)], fill=(50, 50, 90, 200), width=1)

    # ── Neon progress bar ───────────────────────────────────────────────────────
    PBX, PBY = IX, div_y + 22
    PB_W, PB_H = IW - 30, 7
    PLAYED = int(PB_W * 0.38)

    # Background track
    draw.rounded_rectangle([PBX, PBY, PBX + PB_W, PBY + PB_H], radius=4, fill=(45, 45, 75))

    # Gradient fill: cyan → magenta
    grad_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad_layer)
    for i in range(PLAYED):
        t = i / max(PLAYED - 1, 1)
        r = int(0   + 255 * t)
        g = int(255 - 255 * t)
        b = int(255 - 55  * t)
        gd.line([(PBX + i, PBY), (PBX + i, PBY + PB_H)], fill=(r, g, b, 255))
    bg = Image.alpha_composite(bg, grad_layer)
    draw = ImageDraw.Draw(bg)

    # Playhead dot with glow
    dot_x = PBX + PLAYED
    dot_y = PBY + PB_H // 2
    for r_sz, alpha in [(14, 50), (9, 120)]:
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(gl).ellipse(
            [dot_x - r_sz, dot_y - r_sz, dot_x + r_sz, dot_y + r_sz],
            fill=(*CYAN, alpha)
        )
        bg = Image.alpha_composite(bg, gl.filter(ImageFilter.GaussianBlur(5)))
    draw = ImageDraw.Draw(bg)
    draw.ellipse([dot_x - 6, dot_y - 6, dot_x + 6, dot_y + 6], fill=WHITE)

    # Time labels
    tm_y = PBY + 12
    draw.text((PBX, tm_y), "00:00", fill=SOFT_GRAY, font=font_small)
    end_w = int(font_small.getlength(duration_txt))
    draw.text((PBX + PB_W - end_w, tm_y), duration_txt,
              fill=LIVE_RED if is_live else SOFT_GRAY, font=font_small)

    # ── Playback icons ──────────────────────────────────────────────────────────
    icons_path = "ANNIEMUSIC/assets/thumb/play_icons.png"
    icons_y = PBY + 48
    if os.path.isfile(icons_path):
        try:
            ic = Image.open(icons_path).convert("RGBA")
            ic = ic.resize((380, 46))
            # Colorize icons to white/cyan
            r_c, g_c, b_c, a_c = ic.split()
            white_ic = Image.merge("RGBA", (
                a_c.point(lambda x: x),
                a_c.point(lambda x: x),
                a_c.point(lambda x: x),
                a_c,
            ))
            bg.paste(white_ic, (IX, icons_y), white_ic)
            draw = ImageDraw.Draw(bg)
        except Exception:
            pass

    # ── Bot avatar (circular with neon ring) ────────────────────────────────────
    # Use live-downloaded bot PFP if available, else fall back to static upic.png
    avatar_path = (
        "ANNIEMUSIC/assets/bot_pfp.png"
        if os.path.isfile("ANNIEMUSIC/assets/bot_pfp.png")
        else "ANNIEMUSIC/assets/upic.png"
    )
    AV = 88
    AV_X = W - AV - 28
    AV_Y = 22

    if os.path.isfile(avatar_path):
        try:
            av = _circle_avatar(Image.open(avatar_path), AV)

            # Outer glow ring (cyan)
            for ring_r, ring_a, blur in [(AV + 24, 50, 14), (AV + 12, 100, 8)]:
                rgl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                cx2 = AV_X + AV // 2
                cy2 = AV_Y + AV // 2
                ImageDraw.Draw(rgl).ellipse(
                    [cx2 - ring_r // 2, cy2 - ring_r // 2,
                     cx2 + ring_r // 2, cy2 + ring_r // 2],
                    fill=(*CYAN, ring_a)
                )
                bg = Image.alpha_composite(bg, rgl.filter(ImageFilter.GaussianBlur(blur)))

            draw = ImageDraw.Draw(bg)
            # Hard rings
            draw.ellipse([AV_X - 5, AV_Y - 5, AV_X + AV + 5, AV_Y + AV + 5],
                         outline=(*CYAN, 255), width=3)
            draw.ellipse([AV_X - 9, AV_Y - 9, AV_X + AV + 9, AV_Y + AV + 9],
                         outline=(*MAGENTA, 140), width=1)

            bg.paste(av, (AV_X, AV_Y), av)
            draw = ImageDraw.Draw(bg)

            # Bot label below avatar
            bot_lbl = "AnnieX Music"
            bl_w = int(font_small.getlength(bot_lbl))
            bl_x = AV_X + (AV - bl_w) // 2
            draw.text((bl_x, AV_Y + AV + 8), bot_lbl, fill=(*CYAN, 220), font=font_small)
        except Exception:
            pass

    # ── "MADE BY KHUSHI" watermark ──────────────────────────────────────────────
    wm = "✦  MADE BY KHUSHI  ✦"
    wm_w = int(font_wm.getlength(wm))
    wm_x = (W - wm_w) // 2
    wm_y = H - 42

    # Glow
    for dx, alpha in [(3, 40), (0, 255)]:
        col = (*MAGENTA, alpha)
        draw.text((wm_x + dx, wm_y + dx), wm, fill=col, font=font_wm)

    # Decorative divider line above watermark
    dv_y = H - 58
    draw.line([(90, dv_y), (W - 90, dv_y)], fill=(60, 0, 90, 160), width=1)
    for dot_cx, dot_col in [(88, CYAN), (W - 88, MAGENTA)]:
        draw.ellipse([dot_cx - 4, dv_y - 4, dot_cx + 4, dv_y + 4], fill=dot_col)

    # ── Subtle corner grid lines (top-left) ────────────────────────────────────
    for i in range(1, 5):
        offset = i * 28
        draw.line([(offset, 0), (0, offset)], fill=(*CYAN, 18), width=1)

    # ── Cleanup + save ─────────────────────────────────────────────────────────
    try:
        os.remove(thumb_path)
    except OSError:
        pass

    bg.convert("RGB").save(cache_path)
    return cache_path
