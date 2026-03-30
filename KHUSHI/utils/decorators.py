"""KHUSHI-specific decorators — uses KHUSHI's own app client."""

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from KHUSHI import app
from KHUSHI.misc import SUDOERS, db
from KHUSHI.utils.database import (
    get_authuser_names,
    get_cmode,
    get_lang,
    get_upvote_count,
    is_active_chat,
    is_maintenance,
    is_nonadmin_chat,
    is_skipmode,
)
from KHUSHI.utils.formatters import int_to_alpha
from config import SUPPORT_CHAT, adminlist, confirmer
from strings import get_string


def KhushiAdminCheck(mystic):
    """AdminRightsCheck using KHUSHI's app (not ANNIEMUSIC's)."""
    async def wrapper(client, message):
        # Maintenance check
        try:
            if await is_maintenance():
                if message.from_user.id not in SUDOERS:
                    return await message.reply_text(
                        f"{app.mention} ɪs ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ, "
                        f"ᴠɪsɪᴛ <a href='https://t.me/{SUPPORT_CHAT.lstrip('@')}'>sᴜᴘᴘᴏʀᴛ</a>.",
                        disable_web_page_preview=True,
                    )
        except Exception:
            pass

        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)
        except Exception:
            _ = get_string("en")

        # Anonymous admin check
        if message.sender_chat:
            return await message.reply_text(
                _["general_3"],
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("ʜᴏᴡ ᴛᴏ ғɪx ?", callback_data="AnonymousAdmin")
                ]]),
            )

        # Linked chat mode (c* commands)
        if message.command[0][0] == "c":
            chat_id = await get_cmode(message.chat.id)
            if chat_id is None:
                return await message.reply_text(_["setting_7"])
            try:
                await app.get_chat(chat_id)
            except Exception:
                return await message.reply_text(_["cplay_4"])
        else:
            chat_id = message.chat.id

        # Active chat check
        if not await is_active_chat(chat_id):
            return await message.reply_text(_["general_5"])

        # Admin rights check
        is_non_admin = await is_nonadmin_chat(message.chat.id)
        if not is_non_admin:
            if message.from_user.id not in SUDOERS:
                admins = adminlist.get(message.chat.id)
                if not admins:
                    return await message.reply_text(_["admin_13"])
                if message.from_user.id not in admins:
                    if await is_skipmode(message.chat.id):
                        upvote = await get_upvote_count(chat_id)
                        command = message.command[0]
                        if command[0] == "c":
                            command = command[1:]
                        if command == "speed":
                            return await message.reply_text(_["admin_14"])
                        MODE = command.title()
                        upl = InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                "ᴠᴏᴛᴇ",
                                callback_data=f"ADMIN  UpVote|{chat_id}_{MODE}",
                            )
                        ]])
                        if chat_id not in confirmer:
                            confirmer[chat_id] = {}
                        try:
                            vidid = db[chat_id][0]["vidid"]
                            file = db[chat_id][0]["file"]
                        except Exception:
                            return await message.reply_text(_["admin_14"])
                        text = (
                            f"<b>ᴀᴅᴍɪɴ ʀɪɢʜᴛs ɴᴇᴇᴅᴇᴅ</b>\n\n"
                            f"ʀᴇꜰʀᴇꜱʜ ᴀᴅᴍɪɴ ᴄᴀᴄʜᴇ ᴠɪᴀ : /reload\n\n"
                            f"» {upvote} ᴠᴏᴛᴇs ɴᴇᴇᴅᴇᴅ."
                        )
                        senn = await message.reply_text(text, reply_markup=upl)
                        confirmer[chat_id][senn.id] = {"vidid": vidid, "file": file}
                        return
                    else:
                        return await message.reply_text(_["admin_14"])

        return await mystic(client, message, _, chat_id)

    return wrapper


def KhushiActualAdmin(mystic):
    """AdminActual using KHUSHI's app."""
    async def wrapper(client, message):
        try:
            if await is_maintenance():
                if message.from_user.id not in SUDOERS:
                    return await message.reply_text(
                        f"{app.mention} ɪs ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ.",
                        disable_web_page_preview=True,
                    )
        except Exception:
            pass

        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)
        except Exception:
            _ = get_string("en")

        if message.sender_chat:
            return await message.reply_text(
                _["general_3"],
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("ʜᴏᴡ ᴛᴏ ғɪx ?", callback_data="AnonymousAdmin")
                ]]),
            )

        if message.from_user.id not in SUDOERS:
            try:
                member = (
                    await app.get_chat_member(message.chat.id, message.from_user.id)
                ).privileges
                if not member or not member.can_manage_video_chats:
                    return await message.reply_text(_["general_4"])
            except Exception:
                return

        return await mystic(client, message, _)

    return wrapper


AdminRightsCheck = KhushiAdminCheck
AdminActual = KhushiActualAdmin
