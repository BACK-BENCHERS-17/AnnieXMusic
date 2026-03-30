"""KHUSHI — Start & Help Plugin."""

import logging
import random
import re

_LOGGER = logging.getLogger(__name__)

from pyrogram import enums, filters
from pyrogram.parser import Parser
from pyrogram.raw import functions as raw_func, types as raw_types
from pyrogram.types import InlineKeyboardMarkup, InputMediaPhoto, Message

from KHUSHI import app
from KHUSHI.utils.database import get_lang
from KHUSHI.utils.inline import InlineKeyboardButton
from KHUSHI.utils.inline.help import first_page, help_back_markup, private_help_panel
from config import BANNED_USERS, HELP_IMG_URL, START_IMGS, SUPPORT_CHAT
from strings import get_string, helpers

_BRAND = (
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
)

START_TEXT = (
    "<blockquote><b>{mention}</b>, ɪ'ᴍ <b>{bot}</b> — ᴀ ꜱᴜᴘᴇʀ ꜰᴀꜱᴛ ᴍᴜꜱɪᴄ ʙᴏᴛ ᴡɪᴛʜ\n"
    "ʜɪɢʜ ǫᴜᴀʟɪᴛʏ ᴀᴜᴅɪᴏ & ᴠɪᴅᴇᴏ ꜱᴛʀᴇᴀᴍɪɴɢ.\n\n"
    "<emoji id='5972072533833289156'>🔹</emoji> ᴘʟᴀʏ ꜱᴏɴɢꜱ ꜰʀᴏᴍ ʏᴏᴜᴛᴜʙᴇ, ꜱᴘᴏᴛɪꜰʏ, ꜱᴏᴜɴᴅᴄʟᴏᴜᴅ\n"
    "<emoji id='5972072533833289156'>🔹</emoji> ǫᴜᴇᴜᴇ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ, ʟᴏᴏᴘ, ꜱʜᴜꜰꜰʟᴇ, ꜱᴇᴇᴋ\n"
    "<emoji id='5972072533833289156'>🔹</emoji> 24/7 ᴍᴏᴅᴇ, ᴠᴏʟᴜᴍᴇ, ꜱᴘᴇᴇᴅ ᴄᴏɴᴛʀᴏʟ\n"
    "<emoji id='5972072533833289156'>🔹</emoji> ɴꜱꜰᴡ ꜰɪʟᴛᴇʀ, ᴄᴏɴᴛᴇɴᴛ ɢᴜᴀʀᴅ</blockquote>"
)


def _start_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("˹ʜᴇʟᴘ˼", callback_data="khushi_help"),
            InlineKeyboardButton("˹ꜱᴜᴘᴘᴏʀᴛ˼", url=f"https://t.me/{SUPPORT_CHAT.rstrip('/').split('/')[-1]}"),
        ],
        [
            InlineKeyboardButton("˹ᴀᴅᴅ ᴛᴏ ɢʀᴏᴜᴘ˼", url=f"https://t.me/{app.username}?startgroup=true"),
        ],
    ])


async def _get_lang(user_id):
    try:
        return await get_lang(user_id)
    except Exception:
        return "en"


async def _try_send_photo(client, chat_id, photo_url, caption, markup) -> bool:
    """Try to send a photo with spoiler via raw API, then fallback."""
    try:
        peer = await client.resolve_peer(chat_id)
        parser = Parser(client)
        parsed = await parser.parse(caption, mode=enums.ParseMode.HTML)
        text = parsed.get("message", "")
        entities = parsed.get("entities") or []
        raw_markup = await markup.write(client) if markup else None
        media = raw_types.InputMediaPhotoExternal(url=photo_url, spoiler=True)
        await client.invoke(
            raw_func.messages.SendMedia(
                peer=peer,
                media=media,
                message=text,
                random_id=random.randint(-(2**63), 2**63 - 1),
                reply_markup=raw_markup,
                entities=entities,
            )
        )
        return True
    except Exception:
        pass
    try:
        await client.send_photo(
            chat_id=chat_id,
            photo=photo_url,
            caption=caption,
            reply_markup=markup,
        )
        return True
    except Exception:
        pass
    return False


# ── /start & /kstart ──────────────────────────────────────────────────────────

@app.on_message(filters.command(["start", "kstart"]) & filters.private & ~BANNED_USERS)
async def khushi_start_private(client, message: Message):
    caption = (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        + START_TEXT.format(mention=message.from_user.mention, bot=app.mention)
    )
    markup = _start_kb()
    img = random.choice(START_IMGS)
    sent = await _try_send_photo(client, message.chat.id, img, caption, markup)
    if not sent:
        await message.reply_text(caption, reply_markup=markup, disable_web_page_preview=True)


@app.on_message(filters.command(["start", "kstart"]) & filters.group & ~BANNED_USERS)
async def khushi_start_group(client, message: Message):
    lang = await _get_lang(message.from_user.id)
    _ = get_string(lang)
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "˹ᴏᴘᴇɴ ɪɴ ᴘᴍ˼",
            url=f"https://t.me/{app.username}?start=start",
        )
    ]])
    await message.reply_text(
        f"<blockquote>ʜᴇʏ! sᴇɴᴅ ᴍᴇ /ꜱᴛᴀʀᴛ ɪɴ <b>ᴘʀɪᴠᴀᴛᴇ</b> ᴛᴏ ꜱᴇᴇ ᴍʏ ɪɴꜰᴏ.</blockquote>",
        reply_markup=markup,
        disable_web_page_preview=True,
    )


# ── /help & /khelp ────────────────────────────────────────────────────────────

@app.on_message(filters.command(["help", "khelp"]) & filters.private & ~BANNED_USERS)
async def khushi_help_pm(client, message: Message):
    lang = await _get_lang(message.from_user.id)
    _ = get_string(lang)
    keyboard = first_page(_)
    caption = _["help_1"].format(SUPPORT_CHAT)
    try:
        await message.delete()
    except Exception:
        pass
    sent = await _try_send_photo(client, message.chat.id, HELP_IMG_URL, caption, keyboard)
    if not sent:
        await client.send_message(
            message.chat.id,
            caption,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )


@app.on_message(filters.command(["help", "khelp"]) & filters.group & ~BANNED_USERS)
async def khushi_help_group(client, message: Message):
    lang = await _get_lang(message.from_user.id)
    _ = get_string(lang)
    markup = InlineKeyboardMarkup(private_help_panel(_))
    await message.reply_text(
        _["help_2"],
        reply_markup=markup,
        disable_web_page_preview=True,
    )


# ── Help button callback — open category list ─────────────────────────────────

@app.on_callback_query(filters.regex("^(khushi_help|annie_help|open_help)$") & ~BANNED_USERS)
async def khushi_help_cb(client, query):
    await query.answer()
    lang = await _get_lang(query.from_user.id)
    _ = get_string(lang)
    keyboard = first_page(_)
    caption = _["help_1"].format(SUPPORT_CHAT)

    edited = False
    try:
        await query.message.edit_media(
            InputMediaPhoto(media=HELP_IMG_URL, caption=caption, parse_mode=enums.ParseMode.HTML),
            reply_markup=keyboard,
        )
        edited = True
    except Exception as e:
        _LOGGER.warning("[HELP_CB] edit_media failed: %s", e)

    if not edited:
        try:
            await query.message.edit_caption(
                caption, reply_markup=keyboard, parse_mode=enums.ParseMode.HTML
            )
            edited = True
        except Exception as e:
            _LOGGER.warning("[HELP_CB] edit_caption failed: %s", e)

    if not edited:
        try:
            await query.message.edit_text(
                caption, reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
            edited = True
        except Exception as e:
            _LOGGER.warning("[HELP_CB] edit_text failed: %s", e)

    if not edited:
        _LOGGER.warning("[HELP_CB] All edits failed — falling back to delete+send")
        try:
            await query.message.delete()
        except Exception:
            pass
        sent = await _try_send_photo(client, query.message.chat.id, HELP_IMG_URL, caption, keyboard)
        if not sent:
            try:
                await client.send_message(
                    query.message.chat.id,
                    caption,
                    reply_markup=keyboard,
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True,
                )
            except Exception as e:
                _LOGGER.error("[HELP_CB] send_message also failed: %s", e)


# ── Category button callbacks — show specific help section ────────────────────

@app.on_callback_query(filters.regex(r"^help_callback hb(\d+)_p(\d+)$") & ~BANNED_USERS)
async def help_section_cb(client, query):
    match = re.match(r"help_callback hb(\d+)_p(\d+)", query.data)
    if not match:
        return await query.answer("Invalid callback.", show_alert=True)

    number = int(match.group(1))
    current_page = int(match.group(2))
    await query.answer()

    lang = await _get_lang(query.from_user.id)
    _ = get_string(lang)

    help_text = getattr(helpers, f"HELP_{number}", None)
    if not help_text:
        return await query.answer("ɪɴᴠᴀʟɪᴅ ʜᴇʟᴘ ᴛᴏᴘɪᴄ.", show_alert=True)

    back_kb = help_back_markup(_, current_page)
    try:
        await query.message.edit_caption(
            help_text, reply_markup=back_kb, parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        try:
            await query.message.edit_text(
                help_text, reply_markup=back_kb,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception:
            pass


# ── Back to category list ─────────────────────────────────────────────────────

@app.on_callback_query(filters.regex(r"^help_back_(\d+)$") & ~BANNED_USERS)
async def help_back_cb(client, query):
    await query.answer()
    lang = await _get_lang(query.from_user.id)
    _ = get_string(lang)
    keyboard = first_page(_)
    caption = _["help_1"].format(SUPPORT_CHAT)
    try:
        await query.message.edit_caption(
            caption, reply_markup=keyboard, parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        try:
            await query.message.edit_text(
                caption, reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception:
            pass


# ── Back to main start panel ──────────────────────────────────────────────────

@app.on_callback_query(filters.regex("^back_to_main$") & ~BANNED_USERS)
async def back_to_main_cb(client, query):
    await query.answer()
    caption = (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        + START_TEXT.format(mention=query.from_user.mention, bot=app.mention)
    )
    markup = _start_kb()
    img = random.choice(START_IMGS)

    edited = False
    try:
        await query.message.edit_media(
            InputMediaPhoto(media=img, caption=caption, parse_mode=enums.ParseMode.HTML),
            reply_markup=markup,
        )
        edited = True
    except Exception:
        pass

    if not edited:
        try:
            await query.message.edit_caption(
                caption, reply_markup=markup, parse_mode=enums.ParseMode.HTML
            )
            edited = True
        except Exception:
            pass

    if not edited:
        try:
            await query.message.edit_text(
                caption, reply_markup=markup,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
            edited = True
        except Exception:
            pass

    if not edited:
        try:
            await query.message.delete()
        except Exception:
            pass
        sent = await _try_send_photo(client, query.message.chat.id, img, caption, markup)
        if not sent:
            try:
                await client.send_message(
                    query.message.chat.id,
                    caption,
                    reply_markup=markup,
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True,
                )
            except Exception:
                pass


# ── Start back button ─────────────────────────────────────────────────────────

@app.on_callback_query(filters.regex("^(khushi_back|annie_back)$") & ~BANNED_USERS)
async def khushi_back_cb(client, query):
    await query.answer()
    caption = (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        + START_TEXT.format(mention=query.from_user.mention, bot=app.mention)
    )
    markup = _start_kb()
    try:
        await query.message.edit_caption(
            caption, reply_markup=markup, parse_mode=enums.ParseMode.HTML
        )
    except Exception:
        try:
            await query.message.edit_text(
                caption, reply_markup=markup,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception:
            pass


# ── Close button ──────────────────────────────────────────────────────────────

@app.on_callback_query(filters.regex("^close$") & ~BANNED_USERS)
async def close_message(client, query):
    try:
        await query.message.delete()
    except Exception:
        await query.answer()
