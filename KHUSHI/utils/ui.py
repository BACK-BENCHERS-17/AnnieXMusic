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
    "check":     ("5367867546025223117", "✅"),
    "cross":     ("5210952531676504517", "❌"),
    "warn":      ("5467666044815377227", "⚠️"),
    "shield":    ("5895483165182529286", "🛡"),
    "ban":       ("5039671744172917707", "🚫"),
    "lock":      ("5381645965313085884", "🔒"),

    # Music / media
    "music":     ("5188093600538057635", "🎵"),
    "notes":     ("5373123168026207226", "🎶"),
    "mic":       ("5357418988672927257", "🎙"),
    "headset":   ("5373074324779186371", "🎧"),
    "radio":     ("5373180492080903524", "📻"),
    "video":     ("5375464961822695044", "🎬"),
    "videocam":  ("5258217809250372293", "🎥"),
    "live":      ("5346027782059532469", "▶️"),
    "disc":      ("5462956611033117422", "📀"),

    # Actions / states
    "zap":       ("5042334757040423886", "⚡️"),
    "fire":      ("5347895529033462557", "🔥"),
    "star":      ("5356706551848769325", "🌟"),
    "sparkle":   ("5432693215988770596", "✨"),
    "diamond":   ("5368319008979943541", "💎"),
    "bell":      ("5386367538735104399", "🔔"),
    "clock":     ("5434890496440903643", "⏰"),
    "hourglass": ("5420323339007281165", "⏳"),
    "timer":     ("5454415424319931791", "⌛️"),
    "search":    ("5395444784611480792", "🔍"),
    "link":      ("5373024494633049785", "🔗"),
    "crown":     ("5394892612508411389", "👑"),
    "gift":      ("5409029744693897259", "🎁"),
    "pin":       ("5472282911506501403", "📌"),
    "snow":      ("5449449325434266744", "❄️"),
    "heart":     ("5039598514980520994", "❤️‍🔥"),
    "rose":      ("6122692084806716730", "🌹"),
    "globe":     ("5372981976804366741", "🌐"),
    "user":      ("5316992572680320646", "👤"),
    "brain":     ("5237799019329105246", "🧠"),
    "download":  ("5310181805966167157", "📥"),

    # Indicators
    "dot":       ("5972072533833289156", "🔹"),
    "arrow":     ("5197521876529545705", "➤"),
    "play_btn":  ("5346099622383056961", "▶"),
    "repeat":    ("5373150762449421436", "🔁"),
    "shuffle":   ("5370894089711388826", "🔀"),
    "skip":      ("5373018274545775531", "⏭"),
    "prev":      ("5373040281539151958", "⏮"),
    "stop":      ("5371843862470941498", "⏹"),
    "pause":     ("5373103055199560996", "⏸"),
    "playpause": ("5373123633415854520", "⏯"),
    "queue":     ("5350982073854661706", "🔊"),
    "speed":     ("5373042927648818686", "🚀"),
    "seek_fwd":  ("5349880790124955266", "⏩"),
    "seek_bk":   ("5373054327609502403", "⏪"),

    # System / stats
    "ping":      ("5269563867305879894", "🏓"),
    "vc":        ("5226772700113935347", "📞"),
    "uptime":    ("6337029193603225180", "🕔"),
    "cpu":       ("5215186239853964761", "🖥"),
    "ram":       ("5834767463081840315", "🔵"),
    "disk":      ("5116468787377341336", "💬"),
    "stats":     ("4958506272551863292", "📊"),
    "settings":  ("5258096772776991776", "⚙️"),
    "computer":  ("5972055534352733289", "💻"),
}


def _emoji(eid: str | None, fallback: str) -> str:
    """Wrap a unicode glyph as a Telegram premium emoji entity if an ID is set."""
    if eid:
        return f'<emoji id="{eid}">{fallback}</emoji>'
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
