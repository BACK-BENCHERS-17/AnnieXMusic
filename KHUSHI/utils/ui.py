"""
KHUSHI — Centralised UI constants & message builders
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Single source of truth for all emojis, brand row, and
reusable blockquote message helpers.  Import from here everywhere.
"""

# ── Brand row (disabled — premium emojis are used inline instead) ───────────
BRAND = ""

# ── Emoji set ────────────────────────────────────────────────────────────────
E = {
    # Status
    "check":    "✅",
    "cross":    "❌",
    "warn":     "⚠️",
    "shield":   "🛡",
    "ban":      "🚫",
    "lock":     "🔒",

    # Music / media
    "music":    "🎵",
    "notes":    "🎶",
    "mic":      "🎙",
    "headset":  "🎧",
    "radio":    "📻",
    "video":    "🎬",
    "live":     "▶️",

    # Actions / states
    "zap":      "⚡",
    "fire":     "🔥",
    "star":     "🌟",
    "sparkle":  "✨",
    "diamond":  "💎",
    "bell":     "🔔",
    "clock":    "⏰",
    "hourglass":"⏳",
    "search":   "🔍",
    "link":     "🔗",
    "crown":    "👑",
    "gift":     "🎁",
    "pin":      "📌",

    # Indicators
    "dot":      "🔹",
    "arrow":    "➤",
    "play_btn": "▶",
    "repeat":   "🔁",
    "shuffle":  "🔀",
    "skip":     "⏭",
    "prev":     "⏮",
    "stop":     "⏹",
    "pause":    "⏸",
    "queue":    "🔊",
    "speed":    "🚀",
    "seek_fwd": "⏩",
    "seek_bk":  "⏪",
}


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
