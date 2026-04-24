"""
KHUSHI — Centralised UI constants & message builders
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Single source of truth for all emojis, brand row, and
reusable blockquote message helpers.  Import from here everywhere.
"""

# ── Brand row — 🧸 ANNIE in Telegram premium custom-emoji letters ──────────
# Rendered as styled premium glyphs on Telegram Premium clients, falls back to
# the wrapped fallback character (here: the actual letter A/N/N/I/E) on
# non-premium clients so it still reads cleanly as "🧸 ANNIE".
BRAND = (
    "<blockquote>"
    '<tg-emoji emoji-id="5042192219960771668">🧸</tg-emoji> '
    '<tg-emoji emoji-id="5210820276748566172">A</tg-emoji>'
    '<tg-emoji emoji-id="5213301251722203632">N</tg-emoji>'
    '<tg-emoji emoji-id="5213301251722203632">N</tg-emoji>'
    '<tg-emoji emoji-id="5211032856154885824">I</tg-emoji>'
    '<tg-emoji emoji-id="5213337333742454261">E</tg-emoji>'
    "</blockquote>\n"
)

# ── Premium emoji IDs (Telegram custom-emoji) ───────────────────────────────
# Each entry: (custom_emoji_id, unicode_fallback)
# All IDs below have been **validated by the bot owner** as accessible to
# this bot account. Using any non-validated ID causes Telegram to reject
# the entire message with `ENTITY_TEXT_INVALID`, which then triggers the
# reactive fallback to strip ALL custom-emoji entities → user sees plain
# unicode. So when adding new keys, only use IDs from this validated pool.
# Keys whose closest matching premium emoji isn't in the validated pool
# are mapped to the nearest sibling (e.g. 🎧 → 🎵, 🚀 → ⚡, 📌 → 🔖).
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
    "music2":    ("6199299341996268244", "🎵"),
    "music3":    ("5994566609002303309", "🎵"),
    "notes":     ("5039771357349413873", "🎶"),
    "notes2":    ("5938473438468378529", "🎶"),
    "mic":       ("5933678317935791830", "🎤"),
    "mic2":      ("6030722571412967168", "🎤"),
    "sax":       ("5467793203769933478", "🎷"),
    "headset":   ("5463107823946717464", "🎧"),       # validated → 🎵
    "radio":     ("5463107823946717464", "📻"),       # validated → 🎵
    "video":     ("5375464961822695044", "🎬"),
    "videocam":  ("5258217809250372293", "🎥"),
    "tv":        ("6044356915029348425", "📺"),
    "live":      ("5039937555403899813", "▶️"),
    "disc":      ("5462956611033117422", "📀"),

    # Actions / states
    "zap":       ("5042334757040423886", "⚡️"),
    "fire":      ("5039644681583985437", "🔥"),
    "star":      ("5039827436737397847", "🌟"),       # validated → ✨
    "sparkle":   ("5039827436737397847", "✨"),
    "dizzy":     ("5042200814190330758", "💫"),
    "diamond":   ("5039827436737397847", "💎"),       # validated → ✨
    "bell":      ("6334406115341633473", "🔔"),       # validated → 📢
    "announce":  ("6334406115341633473", "📢"),
    "bookmark":  ("5222444124698853913", "🔖"),
    "clock":     ("5123230779593196220", "⏰"),
    "hourglass": ("5454415424319931791", "⏳"),       # validated → ⌛
    "timer":     ("5454415424319931791", "⌛️"),
    "search":    ("5972072533833289156", "🔍"),       # validated → 🔹
    "link":      ("5972072533833289156", "🔗"),       # validated → 🔹
    "crown":     ("5039727497143387500", "👑"),
    "gift":      ("5409029744693897259", "🎁"),
    "gift2":     ("5190745930319554349", "🎁"),
    "pin":       ("5222444124698853913", "📌"),       # validated → 🔖
    "snow":      ("5449449325434266744", "❄️"),
    "heart":     ("5042225965518816316", "❤️‍🔥"),
    "rose":      ("6122692084806716730", "🌹"),
    "butterfly": ("5042131347389285520", "🦋"),
    "globe":     ("5316832074047441823", "🌐"),
    "user":      ("5316992572680320646", "👤"),
    "user2":     ("5884366771913233289", "👤"),
    "brain":     ("5237799019329105246", "🧠"),
    "tired":     ("5371077231823036079", "😫"),
    "cool":      ("5424663180838182778", "😎"),
    "poop":      ("6307831155521494118", "💩"),
    "download":  ("5776182936638329359", "📥"),
    "camera":    ("6048390817033228573", "📷"),
    "camera2":   ("6048390817033228573", "📷"),

    # Indicators
    "dot":       ("5972072533833289156", "🔹"),
    "arrow":     ("5474300135057925400", "➤"),       # validated → ➡
    "play_btn":  ("5039937555403899813", "▶"),       # validated → ▶️
    "left":      ("4981358569468200584", "⬅️"),
    "right":     ("5474300135057925400", "➡️"),
    "repeat":    ("6030657343744644592", "🔁"),
    "shuffle":   ("5129905231785624480", "🔀"),
    "skip":      ("6192553546102085729", "⏭"),       # validated → ⏩
    "prev":      ("4981358569468200584", "⏮"),       # validated → ⬅
    "stop":      ("5040042498634810056", "⏹"),       # validated → ❌
    "pause":     ("5039937555403899813", "⏸"),       # validated → ▶️
    "playpause": ("5039937555403899813", "⏯"),       # validated → ▶️
    "queue":     ("6039454987250044861", "🔊"),
    "speed":     ("5042334757040423886", "🚀"),       # validated → ⚡
    "seek_fwd":  ("6192553546102085729", "⏩"),
    "seek_bk":   ("4981358569468200584", "⏪"),       # validated → ⬅

    # System / stats
    "ping":      ("5269563867305879894", "🏓"),
    "vc":        ("6093587384954262033", "📞"),
    "vc2":       ("5226772700113935347", "📞"),
    "uptime":    ("6337029193603225180", "🕔"),
    "cpu":       ("5215186239853964761", "🖥"),
    "ram":       ("5834767463081840315", "🔵"),
    "disk":      ("5040036030414062506", "💬"),
    "speech":    ("5116468787377341336", "💬"),
    "stats":     ("4958506272551863292", "📊"),
    "stats2":    ("6093382540784046658", "📊"),
    "stats3":    ("5231200819986047254", "📊"),
    "settings":  ("5895592588064328942", "⚙️"),
    "gear":      ("5258096772776991776", "⚙️"),
    "computer":  ("5972055534352733289", "💻"),

    # Brand
    "teddy":     ("5042192219960771668", "🧸"),
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
    # Brand teddy
    "🧸": _P["teddy"][0],
    # Heavier crosses & bans
    "⛔":  _P["ban"][0],
    "⛔️": _P["ban"][0],
    "✘":  _P["cross"][0],
    "🚷": _P["ban"][0],
    "🛑": _P["ban"][0],
    # Plus / add
    "✚":  _P["check"][0],
    "➕": _P["check"][0],
    "➖": _P["cross"][0],
    # House / home
    "🏠": _P["dot"][0],
    "🏡": _P["dot"][0],
    # Coloured circles → fire / dot
    "🔴": _P["fire"][0],
    "🟢": _P["check"][0],
    "🟡": _P["warn"][0],
    "🟠": _P["fire"][0],
    "🟣": _P["dizzy"][0],
    "🟤": _P["dot"][0],
    "⚫": _P["dot"][0],
    "⚪": _P["dot"][0],
    "🔵": _P["ram"][0],
    "🟥": _P["fire"][0],
    "🟦": _P["ram"][0],
    "🟧": _P["fire"][0],
    "🟨": _P["warn"][0],
    "🟩": _P["check"][0],
    "🟪": _P["dizzy"][0],
    "🟫": _P["dot"][0],
    "⬛": _P["dot"][0],
    "⬜": _P["dot"][0],
    # Clock faces → clock
    "🕐": _P["clock"][0], "🕑": _P["clock"][0], "🕒": _P["clock"][0],
    "🕓": _P["clock"][0], "🕔": _P["clock"][0], "🕕": _P["clock"][0],
    "🕖": _P["clock"][0], "🕗": _P["clock"][0], "🕘": _P["clock"][0],
    "🕙": _P["clock"][0], "🕚": _P["clock"][0], "🕛": _P["clock"][0],
    "🕜": _P["clock"][0], "🕝": _P["clock"][0], "🕞": _P["clock"][0],
    "🕟": _P["clock"][0], "🕠": _P["clock"][0], "🕡": _P["clock"][0],
    "🕢": _P["clock"][0], "🕣": _P["clock"][0], "🕤": _P["clock"][0],
    "🕥": _P["clock"][0], "🕦": _P["clock"][0], "🕧": _P["clock"][0],
    "⏱":  _P["clock"][0], "⏱️": _P["clock"][0],
    "⏲":  _P["timer"][0], "⏲️": _P["timer"][0],
    # Music card-suit & note
    "♥":  _P["heart"][0], "♥️": _P["heart"][0],
    "♦":  _P["diamond"][0], "♦️": _P["diamond"][0],
    "♣":  _P["dot"][0],
    "♠":  _P["dot"][0],
    "♪":  _P["notes"][0],
    "♫":  _P["notes"][0],
    "♬":  _P["notes"][0],
    "♩":  _P["notes"][0],
    # Misc symbols frequently used decoratively
    "🗳":  _P["stats"][0], "🗳️": _P["stats"][0],
    "🍓": _P["heart"][0],
    "🎯": _P["fire"][0],
    "💯": _P["fire"][0],
    "🎉": _P["sparkle"][0],
    "🎊": _P["sparkle"][0],
    "🎈": _P["sparkle"][0],
    # Stop / play / pause unicode singletons
    "⏹":  _P["stop"][0], "⏹️": _P["stop"][0],
    "⏸":  _P["pause"][0], "⏸️": _P["pause"][0],
    "⏯":  _P["playpause"][0], "⏯️": _P["playpause"][0],
    "⏭":  _P["skip"][0], "⏭️": _P["skip"][0],
    "⏮":  _P["prev"][0], "⏮️": _P["prev"][0],
    # Stars
    "⭐": _P["star"][0], "⭐️": _P["star"][0],
    "🌟": _P["star"][0],
    # Question / exclamation marks
    "❓": _P["warn"][0],
    "❔": _P["warn"][0],
    "❕": _P["warn"][0],
    "❗": _P["warn"][0],
    # Tools / wrench (settings family)
    "🔧": _P["settings"][0],
    "🔨": _P["settings"][0],
    "🛠":  _P["settings"][0], "🛠️": _P["settings"][0],
    # Pages / docs / clipboards
    "📄": _P["stats"][0],
    "📃": _P["stats"][0],
    "📑": _P["bookmark"][0],
    "📒": _P["bookmark"][0],
    "📓": _P["bookmark"][0],
    "📔": _P["bookmark"][0],
    "📕": _P["bookmark"][0],
    "📖": _P["bookmark"][0],
    "📗": _P["bookmark"][0],
    "📘": _P["bookmark"][0],
    "📙": _P["bookmark"][0],
    "📚": _P["bookmark"][0],
    # Folder / file
    "📁": _P["bookmark"][0],
    "📂": _P["bookmark"][0],
    "🗂":  _P["bookmark"][0], "🗂️": _P["bookmark"][0],
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
_AUTOWRAP_ENABLED = True


def disable_emoji_autowrap() -> None:
    """Globally disable the autowrap layer at runtime. Patched parsers stay
    installed but become no-ops, so outgoing messages send as plain text.

    Use this when the bot account is not Telegram Premium — non-premium bots
    cannot send `MessageEntityCustomEmoji`, and Telegram rejects every such
    message with `ENTITY_TEXT_INVALID` / `DOCUMENT_INVALID` (causing /help,
    /song, /reco etc. to silently fail to send anything)."""
    global _AUTOWRAP_ENABLED
    _AUTOWRAP_ENABLED = False


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
            if not _AUTOWRAP_ENABLED:
                return result
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

    _install_invoke_emoji_fallback()

    _AUTOWRAP_INSTALLED = True


def _strip_custom_emoji_entities(data) -> bool:
    """Remove all `MessageEntityCustomEmoji` entries from a raw RPC request
    object's `entities` list (used by messages.SendMessage / SendMedia /
    EditMessage). Returns True if any were stripped, False otherwise."""
    try:
        from pyrogram.raw.types import MessageEntityCustomEmoji
    except Exception:
        return False
    ents = getattr(data, "entities", None)
    if not ents:
        return False
    new_ents = [e for e in ents if not isinstance(e, MessageEntityCustomEmoji)]
    if len(new_ents) == len(ents):
        return False
    try:
        data.entities = new_ents
    except Exception:
        return False
    return True


_INVOKE_FALLBACK_INSTALLED = False


def _install_invoke_emoji_fallback() -> None:
    """Wrap `Client.invoke` with a reactive safety net for premium custom
    emojis. All IDs in `_P` are validated against this bot account, so
    rejections shouldn't happen in practice — but if Telegram ever returns
    `ENTITY_TEXT_INVALID` / `DOCUMENT_INVALID` (stale ID, deleted from a
    pack, etc.), we strip the custom-emoji entities and retry once so the
    message still goes through (with plain unicode) instead of failing
    silently.

    No proactive group / channel stripping is performed — premium emojis
    render in shared chats too, and the validated ID pool means there's
    no need to defensively downgrade them."""
    global _INVOKE_FALLBACK_INSTALLED
    if _INVOKE_FALLBACK_INSTALLED:
        return
    try:
        from pyrogram import Client
        from pyrogram.errors import BadRequest
    except Exception:
        return

    try:
        orig_invoke = Client.invoke
    except AttributeError:
        return
    if getattr(orig_invoke, "_emoji_fallback_installed", False):
        return

    async def _patched_invoke(self, query, *args, **kwargs):
        try:
            return await orig_invoke(self, query, *args, **kwargs)
        except BadRequest as e:
            msg = str(e)
            if ("ENTITY_TEXT_INVALID" in msg) or ("DOCUMENT_INVALID" in msg):
                if _strip_custom_emoji_entities(query):
                    try:
                        import logging
                        logging.getLogger("KHUSHI.ui").warning(
                            "[autowrap] Telegram rejected custom emojis "
                            "(%s) — retrying without them. Investigate "
                            "which ID is stale and update _P in ui.py.",
                            "ENTITY_TEXT_INVALID" if "ENTITY_TEXT_INVALID" in msg else "DOCUMENT_INVALID",
                        )
                    except Exception:
                        pass
                    return await orig_invoke(self, query, *args, **kwargs)
            raise

    _patched_invoke._emoji_fallback_installed = True
    Client.invoke = _patched_invoke
    _INVOKE_FALLBACK_INSTALLED = True


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
