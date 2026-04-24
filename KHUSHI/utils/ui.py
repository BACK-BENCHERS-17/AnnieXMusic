"""
KHUSHI — Centralised UI constants & message builders
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Single source of truth for all emojis, brand row, and
reusable blockquote message helpers.  Import from here everywhere.
"""

# ── Brand row (disabled — premium emojis are used inline instead) ───────────
BRAND = "<blockquote>🎵 <b>ᴀɴɴɪᴇ</b></blockquote>\n"

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


# ── Unicode → premium-emoji-ID reverse map ──────────────────────────────────
# Used by `install_emoji_autowrap()` to upgrade plain unicode glyphs in any
# outgoing message into Telegram premium custom emojis automatically.
import re as _re

_UNICODE_TO_ID: dict[str, str] = {}
for _key, (_eid, _fb) in _P.items():
    if not (_eid and _fb):
        continue
    # Register the glyph as-is and also its with/without Variation-Selector-16
    # (U+FE0F) form, since users (and YAML strings) sometimes omit VS16 while
    # premium emoji IDs were registered against the VS16 form (or vice-versa).
    _variants = {_fb}
    if "\ufe0f" in _fb:
        _variants.add(_fb.replace("\ufe0f", ""))
    else:
        _variants.add(_fb + "\ufe0f")
    for _v in _variants:
        _UNICODE_TO_ID.setdefault(_v, _eid)

# ── Extra aliases ───────────────────────────────────────────────────────────
# Many plugins use related but slightly-different glyphs (e.g. 🎙 studio mic
# vs 🎤 microphone, 📍 round pin vs 📌 pushpin) that aren't in `_P`. Map them
# to the closest existing premium emoji ID so EVERY unicode glyph in any
# outgoing message gets upgraded to a premium custom emoji.
_EXTRA_ALIASES: dict[str, str] = {
    # Music / mics
    "🎙":  _P["mic"][0],            # studio mic → mic
    "🎙️": _P["mic"][0],
    "🔇":  _P["queue"][0],          # muted speaker → speaker
    "🔈":  _P["queue"][0],
    "🔉":  _P["queue"][0],
    "🔊":  _P["queue"][0],
    "📹":  _P["videocam"][0],       # video camera
    "🎞":  _P["video"][0],          # film frames
    "🎞️": _P["video"][0],
    # Hearts / love
    "❤":  _P["heart"][0],           # red heart (no VS16) → heart_on_fire
    "❤️": _P["heart"][0],           # red heart (VS16)
    "💖": _P["heart"][0],
    "💗": _P["heart"][0],
    "💘": _P["heart"][0],
    "💝": _P["heart"][0],
    "🩷": _P["heart"][0],
    # Pins / bookmarks / mail
    "📍": _P["pin"][0],             # round pushpin → pushpin
    "📋": _P["stats"][0],           # clipboard → stats
    "📭": _P["bookmark"][0],        # mailbox → bookmark
    "📬": _P["bookmark"][0],
    "📨": _P["announce"][0],
    # Alerts
    "🚨": _P["warn"][0],            # rotating light → warn
    "🆘": _P["warn"][0],
    "‼":  _P["warn"][0],
    "‼️": _P["warn"][0],
    # Arrows
    "⬇":  _P["download"][0],
    "⬇️": _P["download"][0],
    "⬆":  _P["arrow"][0],
    "⬆️": _P["arrow"][0],
    "↑":  _P["arrow"][0],
    "↓":  _P["download"][0],
    "→":  _P["right"][0],
    "←":  _P["left"][0],
    "➥":  _P["right"][0],
    "➻":  _P["right"][0],
    "↬":  _P["right"][0],
    "➡":  _P["right"][0],
    "⬅":  _P["left"][0],
    "↻":  _P["repeat"][0],
    "🔄": _P["repeat"][0],
    # Misc
    "✓":  _P["check"][0],
    "✔":  _P["check"][0],
    "✔️": _P["check"][0],
    "✗":  _P["cross"][0],
    "✖":  _P["cross"][0],
    "✖️": _P["cross"][0],
    "⏤":  _P["dot"][0],
    "•":  _P["dot"][0],
    "▪":  _P["dot"][0],
    "▫":  _P["dot"][0],
    "🌹": _P["rose"][0] if "rose" in _P else _P["heart"][0],
}
for _g, _eid in _EXTRA_ALIASES.items():
    _UNICODE_TO_ID.setdefault(_g, _eid)
    if "\ufe0f" in _g:
        _UNICODE_TO_ID.setdefault(_g.replace("\ufe0f", ""), _eid)
    else:
        _UNICODE_TO_ID.setdefault(_g + "\ufe0f", _eid)

# Longest-glyph-first so multi-codepoint emojis (e.g. ❤️‍🔥, ⚡️ with VS16)
# match before their single-codepoint variants.
_SORTED_GLYPHS = sorted(_UNICODE_TO_ID.keys(), key=len, reverse=True)
_GLYPH_RE = (
    _re.compile("(?:" + "|".join(_re.escape(g) for g in _SORTED_GLYPHS) + ")")
    if _SORTED_GLYPHS else None
)


def _augment_with_custom_emoji(message: str, entities):
    """Add MessageEntityCustomEmoji entries for every known unicode glyph in
    `message`, while leaving any pre-existing entities untouched.

    Telegram entity offsets and lengths are measured in **UTF-16 code units**,
    not Python characters, so we encode the prefix and the glyph in
    ``utf-16-le`` and divide by 2.
    """
    if not _GLYPH_RE or not message:
        return entities or []
    try:
        from pyrogram.raw.types import MessageEntityCustomEmoji
    except Exception:
        return entities or []

    new_entities = list(entities or [])
    # Skip glyph occurrences that already have a CustomEmoji entity covering
    # them (e.g. when the source already used a <tg-emoji> tag).
    occupied = {
        (getattr(e, "offset", -1), getattr(e, "length", 0))
        for e in new_entities
        if e.__class__.__name__ == "MessageEntityCustomEmoji"
    }

    for m in _GLYPH_RE.finditer(message):
        glyph = m.group(0)
        eid = _UNICODE_TO_ID.get(glyph)
        if not eid:
            continue
        offset = len(message[:m.start()].encode("utf-16-le")) // 2
        length = len(glyph.encode("utf-16-le")) // 2
        if (offset, length) in occupied:
            continue
        new_entities.append(
            MessageEntityCustomEmoji(
                offset=offset, length=length, document_id=int(eid)
            )
        )
    return new_entities


_AUTOWRAP_INSTALLED = False


def install_emoji_autowrap() -> None:
    """Monkeypatch Pyrogram's parser so every outgoing message — regardless of
    parse mode (HTML / Markdown / Default) — gets premium custom-emoji
    entities for any known unicode glyph it contains.

    We patch THREE entry points so every code path is covered:

    * `Parser.parse`        — the high-level dispatcher used by every
                              high-level Pyrogram method (send_message,
                              send_photo caption, edit_text, etc).
    * `HTML.parse`          — used directly by `KHUSHI/utils/raw_send.py`
                              (the invert-media trick for /play, /song,
                              now-playing notifications) and any other
                              caller that constructs an `HTML(client)`
                              instance and calls `.parse()` themselves.
    * `Markdown.parse`      — same idea for any direct Markdown caller.

    Dedup in `_augment_with_custom_emoji` (offset/length tracking) prevents
    double-wrapping when both HTML.parse and Parser.parse run on the same
    message.

    Idempotent: safe to call multiple times.
    """
    global _AUTOWRAP_INSTALLED
    if _AUTOWRAP_INSTALLED:
        return

    def _wrap_parse_method(cls, method_name: str = "parse"):
        """Monkey-patch ``cls.<method_name>`` so its return value has its
        entities augmented with premium custom-emoji entries. Works for any
        async method whose return value is a ``{"message": ..., "entities":
        ...}`` dict."""
        try:
            orig = getattr(cls, method_name)
        except AttributeError:
            return
        if getattr(orig, "_emoji_autowrap_installed", False):
            return

        async def _patched(self, *args, **kwargs):
            result = await orig(self, *args, **kwargs)
            try:
                if isinstance(result, dict):
                    result["entities"] = _augment_with_custom_emoji(
                        result.get("message", ""), result.get("entities")
                    )
            except Exception:
                pass
            return result

        _patched._emoji_autowrap_installed = True
        setattr(cls, method_name, _patched)

    try:
        from pyrogram.parser.parser import Parser
        _wrap_parse_method(Parser)
    except Exception:
        pass
    try:
        from pyrogram.parser.html import HTML
        _wrap_parse_method(HTML)
    except Exception:
        pass
    try:
        from pyrogram.parser.markdown import Markdown
        _wrap_parse_method(Markdown)
    except Exception:
        pass

    _AUTOWRAP_INSTALLED = True


# ── Message builder helpers ──────────────────────────────────────────────────

def _box(content: str, expandable: bool = False) -> str:
    """Wrap content in a Telegram blockquote (optionally expandable)."""
    tag = "blockquote expandable" if expandable else "blockquote"
    return f"<{tag}>{content}</{tag}>"


def brand_block() -> str:
    """Return the standard ANNIE brand header (premium-emoji enabled).

    The 🎵 glyph maps to a premium custom-emoji ID via ``_UNICODE_TO_ID``
    so the autowrap parser will render it as a Telegram premium emoji on
    every outgoing message that contains this block.
    """
    return BRAND


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
