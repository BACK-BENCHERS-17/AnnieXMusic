"""KHUSHI — Start & Help Plugin."""

import logging
import random
import re

_LOGGER = logging.getLogger(__name__)


def _safe_text(text: str) -> str:
    """Strip  custom-emoji wrappers, keep fallback unicode char."""
    return re.sub(r'<emoji id=["\'][^"\']*["\']>(.*?)', r'\1', text, flags=re.DOTALL)


from pyrogram import enums, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.parser import Parser
from pyrogram.raw import functions as raw_func, types as raw_types
from pyrogram.types import ChatMemberUpdated, InlineKeyboardMarkup, InputMediaPhoto, Message

from KHUSHI import app
from KHUSHI.utils.database import (
    add_served_chat,
    get_lang,
    get_served_chats,
    remove_served_chat,
)
from KHUSHI.utils.inline import InlineKeyboardButton
from KHUSHI.utils.reactions import react_to_command
from KHUSHI.utils.inline.help import first_page, second_page, help_back_markup, private_help_panel
from KHUSHI.utils.ui import BRAND as _BRAND, E as _E
from config import BANNED_USERS, HELP_IMG_URL, LOGGER_ID, START_IMGS, SUPPORT_CHAT, SUPPORT_CHANNEL
from strings import get_string, helpers

_DOT = _E["dot"]
_ZAP = _E["zap"]
_FIRE = _E["fire"]
_SPARKLE = _E["sparkle"]
_MUSIC = _E["music"]
_GIFT = _E["gift"]
_CROSS = _E["cross"]

START_TEXT = (
    "<blockquote><b>{mention}</b>, ɪ'ᴍ <b>{bot}</b> — ᴀ ꜱᴜᴘᴇʀ ꜰᴀꜱᴛ ᴍᴜꜱɪᴄ ʙᴏᴛ ᴡɪᴛʜ\n"
    "ʜɪɢʜ ǫᴜᴀʟɪᴛʏ ᴀᴜᴅɪᴏ & ᴠɪᴅᴇᴏ ꜱᴛʀᴇᴀᴍɪɴɢ.\n\n"
    f"{_DOT} ᴘʟᴀʏ ꜱᴏɴɢꜱ ꜰʀᴏᴍ ʏᴏᴜᴛᴜʙᴇ, ꜱᴘᴏᴛɪꜰʏ, ꜱᴏᴜɴᴅᴄʟᴏᴜᴅ\n"
    f"{_DOT} ǫᴜᴇᴜᴇ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ, ʟᴏᴏᴘ, ꜱʜᴜꜰꜰʟᴇ, ꜱᴇᴇᴋ\n"
    f"{_DOT} 24/7 ᴍᴏᴅᴇ, ᴠᴏʟᴜᴍᴇ, ꜱᴘᴇᴇᴅ ᴄᴏɴᴛʀᴏʟ\n"
    f"{_DOT} ɴꜱꜰᴡ ꜰɪʟᴛᴇʀ, ᴄᴏɴᴛᴇɴᴛ ɢᴜᴀʀᴅ</blockquote>"
)


def _start_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("˹ʜᴇʟᴘ˼", callback_data="khushi_help", style="primary"),
            InlineKeyboardButton("˹ꜱᴜᴘᴘᴏʀᴛ˼", url=f"https://t.me/{SUPPORT_CHAT.rstrip('/').split('/')[-1]}", style="success"),
        ],
        [
            InlineKeyboardButton("˹ᴀᴅᴅ ᴛᴏ ɢʀᴏᴜᴘ˼", url=f"https://t.me/{app.username}?startgroup=true", style="primary"),
        ],
    ])


async def _get_lang(user_id):
    try:
        return await get_lang(user_id)
    except Exception:
        return "en"


async def _raw_edit(client, chat_id, msg_id, caption, markup) -> bool:
    """Edit a message caption via raw MTProto (same parser as SendMedia, supports custom emoji)."""
    try:
        peer = await client.resolve_peer(chat_id)
        parser = Parser(client)
        parsed = await parser.parse(caption, mode=enums.ParseMode.HTML)
        text = parsed.get("message", "")
        entities = parsed.get("entities") or []
        raw_markup = await markup.write(client) if markup else None
        await client.invoke(
            raw_func.messages.EditMessage(
                peer=peer,
                id=msg_id,
                message=text,
                entities=entities,
                reply_markup=raw_markup,
                no_webpage=True,
            )
        )
        return True
    except Exception as e:
        err_str = str(e)
        if "MESSAGE_NOT_MODIFIED" not in err_str and "MESSAGE_ID_INVALID" not in err_str:
            _LOGGER.warning("[RAW_EDIT] failed: %s", e)
        return False


async def _try_send_photo(client, chat_id, photo_url, caption, markup) -> bool:
    """Try to send a photo with spoiler via raw API, then fallback to plain message."""
    # Layer 1: raw MTProto SendMedia — supports custom emoji entities
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
    # Layer 2: high-level send_photo
    try:
        await client.send_photo(
            chat_id=chat_id,
            photo=photo_url,
            caption=caption,
            reply_markup=markup,
            parse_mode=enums.ParseMode.HTML,
        )
        return True
    except Exception:
        pass
    # Layer 3: plain text message (no photo)
    try:
        await client.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=markup,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return True
    except Exception:
        pass
    return False


# ── /start ────────────────────────────────────────────────────────────────────

@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
async def khushi_start_private(client, message: Message):
    await react_to_command(message, emoji="🍓")
    param = message.command[1] if len(message.command) > 1 else None

    # ── /start info_<videoid> — show song details in DM ──────────────────────
    if param and param.startswith("info_"):
        vidid = param[5:]
        try:
            from KHUSHI import YouTube
            title, duration_min, duration_sec, thumbnail, _ = await YouTube.details(
                vidid, videoid=True
            )
        except Exception:
            title, duration_min, thumbnail = None, None, None

        if title:
            info_caption = (
                f"<blockquote>{_BRAND}</blockquote>\n\n"
                f"<blockquote>"
                f"{_MUSIC} <b>{title}</b>\n\n"
                f"{_DOT} <b>Duration:</b> <code>{duration_min}</code>\n"
                f"{_DOT} <b>YouTube ID:</b> <code>{vidid}</code>"
                f"</blockquote>"
            )
            info_markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "˹ʏᴏᴜᴛᴜʙᴇ˼",
                        url=f"https://youtu.be/{vidid}",
                        style="danger",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "˹ᴀᴅᴅ ᴍᴇ ᴛᴏ ɢʀᴏᴜᴩ˼",
                        url=f"https://t.me/{app.username}?startgroup=true",
                        style="primary",
                    ),
                ],
            ])
            sent = await _try_send_photo(client, message.chat.id, thumbnail or random.choice(START_IMGS), info_caption, info_markup)
            if not sent:
                await message.reply_text(info_caption, reply_markup=info_markup, disable_web_page_preview=True)
        else:
            await message.reply_text(
                f"<blockquote>{_BRAND}</blockquote>\n\n"
                f"<blockquote>{_CROSS} ꜱᴏɴɢ ɪɴꜰᴏ ɴᴏᴛ ꜰᴏᴜɴᴅ.</blockquote>",
                disable_web_page_preview=True,
            )
        return

    # ── /start help — open help menu in DM ───────────────────────────────────
    if param == "help" or param == "start":
        lang = await _get_lang(message.from_user.id)
        _ = get_string(lang)
        keyboard = first_page(_)
        caption = _["help_1"].format(SUPPORT_CHAT)
        sent = await _try_send_photo(client, message.chat.id, HELP_IMG_URL, caption, keyboard)
        if not sent:
            await message.reply_text(
                caption,
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
        return

    # ── Normal /start ─────────────────────────────────────────────────────────
    caption = (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        + START_TEXT.format(mention=message.from_user.mention, bot=app.mention)
    )
    markup = _start_kb()
    img = random.choice(START_IMGS)
    sent = await _try_send_photo(client, message.chat.id, img, caption, markup)
    if not sent:
        await message.reply_text(caption, reply_markup=markup, disable_web_page_preview=True)


@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
async def khushi_start_group(client, message: Message):
    grp = message.chat.title or "ᴛʜɪꜱ ɢʀᴏᴜᴩ"
    mention = message.from_user.mention if message.from_user else "ʏᴏᴜ"
    caption = (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        "<blockquote>"
        f"{_FIRE}"
        f" ɴᴀᴍᴀsᴛᴇ {mention}!\n\n"
        f"{_DOT}"
        f" <b>{grp}</b> ᴍᴇɪɴ ᴡᴇʟᴄᴏᴍᴇ ʜᴀɪ!\n"
        f"{_DOT}"
        " ᴍᴇɪɴ ᴀᴀᴘᴋᴇ ɢʀᴏᴜᴘ ᴋᴀ ᴍᴜꜱɪᴄ ʙᴏᴛ ʜᴏᴏɴ.\n\n"
        f"{_ZAP}"
        " <b>ǫᴜɪᴄᴋ ᴄᴏᴍᴍᴀɴᴅꜱ</b>\n"
        f"{_DOT}"
        " <code>/play [ɢᴀᴀɴᴀ]</code> — VC ᴍᴇɪɴ ʙᴀᴊᴀᴏ\n"
        f"{_DOT}"
        " <code>/reco</code> — ʜɪɴᴅɪ / ᴘᴜɴᴊᴀʙɪ ꜱᴜɢɢᴇꜱᴛɪᴏɴꜱ\n"
        f"{_DOT}"
        " <code>/help</code> — ᴘᴜʀᴀ ʜᴇʟᴘ ᴅᴇᴋʜᴏ"
        "</blockquote>"
    )
    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("˹ʜᴇʟᴘ˼", url=f"https://t.me/{app.username}?start=start", style="primary"),
            InlineKeyboardButton("˹sᴜᴩᴘᴏʀᴛ˼", url=SUPPORT_CHAT, style="success"),
        ],
        [
            InlineKeyboardButton("˹ᴄʜᴀɴɴᴇʟ˼", url=SUPPORT_CHANNEL, style="default"),
            InlineKeyboardButton("˹ᴀᴅᴅ ᴍᴇ˼", url=f"https://t.me/{app.username}?startgroup=true", style="primary"),
        ],
    ])
    img = random.choice(START_IMGS)
    sent = await _try_send_photo(client, message.chat.id, img, caption, markup)
    if not sent:
        await message.reply_text(caption, reply_markup=markup, disable_web_page_preview=True)


# ── Helper: send join/leave log to LOGGER_ID ─────────────────────────────────

async def _send_join_log(chat, adder):
    """Send an advanced styled group-join log to the logger channel."""
    if not LOGGER_ID:
        return
    try:
        total = len(await get_served_chats())
        uname = f"@{chat.username}" if getattr(chat, "username", None) else "ɴᴏɴᴇ"
        adder_text = adder.mention if adder else "ᴜɴᴋɴᴏᴡɴ"
        adder_id   = adder.id if adder else "—"
        adder_uname = (
            f"@{adder.username}" if adder and getattr(adder, "username", None) else "ɴᴏɴᴇ"
        )

        # Try to fetch member count
        member_count = "—"
        try:
            member_count = (await app.get_chat(chat.id)).members_count or "—"
        except Exception:
            pass

        # Try to get invite link
        invite_link = "—"
        try:
            invite_link = (await app.get_chat(chat.id)).invite_link or "—"
        except Exception:
            pass

        log_text = (
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            "<blockquote>"
            f"{_SPARKLE} "
            "<b>ɴᴇᴡ ɢʀᴏᴜᴩ ᴊᴏɪɴᴇᴅ</b>\n\n"
            f"{_DOT} "
            f"<b>ɢʀᴏᴜᴩ :</b> {chat.title}\n"
            f"{_DOT} "
            f"<b>ɪᴅ :</b> <code>{chat.id}</code>\n"
            f"{_DOT} "
            f"<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {uname}\n"
            f"{_DOT} "
            f"<b>ᴍᴇᴍʙᴇʀs :</b> <code>{member_count}</code>\n"
            f"{_DOT} "
            f"<b>ɪɴᴠɪᴛᴇ :</b> {invite_link}\n\n"
            f"{_ZAP} "
            f"<b>ᴀᴅᴅᴇᴅ ʙʏ :</b> {adder_text}\n"
            f"{_ZAP} "
            f"<b>ᴜsᴇʀ ɪᴅ :</b> <code>{adder_id}</code>\n"
            f"{_ZAP} "
            f"<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {adder_uname}\n\n"
            f"{_GIFT} "
            f"<b>ᴛᴏᴛᴀʟ ɢʀᴏᴜᴩs :</b> <code>{total}</code>"
            "</blockquote>"
        )
        await app.send_message(
            LOGGER_ID, log_text,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception as _e:
        _LOGGER.warning(f"[JoinLog] Failed to send join log: {_e}")


async def _send_leave_log(chat_id: int, chat_title: str, chat_username: str, remover):
    """Send an advanced styled group-leave log to the logger channel."""
    if not LOGGER_ID:
        return
    try:
        total = len(await get_served_chats())
        uname = f"@{chat_username}" if chat_username else "ɴᴏɴᴇ"
        remover_text = remover.mention if remover else "ᴜɴᴋɴᴏᴡɴ"
        remover_id   = remover.id if remover else "—"
        remover_uname = (
            f"@{remover.username}" if remover and getattr(remover, "username", None) else "ɴᴏɴᴇ"
        )
        log_text = (
            f"<blockquote>{_BRAND}</blockquote>\n\n"
            "<blockquote>"
            f"{_FIRE} "
            "<b>ʟᴇꜰᴛ / ʀᴇᴍᴏᴠᴇᴅ ꜰʀᴏᴍ ɢʀᴏᴜᴩ</b>\n\n"
            f"{_DOT} "
            f"<b>ɢʀᴏᴜᴩ :</b> {chat_title}\n"
            f"{_DOT} "
            f"<b>ɪᴅ :</b> <code>{chat_id}</code>\n"
            f"{_DOT} "
            f"<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {uname}\n\n"
            f"{_ZAP} "
            f"<b>ʀᴇᴍᴏᴠᴇᴅ ʙʏ :</b> {remover_text}\n"
            f"{_ZAP} "
            f"<b>ᴜsᴇʀ ɪᴅ :</b> <code>{remover_id}</code>\n"
            f"{_ZAP} "
            f"<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {remover_uname}\n\n"
            f"{_GIFT} "
            f"<b>ʀᴇᴍᴀɪɴɪɴɢ ɢʀᴏᴜᴩs :</b> <code>{total}</code>"
            "</blockquote>"
        )
        await app.send_message(
            LOGGER_ID, log_text,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception as _e:
        _LOGGER.warning(f"[LeaveLog] Failed to send leave log: {_e}")


# ── Bot added to group — welcome + log ───────────────────────────────────────

@app.on_message(filters.new_chat_members)
async def bot_added_to_group(client, message: Message):
    """Send a rich welcome card when this bot itself is added to a group."""
    if not message.new_chat_members:
        return
    bot_id = (await client.get_me()).id
    is_bot_added = any(m.id == bot_id for m in message.new_chat_members)
    if not is_bot_added:
        return

    grp = message.chat.title or "ᴀᴀᴘᴋᴀ ɢʀᴏᴜᴩ"
    adder = message.from_user

    # ── Register this chat in DB ──────────────────────────────────────────────
    try:
        await add_served_chat(message.chat.id)
    except Exception:
        pass

    # ── Advanced log to LOGGER_ID ─────────────────────────────────────────────
    await _send_join_log(message.chat, adder)

    # ── Welcome message in the group ──────────────────────────────────────────
    adder_mention = adder.mention if adder else "ᴀᴅᴍɪɴ"
    caption = (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        "<blockquote>"
        f"{_FIRE}"
        f" <b>ʜᴇʟʟᴏ {grp}!</b>\n\n"
        f"{_DOT}"
        f" ᴛʜᴀɴᴋ ʏᴏᴜ {adder_mention} ꜰᴏʀ ᴀᴅᴅɪɴɢ ᴍᴇ!\n\n"
        f"{_ZAP}"
        " <b>ᴍᴇʀɪ ᴩᴏᴡᴇʀ</b>\n"
        f"{_DOT} {_MUSIC} ʜɪɴᴅɪ · ᴩᴜɴᴊᴀʙɪ · ʙᴏʟʟʏᴡᴏᴏᴅ · ɪɴᴛᴇʀɴᴀᴛɪᴏɴᴀʟ\n"
        f"{_DOT} ᴜʟᴛʀᴀ ᴩᴏꜱᴛ VC ꜱᴛʀᴇᴀᴍɪɴɢ\n"
        f"{_DOT} ʏᴏᴜᴛᴜʙᴇ · ꜱᴩᴏᴛɪꜰʏ · ꜱᴏᴜɴᴅᴄʟᴏᴜᴅ\n"
        f"{_DOT} ɢʀᴏᴜᴩ ꜱᴇᴄᴜʀɪᴛʏ + ʜᴜ ᴍᴏᴅᴇʀᴀᴛɪᴏɴ\n\n"
        f"{_SPARKLE}"
        " <code>/play [ɢᴀᴀɴᴀ ᴋᴀ ɴᴀᴀᴍ]</code> ꜱᴇ ʙᴀᴊᴀᴏ!\n"
        "<b>ᴍᴜᴊʜᴇ ᴀᴅᴍɪɴ ʙᴀɴᴀᴏ ᴛᴀᴋɪ ᴍᴀɪɴ VC ᵴᴜɴᴀ ꜱᴀᴋᴏᴏɴ.</b>"
        "</blockquote>"
    )
    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("˹ʜᴇʟᴘ˼", url=f"https://t.me/{app.username}?start=start", style="primary"),
            InlineKeyboardButton("˹sᴜᴩᴘᴏʀᴛ˼", url=SUPPORT_CHAT, style="success"),
        ],
        [
            InlineKeyboardButton("˹ᴄʜᴀɴɴᴇʟ˼", url=SUPPORT_CHANNEL, style="default"),
            InlineKeyboardButton("˹ᴀᴅᴅ ᴛᴏ ɢʀᴏᴜᴩ˼", url=f"https://t.me/{app.username}?startgroup=true", style="primary"),
        ],
    ])
    img = random.choice(START_IMGS)
    sent = await _try_send_photo(client, message.chat.id, img, caption, markup)
    if not sent:
        await message.reply_text(caption, reply_markup=markup, disable_web_page_preview=True)


# ── Bot removed from group — leave log ───────────────────────────────────────

@app.on_chat_member_updated(filters.group)
async def bot_member_updated(client, update: ChatMemberUpdated):
    """Detect when the bot is removed/banned from a group and log it."""
    try:
        me = await client.get_me()
        bot_id = me.id

        new = update.new_chat_member
        old = update.old_chat_member

        # Only care about the bot itself
        if not new or new.user.id != bot_id:
            return

        new_status = new.status
        old_status = old.status if old else None

        # Bot was removed / banned / left
        left_statuses = {ChatMemberStatus.BANNED, ChatMemberStatus.LEFT, ChatMemberStatus.RESTRICTED}
        was_active = old_status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER, ChatMemberStatus.OWNER}
        is_gone    = new_status in left_statuses

        if was_active and is_gone:
            chat = update.chat
            chat_id    = chat.id
            chat_title = getattr(chat, "title", str(chat_id))
            chat_uname = getattr(chat, "username", None)
            remover    = update.from_user

            # Remove from served chats DB
            try:
                await remove_served_chat(chat_id)
            except Exception:
                pass

            await _send_leave_log(chat_id, chat_title, chat_uname, remover)

    except Exception as _e:
        _LOGGER.debug(f"[MemberUpdate] Error: {_e}")


# ── /help ─────────────────────────────────────────────────────────────────────

@app.on_message(filters.command(["help"]) & filters.private & ~BANNED_USERS)
async def khushi_help_pm(client, message: Message):
    await react_to_command(message, emoji="🍓")
    lang = await _get_lang(message.from_user.id)
    _ = get_string(lang)
    keyboard = first_page(_)
    caption = _["help_1"].format(SUPPORT_CHAT)
    try:
        await message.delete()
    except Exception:
        pass
    await _try_send_photo(client, message.chat.id, HELP_IMG_URL, caption, keyboard)


@app.on_message(filters.command(["help"]) & filters.group & ~BANNED_USERS)
async def khushi_help_group(client, message: Message):
    await react_to_command(message, emoji="🍓")
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

    msg = query.message
    edited = await _raw_edit(client, msg.chat.id, msg.id, caption, keyboard)

    if not edited:
        try:
            await msg.edit_caption(
                caption, reply_markup=keyboard, parse_mode=enums.ParseMode.HTML
            )
            edited = True
        except Exception as e:
            _LOGGER.warning("[HELP_CB] edit_caption failed: %s", e)

    if not edited:
        try:
            await msg.edit_text(
                caption, reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
            edited = True
        except Exception as e:
            _LOGGER.warning("[HELP_CB] edit_text failed: %s", e)

    if not edited:
        _LOGGER.warning("[HELP_CB] All edits failed — deleting and sending fresh")
        try:
            await msg.delete()
        except Exception:
            pass
        await _try_send_photo(client, msg.chat.id, HELP_IMG_URL, caption, keyboard)


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

    back_kb = help_back_markup(_, number)

    msg = query.message
    edited = await _raw_edit(client, msg.chat.id, msg.id, help_text, back_kb)

    if not edited:
        try:
            await msg.edit_caption(
                help_text, reply_markup=back_kb, parse_mode=enums.ParseMode.HTML
            )
            edited = True
        except Exception as e:
            _LOGGER.warning("[HELP_SEC] edit_caption hb%d failed: %s", number, e)

    if not edited:
        try:
            await msg.edit_text(
                help_text, reply_markup=back_kb,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
            edited = True
        except Exception as e2:
            _LOGGER.warning("[HELP_SEC] edit_text hb%d failed: %s", number, e2)

    if not edited:
        _LOGGER.warning("[HELP_SEC] hb%d — all edits failed, deleting and sending fresh", number)
        try:
            await msg.delete()
        except Exception:
            pass
        await _try_send_photo(client, msg.chat.id, HELP_IMG_URL, help_text, back_kb)


# ── Next / Prev section navigation (loop) ────────────────────────────────────

@app.on_callback_query(filters.regex(r"^help_nav_(\d+)$") & ~BANNED_USERS)
async def help_nav_cb(client, query):
    match = re.match(r"help_nav_(\d+)", query.data)
    if not match:
        return await query.answer()

    section = int(match.group(1))
    await query.answer()

    lang = await _get_lang(query.from_user.id)
    _ = get_string(lang)

    help_text = getattr(helpers, f"HELP_{section}", None)
    if not help_text:
        return await query.answer("ɪɴᴠᴀʟɪᴅ sᴇᴄᴛɪᴏɴ.", show_alert=True)

    nav_kb = help_back_markup(_, section)
    nav_msg = query.message

    edited = await _raw_edit(client, nav_msg.chat.id, nav_msg.id, help_text, nav_kb)

    if not edited:
        try:
            await nav_msg.edit_caption(
                help_text, reply_markup=nav_kb, parse_mode=enums.ParseMode.HTML
            )
            edited = True
        except Exception:
            pass

    if not edited:
        try:
            await nav_msg.edit_text(
                help_text, reply_markup=nav_kb,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
            edited = True
        except Exception:
            pass

    if not edited:
        try:
            await nav_msg.delete()
        except Exception:
            pass
        await _try_send_photo(client, nav_msg.chat.id, HELP_IMG_URL, help_text, nav_kb)


# ── Back to category list (page 1 or 2) ──────────────────────────────────────

@app.on_callback_query(filters.regex(r"^(help_back|help_page)_(\d+)$") & ~BANNED_USERS)
async def help_back_cb(client, query):
    await query.answer()
    match = re.match(r"^(?:help_back|help_page)_(\d+)$", query.data)
    page = int(match.group(1)) if match else 1
    lang = await _get_lang(query.from_user.id)
    _ = get_string(lang)
    keyboard = second_page(_) if page == 2 else first_page(_)
    caption = _["help_1"].format(SUPPORT_CHAT)

    bk_msg = query.message
    edited = await _raw_edit(client, bk_msg.chat.id, bk_msg.id, caption, keyboard)

    if not edited:
        try:
            await bk_msg.edit_caption(
                caption, reply_markup=keyboard, parse_mode=enums.ParseMode.HTML
            )
            edited = True
        except Exception:
            pass

    if not edited:
        try:
            await bk_msg.edit_text(
                caption, reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True,
            )
            edited = True
        except Exception:
            pass

    if not edited:
        try:
            await bk_msg.delete()
        except Exception:
            pass
        await _try_send_photo(client, bk_msg.chat.id, HELP_IMG_URL, caption, keyboard)


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
    img = random.choice(START_IMGS)
    edited = False
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
        await _try_send_photo(client, query.message.chat.id, img, caption, markup)

