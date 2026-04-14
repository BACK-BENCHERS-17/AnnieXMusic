import logging
import re
from random import randint

from pyrogram import raw
from pyrogram.enums import ParseMode
from pyrogram.parser import html as html_mod

_log = logging.getLogger(__name__)


def _strip_invisible_link(text: str) -> str:
    """Remove the invisible-link anchor prefix used for the invert_media trick.
    Handles both \u200C (zero-width non-joiner) and \u200B (zero-width space)
    as the anchor body, and their HTML-entity equivalents."""
    return re.sub(
        r'^<a href="[^"]*">(?:\u200c|\u200b|&#8203;|&#8204;)</a>',
        "",
        text,
        count=1,
    )


def _strip_all_anchors(text: str) -> str:
    """Remove ALL <a href> tags from HTML text, keeping the visible link text.
    This prevents Telegram from rejecting CDN/stream URLs as DOCUMENT_INVALID."""
    text = re.sub(r'<a\b[^>]*>', "", text)
    text = re.sub(r'</a>', "", text)
    return text


async def send_msg_invert_preview(
    client,
    chat_id: int,
    text: str,
    reply_markup=None,
    reply_to_message_id: int = None,
):
    """
    Send a message with the link preview displayed ABOVE the text
    (invert_media=True) using Pyrogram's raw API.
    Falls back through multiple layers if the raw call fails.
    """
    # ── Layer 1: Raw API with invert_media ───────────────────────────────────
    try:
        parser = html_mod.HTML(client)
        parsed = await parser.parse(text)
        msg_text = parsed["message"]
        entities = parsed.get("entities", [])

        peer = await client.resolve_peer(chat_id)
        raw_markup = await reply_markup.write(client) if reply_markup else None

        reply_to = None
        if reply_to_message_id:
            reply_to = raw.types.InputReplyToMessage(reply_to_msg_id=reply_to_message_id)

        result = await client.invoke(
            raw.functions.messages.SendMessage(
                peer=peer,
                message=msg_text,
                random_id=randint(1, 2**31 - 1),
                no_webpage=False,
                invert_media=True,
                reply_markup=raw_markup,
                entities=entities,
                reply_to=reply_to,
            )
        )

        if hasattr(result, "updates"):
            for update in result.updates:
                if isinstance(
                    update,
                    (raw.types.UpdateNewMessage, raw.types.UpdateNewChannelMessage),
                ):
                    return await client.get_messages(chat_id, update.message.id)

            for update in result.updates:
                if isinstance(update, raw.types.UpdateMessageID):
                    try:
                        return await client.get_messages(chat_id, update.id)
                    except Exception:
                        pass

        elif hasattr(result, "id"):
            try:
                return await client.get_messages(chat_id, result.id)
            except Exception:
                pass

        _log.warning(
            "[raw_send] Layer 1 sent but could not resolve message object "
            "for chat=%s — falling through to Layer 2", chat_id
        )

    except Exception as e:
        _log.warning("[raw_send] Layer 1 (raw+invert_media) failed for chat=%s: %s", chat_id, e)

    # ── Layer 2: Regular send_message with link preview ──────────────────────
    try:
        return await client.send_message(
            chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False,
            reply_to_message_id=reply_to_message_id,
        )
    except Exception as e:
        _log.warning("[raw_send] Layer 2 (send_message w/ preview) failed for chat=%s: %s", chat_id, e)

    # ── Layer 3: Plain send_message without link preview ────────────────────
    # Strip ALL anchor tags so Telegram never receives a URL entity pointing
    # to a CDN/stream URL, which triggers DOCUMENT_INVALID on messages.SendMessage.
    try:
        clean_text = _strip_all_anchors(_strip_invisible_link(text))
        return await client.send_message(
            chat_id,
            text=clean_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_to_message_id=reply_to_message_id,
        )
    except Exception as e:
        _log.error("[raw_send] Layer 3 (plain send_message) also failed for chat=%s: %s", chat_id, e)
        return None
