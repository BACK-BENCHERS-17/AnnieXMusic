"""
KHUSHI — Centralised UI constants & message builders
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Single source of truth for all emojis, brand row, and
reusable blockquote message helpers.  Import from here everywhere.
"""

# ── Brand row (disabled — premium emojis are used inline instead) ───────────
BRAND = ""

# ── Premium emoji IDs (Telegram custom-emoji) ───────────────────────────────
# Each entry: (custom_emoji_id_or_None, unicode_fallback)
# The IDs below come from publicly-used Telegram premium emoji packs and have
# been validated in this project's history. If an ID is None, the plain
# unicode emoji is used (and you can supply the correct ID later).
_P = {
    # Status
    "check":     ("5852871561983299073", "✅"),
    "check2":    ("6041597085009056322", "✅"),
    "cross":     ("5040042498634810056", "❌"),
    "warn":      ("5420323339723881652", "⚠️"),
    "shield":    ("5895483165182529286", "🛡"),
    "ban":       ("5039671744172917707", "🚫"),
    "lock":      ("5472308992514464048", "🔐"),

    # Music / media
    "music":     ("5463107823946717464", "🎵"),
    "notes":     ("5039771357349413873", "🎶"),
    "notes2":    ("5938473438468378529", "🎶"),
    "mic":       ("5933678317935791830", "🎤"),
    "sax":       ("5467793203769933478", "🎷"),
    "headset":   ("5373074324779186371", "🎧"),
    "radio":     ("5373180492080903524", "📻"),
    "video":     ("5375464961822695044", "🎬"),
    "videocam":  ("5258217809250372293", "🎥"),
    "tv":        ("6044356915029348425", "📺"),
    "live":      ("5039937555403899813", "▶️"),
    "disc":      ("5462956611033117422", "📀"),

    # Actions / states
    "zap":       ("5042334757040423886", "⚡️"),
    "fire":      ("5347895529033462557", "🔥"),
    "star":      ("5356706551848769325", "🌟"),
    "sparkle":   ("5039827436737397847", "✨"),
    "dizzy":     ("5042200814190330758", "💫"),
    "diamond":   ("5368319008979943541", "💎"),
    "bell":      ("5386367538735104399", "🔔"),
    "announce":  ("6334406115341633473", "📢"),
    "bookmark":  ("5222444124698853913", "🔖"),
    "clock":     ("5123230779593196220", "⏰"),
    "hourglass": ("5420323339007281165", "⏳"),
    "timer":     ("5454415424319931791", "⌛️"),
    "search":    ("5395444784611480792", "🔍"),
    "link":      ("5373024494633049785", "🔗"),
    "crown":     ("5039727497143387500", "👑"),
    "gift":      ("5409029744693897259", "🎁"),
    "pin":       ("5472282911506501403", "📌"),
    "snow":      ("5449449325434266744", "❄️"),
    "heart":     ("5042225965518816316", "❤️‍🔥"),
    "rose":      ("6122692084806716730", "🌹"),
    "butterfly": ("5042131347389285520", "🦋"),
    "globe":     ("5316832074047441823", "🌐"),
    "user":      ("5316992572680320646", "👤"),
    "user2":     ("5884366771913233289", "👤"),
    "brain":     ("5237799019329105246", "🧠"),
    "tired":     ("5371077231823036079", "😫"),
    "download":  ("5776182936638329359", "📥"),
    "camera":    ("6048390817033228573", "📷"),
    "camera2":   ("5944753741512052670", "📷"),

    # Indicators
    "dot":       ("5972072533833289156", "🔹"),
    "arrow":     ("5197521876529545705", "➤"),
    "play_btn":  ("5346099622383056961", "▶"),
    "left":      ("4981358569468200584", "⬅️"),
    "right":     ("5474300135057925400", "➡️"),
    "repeat":    ("6030657343744644592", "🔁"),
    "shuffle":   ("5129905231785624480", "🔀"),
    "skip":      ("5373018274545775531", "⏭"),
    "prev":      ("5373040281539151958", "⏮"),
    "stop":      ("5371843862470941498", "⏹"),
    "pause":     ("5373103055199560996", "⏸"),
    "playpause": ("5373123633415854520", "⏯"),
    "queue":     ("6039454987250044861", "🔊"),
    "speed":     ("5373042927648818686", "🚀"),
    "seek_fwd":  ("6192553546102085729", "⏩"),
    "seek_bk":   ("5373054327609502403", "⏪"),

    # System / stats
    "ping":      ("5269563867305879894", "🏓"),
    "vc":        ("6093587384954262033", "📞"),
    "uptime":    ("6337029193603225180", "🕔"),
    "cpu":       ("5215186239853964761", "🖥"),
    "ram":       ("5834767463081840315", "🔵"),
    "disk":      ("5040036030414062506", "💬"),
    "stats":     ("4958506272551863292", "📊"),
    "stats2":    ("6093382540784046658", "📊"),
    "settings":  ("5895592588064328942", "⚙️"),
    "gear":      ("5258096772776991776", "⚙️"),
    "computer":  ("5972055534352733289", "💻"),
}


def _emoji(eid: str | None, fallback: str) -> str:
    """Wrap a unicode glyph as a Telegram premium custom-emoji entity.

    Telegram / Pyrogram's HTML parser only recognises the `<tg-emoji>` tag with
    an `emoji-id` attribute — anything else (e.g. `<emoji id="...">`) is
    silently stripped, leaving just the unicode fallback. Using the correct
    tag here makes every premium emoji actually render as a premium custom
    emoji for users on Telegram Premium clients (and as the unicode fallback
    elsewhere).
    """
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{fallback}</tg-emoji>'
    return fallback


# Public emoji map — values are ready-to-paste HTML strings
E = {key: _emoji(eid, fb) for key, (eid, fb) in _P.items()}


# ── Message builder helpers ──────────────────────────────────────────────────

def _box(content: str, expandable: bool = False) -> str:
    """Wrap content in a Telegram blockquote (optionally expandable)."""
    tag = "blockquote expandable" if expandable else "blockquote"
    return f"<{tag}>{content}</{tag}>"


def brand_block() -> str:
    """Brand header — disabled. Returns empty string for backward compatibility."""
    return ""


def msg(
    header: str,
    body: str,
    *,
    emoji_key: str = "dot",
    expandable: bool = False,
) -> str:
    """
    Build a clean single-blockquote message:

        ╔ emoji  header ╗
          body lines

    Usage::

        msg("ꜱᴇᴇᴋᴇᴅ", f"Jumped to <code>1:45</code>", emoji_key="zap")
    """
    em = E.get(emoji_key, E["dot"])
    inner = f"{em} <b>{header}</b>"
    if body:
        inner += f"\n{body}"
    return _box(inner, expandable=expandable)


def err(text: str) -> str:
    """Standard error message."""
    return msg("ᴇʀʀᴏʀ", text, emoji_key="cross")


def ok(text: str) -> str:
    """Standard success message."""
    return msg("sᴜᴄᴄᴇss", text, emoji_key="check")


def info(header: str, body: str = "", expandable: bool = False) -> str:
    """Standard info message."""
    return msg(header, body, emoji_key="dot", expandable=expandable)


def panel(title: str, rows: list[str], *, expandable: bool = False) -> str:
    """
    Build a box-drawing panel inside a blockquote:

        ┌── ˹ TITLE ˼ ──●
        ┆ emoji  row 1
        ┆ emoji  row 2
        └──────────────●

    ``rows`` is a list of already-formatted line strings (including emoji).
    """
    bar_open  = f"┌────── ˹ {title} ˼ ─── ⏤‌●"
    bar_close = "└──────────────────●"
    body = bar_open + "\n" + "\n".join(f"┆{r}" for r in rows) + "\n" + bar_close
    return _box(body, expandable=expandable)
