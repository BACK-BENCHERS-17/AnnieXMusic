import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch
from config import YOUTUBE_IMG_URL, BOT_USERNAME
from ANNIEMUSIC.core.dir import CACHE_DIR

W, H = 1280, 720

# ── Color palette (warm-neon mix from both references) ─────────────────────────
CYAN       = (0, 220, 255)
MAGENTA    = (255, 30, 180)
WHITE      = (255, 255, 255)
OFF_WHITE  = (230, 230, 245)
WARM_DARK  = (14, 8, 22, 220)
WARM_GLOW  = (120, 30, 60, 80)
SOFT_GRAY  = (165, 165, 185)
DIM_WHITE  = (200, 200, 220)
LIVE_RED   = (255, 70, 70)
GOLD       = (255, 210, 60)
VIEW_RED   = (200, 30, 30)

_FONT_BOLD = "ANNIEMUSIC/assets/thumb/font2.ttf"
_FONT_REG  = "ANNIEMUSIC/assets/thumb/font.ttf"


def _load_fonts():
    try:
        return (
            ImageFont.truetype(_FONT_BOLD, 40),   # [0] title
            ImageFont.truetype(_FONT_BOLD, 22),   # [1] badge / label key
            ImageFont.truetype(_FONT_REG,  20),   # [2] meta value
            ImageFont.truetype(_FONT_REG,  17),   # [3] small
            ImageFont.truetype(_FONT_BOLD, 21),   # [4] watermark
            ImageFont.truetype(_FONT_BOLD, 26),   # [5] channel / "NOW PLAYING"
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


def _glow(base, shape_fn, color_rgba, blur=18):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shape_fn(ImageDraw.Draw(layer), color_rgba)
    return Image.alpha_composite(base, layer.filter(ImageFilter.GaussianBlur(blur)))


def _circle_avatar(img, size):
    img = img.resize((size, size)).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img


def _draw_rounded_rect_outline(draw, box, radius, color, width=2):
    draw.rounded_rectangle(box, radius=radius, outline=color, width=width)


def _radial_gradient_bg(raw_blurred):
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    steps = 14
    cx, cy = W // 2, H // 2
    for i in range(steps, 0, -1):
        t   = i / steps
        r   = int(60 * t)
        g   = int(10 * t)
        b   = int(35 * t)
        a   = int(120 * t)
        rx  = int(W * 0.55 * t)
        ry  = int(H * 0.55 * t)
        gd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(r, g, b, a))
    return Image.alpha_composite(raw_blurred, grad)


async def get_thumb(videoid: str) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_v8.png")
    if os.path.exists(cache_path):
        return cache_path

    # ── Fetch YouTube metadata ─────────────────────────────────────────────────
    try:
        results_data = await VideosSearch(
            f"https://www.youtube.com/watch?v={videoid}", limit=1
        ).next()
        data     = (results_data.get("result") or [{}])[0]
        title    = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
        thumbnail= (data.get("thumbnails") or [{}])[0].get("url") or YOUTUBE_IMG_URL
        duration = data.get("duration")
        views    = (data.get("viewCount") or {}).get("short") or "Unknown"
        channel  = (data.get("channel") or {}).get("name") or "YouTube"
    except Exception:
        title, thumbnail, duration, views, channel = (
            "Unsupported Title", YOUTUBE_IMG_URL, None, "Unknown", "YouTube"
        )

    is_live      = not duration or str(duration).strip().lower() in {"", "live", "live now"}
    duration_txt = "● LIVE" if is_live else (duration or "—")

    # ── Download thumbnail ─────────────────────────────────────────────────────
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

    # ── Base: blurred + warmed bg ──────────────────────────────────────────────
    raw = Image.open(thumb_path).resize((W, H)).convert("RGBA")
    bg  = ImageEnhance.Brightness(
              raw.filter(ImageFilter.GaussianBlur(28))
          ).enhance(0.28).convert("RGBA")
    bg  = ImageEnhance.Color(bg).enhance(1.6)

    # Warm dark overlay
    overlay = Image.new("RGBA", (W, H), (12, 5, 24, 200))
    bg = Image.alpha_composite(bg, overlay)

    # Radial warm glow in center (from image 2)
    bg = _radial_gradient_bg(bg)

    # ── Neon top bar ──────────────────────────────────────────────────────────
    for thick, alpha in [(22, 35), (10, 85), (4, 255)]:
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(gl).line([(0, 0), (W, 0)], fill=(*CYAN, alpha), width=thick)
        bg = Image.alpha_composite(bg, gl)

    # ── Neon bottom bar ───────────────────────────────────────────────────────
    for thick, alpha in [(18, 35), (8, 85), (3, 255)]:
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(gl).line([(0, H - 1), (W, H - 1)], fill=(*MAGENTA, alpha), width=thick)
        bg = Image.alpha_composite(bg, gl)

    draw = ImageDraw.Draw(bg)

    # Corner accent dots
    for cx, cy, col in [(0, 0, CYAN), (W, 0, MAGENTA), (0, H, MAGENTA), (W, H, CYAN)]:
        draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=col)

    # ══════════════════════════════════════════════════════════════════════════
    # LEFT: Large album art  (image-2 style: big square card)
    # ══════════════════════════════════════════════════════════════════════════
    TX, TY, TW, TH, TR = 48, 95, 490, 490, 26

    # Outer warm glow behind art
    bg = _glow(bg,
        lambda d, col: d.rounded_rectangle(
            [TX - 18, TY - 18, TX + TW + 18, TY + TH + 18],
            radius=TR + 12, fill=col),
        (*MAGENTA, 45), blur=28)

    # Outer magenta ring
    gl2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl2).rounded_rectangle(
        [TX - 5, TY - 5, TX + TW + 5, TY + TH + 5],
        radius=TR + 5, outline=(*MAGENTA, 200), width=3)
    bg = Image.alpha_composite(bg, gl2)

    # Inner cyan ring
    gl3 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl3).rounded_rectangle(
        [TX - 10, TY - 10, TX + TW + 10, TY + TH + 10],
        radius=TR + 10, outline=(*CYAN, 90), width=1)
    bg = Image.alpha_composite(bg, gl3)

    # Paste album art
    thumb_img = raw.resize((TW, TH))
    t_mask = Image.new("L", (TW, TH), 0)
    ImageDraw.Draw(t_mask).rounded_rectangle((0, 0, TW, TH), radius=TR, fill=255)
    bg.paste(thumb_img, (TX, TY), t_mask)
    draw = ImageDraw.Draw(bg)

    # Views badge on art (image-2 style: red pill bottom-left of art)
    views_badge = f"  {views} Views  "
    vb_w = int(font_tiny.getlength(views_badge)) + 4
    vb_x, vb_y = TX + 12, TY + TH - 38
    draw.rounded_rectangle([vb_x, vb_y, vb_x + vb_w, vb_y + 26], radius=7, fill=(*VIEW_RED, 220))
    draw.text((vb_x + 8, vb_y + 5), views_badge.strip(), fill=WHITE, font=font_tiny)

    # "NOW PLAYING" badge on art (top-left of art, image-2 style)
    np_txt = "♫  NOW PLAYING"
    np_w   = int(font_tiny.getlength(np_txt)) + 16
    np_x, np_y = TX + 12, TY + 12
    draw.rounded_rectangle([np_x, np_y, np_x + np_w, np_y + 24], radius=5,
                            fill=(0, 0, 0, 170))
    draw.text((np_x + 8, np_y + 4), np_txt, fill=(*CYAN, 255), font=font_tiny)

    # ══════════════════════════════════════════════════════════════════════════
    # RIGHT: Info panel (image-2 style layout)
    # ══════════════════════════════════════════════════════════════════════════
    IX, IY = 578, 95
    IW = 640

    # Dark semi-transparent panel
    ip = Image.new("RGBA", (IW, 500), (10, 6, 28, 180))
    ip_mask = Image.new("L", (IW, 500), 0)
    ImageDraw.Draw(ip_mask).rounded_rectangle((0, 0, IW, 500), radius=24, fill=255)
    bg.paste(ip, (IX - 16, IY - 16), ip_mask)

    # Left accent bar (neon cyan glow, like original)
    for thick, alpha in [(20, 30), (9, 75), (3, 255)]:
        gl4 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(gl4).line(
            [(IX - 18, IY - 4), (IX - 18, IY + 460)],
            fill=(*CYAN, alpha), width=thick)
        bg = Image.alpha_composite(bg, gl4)
    draw = ImageDraw.Draw(bg)

    # ── "NOW PLAYING" label (image-2: small gray uppercase)
    draw.text((IX, IY + 4), "NOW PLAYING", fill=(*SOFT_GRAY, 200), font=font_tiny)

    # Thin underline below label
    np_lbl_w = int(font_tiny.getlength("NOW PLAYING"))
    draw.line([(IX, IY + 24), (IX + np_lbl_w, IY + 24)], fill=(*CYAN, 120), width=1)

    # ── Title (large bold white, image-2 style)
    title_y = IY + 36
    title_line1 = trim_to_width(title, font_title, IW - 8)
    # Shadow effect
    draw.text((IX + 2, title_y + 2), title_line1, fill=(0, 0, 0, 120), font=font_title)
    draw.text((IX, title_y), title_line1, fill=WHITE, font=font_title)

    # ── Divider (image-2 style: full-width thin line)
    div1_y = title_y + 56
    draw.line([(IX, div1_y), (IX + IW - 20, div1_y)], fill=(60, 40, 90, 200), width=1)

    # ── Channel / Artist name
    ch_y = div1_y + 14
    ch_txt = trim_to_width(f"◈  {channel}", font_channel, IW - 10)
    draw.text((IX, ch_y), ch_txt, fill=(*CYAN, 220), font=font_channel)

    # ── Duration row (image-2 style: label : value)
    row1_y = ch_y + 46
    draw.text((IX, row1_y), "Duration :", fill=(*SOFT_GRAY, 200), font=font_badge)
    dur_col = LIVE_RED if is_live else OFF_WHITE
    draw.text((IX + 130, row1_y), duration_txt, fill=dur_col, font=font_badge)

    # ── Views row
    row2_y = row1_y + 36
    draw.text((IX, row2_y), "Views :", fill=(*SOFT_GRAY, 200), font=font_badge)
    draw.text((IX + 130, row2_y), f"{views} views", fill=OFF_WHITE, font=font_badge)

    # ── Progress bar (image-2 style: wider, prominent slider)
    div2_y = row2_y + 40
    draw.line([(IX, div2_y), (IX + IW - 20, div2_y)], fill=(60, 40, 90, 200), width=1)

    PBX   = IX
    PBY   = div2_y + 18
    PB_W  = IW - 24
    PB_H  = 8
    PLAYED = int(PB_W * 0.38)

    # Track bg
    draw.rounded_rectangle([PBX, PBY, PBX + PB_W, PBY + PB_H], radius=4, fill=(40, 30, 70, 255))

    # Gradient fill cyan → magenta
    grad_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd2 = ImageDraw.Draw(grad_l)
    for i in range(PLAYED):
        t = i / max(PLAYED - 1, 1)
        r = int(0   + 255 * t)
        g = int(220 - 190 * t)
        b = int(255 - 75  * t)
        gd2.line([(PBX + i, PBY), (PBX + i, PBY + PB_H)], fill=(r, g, b, 255))
    bg = Image.alpha_composite(bg, grad_l)
    draw = ImageDraw.Draw(bg)

    # Playhead dot (image-2 has a toggle/circle)
    dot_x = PBX + PLAYED
    dot_y = PBY + PB_H // 2
    for r_sz, alp in [(18, 45), (11, 110)]:
        gl5 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(gl5).ellipse(
            [dot_x - r_sz, dot_y - r_sz, dot_x + r_sz, dot_y + r_sz],
            fill=(*CYAN, alp))
        bg = Image.alpha_composite(bg, gl5.filter(ImageFilter.GaussianBlur(5)))
    draw = ImageDraw.Draw(bg)
    draw.ellipse([dot_x - 8, dot_y - 8, dot_x + 8, dot_y + 8], fill=WHITE)
    draw.ellipse([dot_x - 4, dot_y - 4, dot_x + 4, dot_y + 4], fill=(*CYAN, 200))

    # Time stamps
    tm_y = PBY + 14
    draw.text((PBX, tm_y), "00:00", fill=SOFT_GRAY, font=font_tiny)
    end_lbl_w = int(font_tiny.getlength(duration_txt))
    draw.text((PBX + PB_W - end_lbl_w, tm_y), duration_txt,
              fill=LIVE_RED if is_live else SOFT_GRAY, font=font_tiny)

    # ── Platform badge (▶ YouTube pill)
    plat_y = PBY + 38
    badge = "▶  YouTube"
    bw2 = int(font_tiny.getlength(badge)) + 22
    draw.rounded_rectangle([IX, plat_y, IX + bw2, plat_y + 24], radius=7,
                            fill=(0, 130, 255, 210))
    draw.text((IX + 11, plat_y + 4), badge, fill=WHITE, font=font_tiny)

    # ══════════════════════════════════════════════════════════════════════════
    # TOP-RIGHT: Bot avatar (from original code, now with username)
    # ══════════════════════════════════════════════════════════════════════════
    avatar_path = (
        "ANNIEMUSIC/assets/bot_pfp.png"
        if os.path.isfile("ANNIEMUSIC/assets/bot_pfp.png")
        else "ANNIEMUSIC/assets/upic.png"
    )
    AV   = 92
    AV_X = W - AV - 24
    AV_Y = 18

    if os.path.isfile(avatar_path):
        try:
            av = _circle_avatar(Image.open(avatar_path), AV)

            # Outer glow rings
            for ring_r, ring_a, blur in [(AV + 28, 45, 16), (AV + 14, 90, 9)]:
                rgl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                cx2 = AV_X + AV // 2
                cy2 = AV_Y + AV // 2
                ImageDraw.Draw(rgl).ellipse(
                    [cx2 - ring_r // 2, cy2 - ring_r // 2,
                     cx2 + ring_r // 2, cy2 + ring_r // 2],
                    fill=(*CYAN, ring_a))
                bg = Image.alpha_composite(bg, rgl.filter(ImageFilter.GaussianBlur(blur)))

            draw = ImageDraw.Draw(bg)
            draw.ellipse([AV_X - 5, AV_Y - 5, AV_X + AV + 5, AV_Y + AV + 5],
                         outline=(*CYAN, 255), width=3)
            draw.ellipse([AV_X - 9, AV_Y - 9, AV_X + AV + 9, AV_Y + AV + 9],
                         outline=(*MAGENTA, 130), width=1)
            bg.paste(av, (AV_X, AV_Y), av)
            draw = ImageDraw.Draw(bg)

            # Bot name below avatar (from BOT_NAME or fallback)
            _bot_lbl = "AnnieXMusic"
            bl_w     = int(font_tiny.getlength(_bot_lbl))
            bl_x     = AV_X + (AV - bl_w) // 2
            draw.text((bl_x, AV_Y + AV + 7), _bot_lbl, fill=(*CYAN, 215), font=font_tiny)

            # @username below bot name
            _bot_un = f"@{BOT_USERNAME}" if BOT_USERNAME else "@AnnieXMusicXBot"
            un_w    = int(font_tiny.getlength(_bot_un))
            un_x    = AV_X + (AV - un_w) // 2
            draw.text((un_x, AV_Y + AV + 26), _bot_un, fill=(*SOFT_GRAY, 180), font=font_tiny)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # BOTTOM-LEFT: @username watermark (image-1 style)
    # ══════════════════════════════════════════════════════════════════════════
    _un_bl = f"@{BOT_USERNAME}" if BOT_USERNAME else "@AnnieXMusicXBot"
    draw.text((18, H - 36), _un_bl, fill=(*CYAN, 180), font=font_small)

    # ══════════════════════════════════════════════════════════════════════════
    # BOTTOM-CENTER: "✦ MADE BY KHUSHI ✦" (magenta glow watermark)
    # ══════════════════════════════════════════════════════════════════════════
    wm   = "✦  MADE BY KHUSHI  ✦"
    wm_w = int(font_wm.getlength(wm))
    wm_x = (W - wm_w) // 2
    wm_y = H - 40

    # Glow pass
    draw.text((wm_x + 2, wm_y + 2), wm, fill=(*MAGENTA, 45), font=font_wm)
    draw.text((wm_x, wm_y), wm, fill=(*MAGENTA, 255), font=font_wm)

    # Decorative divider
    dv_y = H - 56
    draw.line([(80, dv_y), (W - 80, dv_y)], fill=(80, 0, 100, 140), width=1)
    for dot_cx, dot_col in [(78, CYAN), (W - 78, MAGENTA)]:
        draw.ellipse([dot_cx - 4, dv_y - 4, dot_cx + 4, dv_y + 4], fill=dot_col)

    # ── Subtle corner grid lines (top-left accent)
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
