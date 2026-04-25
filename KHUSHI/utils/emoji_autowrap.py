"""
KHUSHI — Premium custom-emoji autowrap runtime
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Monkey-patches Pyrogram's parser so every outgoing message gets premium
custom-emoji entities for any known unicode glyph it contains. Premium emoji
HTML strings are inlined directly at call sites throughout the bot — this
module only carries the runtime patching layer plus the unicode-to-ID
mapping needed by the autowrap layer.
"""

import re as _re


# ── Unicode → premium-emoji-ID map (used by autowrap to upgrade plain glyphs)
_UNICODE_TO_ID: dict[str, str] = {
    # Status
    "✅": "5852871561983299073",
    "❌": "5040042498634810056",
    "⚠️": "5420323339723881652",
    "⚠":  "5420323339723881652",
    "🛡": "5895483165182529286",
    "🛡️": "5895483165182529286",
    "🚫": "5039671744172917707",
    "🔐": "5472308992514464048",
    # Music / media
    "🎵": "5463107823946717464",
    "🎶": "5039771357349413873",
    "🎤": "5933678317935791830",
    "🎷": "5467793203769933478",
    "🎧": "5463107823946717464",
    "📻": "5463107823946717464",
    "🎬": "5375464961822695044",
    "🎥": "5258217809250372293",
    "📺": "6044356915029348425",
    "▶️": "5039937555403899813",
    "▶":  "5039937555403899813",
    "📀": "5462956611033117422",
    # Actions / states
    "⚡️": "5042334757040423886",
    "⚡":  "5042334757040423886",
    "🔥": "5039644681583985437",
    "🌟": "5039827436737397847",
    "✨": "5039827436737397847",
    "💫": "5042200814190330758",
    "💎": "5039827436737397847",
    "🔔": "6334406115341633473",
    "📢": "6334406115341633473",
    "🔖": "5222444124698853913",
    "⏰": "5123230779593196220",
    "⏳": "5454415424319931791",
    "⌛️": "5454415424319931791",
    "⌛":  "5454415424319931791",
    "🔍": "5972072533833289156",
    "🔗": "5972072533833289156",
    "👑": "5039727497143387500",
    "🎁": "5409029744693897259",
    "📌": "5222444124698853913",
    "❄️": "5449449325434266744",
    "❄":  "5449449325434266744",
    "❤️\u200d🔥": "5042225965518816316",
    "🌹": "6122692084806716730",
    "🦋": "5042131347389285520",
    "🌐": "5316832074047441823",
    "👤": "5316992572680320646",
    "🧠": "5237799019329105246",
    "😫": "5371077231823036079",
    "😎": "5424663180838182778",
    "💩": "6307831155521494118",
    "📥": "5776182936638329359",
    "📷": "6048390817033228573",
    # Indicators
    "🔹": "5972072533833289156",
    "➤":  "5474300135057925400",
    "⬅️": "4981358569468200584",
    "⬅":  "4981358569468200584",
    "➡️": "5474300135057925400",
    "➡":  "5474300135057925400",
    "🔁": "6030657343744644592",
    "🔀": "5129905231785624480",
    "⏭": "6192553546102085729",
    "⏮": "4981358569468200584",
    "⏹": "5040042498634810056",
    "⏸": "5039937555403899813",
    "⏯": "5039937555403899813",
    "🔊": "6039454987250044861",
    "🚀": "5042334757040423886",
    "⏩": "6192553546102085729",
    "⏪": "4981358569468200584",
    # System / stats
    "🏓": "5269563867305879894",
    "📞": "6093587384954262033",
    "🕔": "6337029193603225180",
    "🖥": "5215186239853964761",
    "🖥️": "5215186239853964761",
    "🔵": "5834767463081840315",
    "💬": "5040036030414062506",
    "📊": "4958506272551863292",
    "⚙️": "5895592588064328942",
    "⚙":  "5895592588064328942",
    "💻": "5972055534352733289",
    # Brand
    "🧸": "5042192219960771668",
    # Extras / aliases
    "🎙": "5933678317935791830", "🎙️": "5933678317935791830",
    "🔇": "6039454987250044861", "🔈": "6039454987250044861",
    "🔉": "6039454987250044861",
    "📹": "5258217809250372293",
    "🎞": "5375464961822695044", "🎞️": "5375464961822695044",
    "❤":  "5042225965518816316", "❤️": "5042225965518816316",
    "💖": "5042225965518816316", "💗": "5042225965518816316",
    "💘": "5042225965518816316", "💝": "5042225965518816316",
    "🩷": "5042225965518816316",
    "📍": "5222444124698853913",
    "📋": "4958506272551863292",
    "📭": "5222444124698853913", "📬": "5222444124698853913",
    "📨": "6334406115341633473",
    "🚨": "5420323339723881652", "🆘": "5420323339723881652",
    "‼":  "5420323339723881652", "‼️": "5420323339723881652",
    "⬇":  "5776182936638329359", "⬇️": "5776182936638329359",
    "⬆":  "5474300135057925400", "⬆️": "5474300135057925400",
    "↑":  "5474300135057925400", "↓": "5776182936638329359",
    "→":  "5474300135057925400", "←": "4981358569468200584",
    "➥":  "5474300135057925400", "➻": "5474300135057925400",
    "↬":  "5474300135057925400",
    "↻":  "6030657343744644592", "🔄": "6030657343744644592",
    "✓":  "5852871561983299073", "✔": "5852871561983299073",
    "✔️": "5852871561983299073",
    "✗":  "5040042498634810056", "✖": "5040042498634810056",
    "✖️": "5040042498634810056",
    "⏤":  "5972072533833289156", "•": "5972072533833289156",
    "▪":  "5972072533833289156", "▫": "5972072533833289156",
    "⛔":  "5039671744172917707", "⛔️": "5039671744172917707",
    "✘":  "5040042498634810056", "🚷": "5039671744172917707",
    "🛑": "5039671744172917707",
    "✚":  "5852871561983299073", "➕": "5852871561983299073",
    "➖": "5040042498634810056",
    "🏠": "5972072533833289156", "🏡": "5972072533833289156",
    "🔴": "5039644681583985437", "🟢": "5852871561983299073",
    "🟡": "5420323339723881652", "🟠": "5039644681583985437",
    "🟣": "5042200814190330758", "🟤": "5972072533833289156",
    "⚫": "5972072533833289156", "⚪": "5972072533833289156",
    "🟥": "5039644681583985437", "🟦": "5834767463081840315",
    "🟧": "5039644681583985437", "🟨": "5420323339723881652",
    "🟩": "5852871561983299073", "🟪": "5042200814190330758",
    "🟫": "5972072533833289156", "⬛": "5972072533833289156",
    "⬜": "5972072533833289156",
    "🕐": "5123230779593196220", "🕑": "5123230779593196220",
    "🕒": "5123230779593196220", "🕓": "5123230779593196220",
    "🕕": "5123230779593196220", "🕖": "5123230779593196220",
    "🕗": "5123230779593196220", "🕘": "5123230779593196220",
    "🕙": "5123230779593196220", "🕚": "5123230779593196220",
    "🕛": "5123230779593196220", "🕜": "5123230779593196220",
    "🕝": "5123230779593196220", "🕞": "5123230779593196220",
    "🕟": "5123230779593196220", "🕠": "5123230779593196220",
    "🕡": "5123230779593196220", "🕢": "5123230779593196220",
    "🕣": "5123230779593196220", "🕤": "5123230779593196220",
    "🕥": "5123230779593196220", "🕦": "5123230779593196220",
    "🕧": "5123230779593196220",
    "⏱":  "5123230779593196220", "⏱️": "5123230779593196220",
    "⏲":  "5454415424319931791", "⏲️": "5454415424319931791",
    "♥":  "5042225965518816316", "♥️": "5042225965518816316",
    "♦":  "5039827436737397847", "♦️": "5039827436737397847",
    "♣":  "5972072533833289156", "♠": "5972072533833289156",
    "♪":  "5039771357349413873", "♫": "5039771357349413873",
    "♬":  "5039771357349413873", "♩": "5039771357349413873",
    "🗳":  "4958506272551863292", "🗳️": "4958506272551863292",
    "🍓": "5042225965518816316",
    "🎯": "5039644681583985437", "💯": "5039644681583985437",
    "🎉": "5039827436737397847", "🎊": "5039827436737397847",
    "🎈": "5039827436737397847",
    "⏹️": "5040042498634810056",
    "⏸️": "5039937555403899813",
    "⏯️": "5039937555403899813",
    "⏭️": "6192553546102085729",
    "⏮️": "4981358569468200584",
    "⭐": "5039827436737397847", "⭐️": "5039827436737397847",
    "❓": "5420323339723881652", "❔": "5420323339723881652",
    "❕": "5420323339723881652", "❗": "5420323339723881652",
    "🔧": "5895592588064328942", "🔨": "5895592588064328942",
    "🛠":  "5895592588064328942", "🛠️": "5895592588064328942",
    "📄": "4958506272551863292", "📃": "4958506272551863292",
    "📑": "5222444124698853913", "📒": "5222444124698853913",
    "📓": "5222444124698853913", "📔": "5222444124698853913",
    "📕": "5222444124698853913", "📖": "5222444124698853913",
    "📗": "5222444124698853913", "📘": "5222444124698853913",
    "📙": "5222444124698853913", "📚": "5222444124698853913",
    "📁": "5222444124698853913", "📂": "5222444124698853913",
    "🗂":  "5222444124698853913", "🗂️": "5222444124698853913",
}

# Add VS16 (U+FE0F) variants for every glyph that doesn't already have one
for _g, _eid in list(_UNICODE_TO_ID.items()):
    if "\ufe0f" not in _g:
        _UNICODE_TO_ID.setdefault(_g + "\ufe0f", _eid)

# Longest-glyph-first so multi-codepoint emojis match before single-codepoint ones
_SORTED_GLYPHS = sorted(_UNICODE_TO_ID.keys(), key=len, reverse=True)
_GLYPH_RE = (
    _re.compile("(?:" + "|".join(_re.escape(g) for g in _SORTED_GLYPHS) + ")")
    if _SORTED_GLYPHS else None
)


def _augment_with_custom_emoji(message: str, entities):
    """Add MessageEntityCustomEmoji entries for every known unicode glyph in
    `message`, while leaving any pre-existing entities untouched."""
    if not _GLYPH_RE or not message:
        return entities or []
    try:
        from pyrogram.raw.types import MessageEntityCustomEmoji
    except Exception:
        return entities or []

    new_entities = list(entities or [])
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
    """Globally disable the autowrap layer at runtime."""
    global _AUTOWRAP_ENABLED
    _AUTOWRAP_ENABLED = False


def install_emoji_autowrap() -> None:
    """Monkeypatch Pyrogram's parser so every outgoing message gets premium
    custom-emoji entities for any known unicode glyph it contains.

    Idempotent: safe to call multiple times.
    """
    global _AUTOWRAP_INSTALLED
    if _AUTOWRAP_INSTALLED:
        return

    def _wrap_parse_method(cls, method_name: str = "parse"):
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
    """Remove all MessageEntityCustomEmoji entries from a raw RPC request."""
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
    """Wrap Client.invoke with a reactive safety net for premium custom emojis."""
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
                        logging.getLogger("KHUSHI.emoji").warning(
                            "[autowrap] Telegram rejected custom emojis "
                            "(%s) — retrying without them.",
                            "ENTITY_TEXT_INVALID" if "ENTITY_TEXT_INVALID" in msg else "DOCUMENT_INVALID",
                        )
                    except Exception:
                        pass
                    return await orig_invoke(self, query, *args, **kwargs)
            raise

    _patched_invoke._emoji_fallback_installed = True
    Client.invoke = _patched_invoke
    _INVOKE_FALLBACK_INSTALLED = True
