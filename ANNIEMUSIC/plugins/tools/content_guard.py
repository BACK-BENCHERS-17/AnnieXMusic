import asyncio

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.types import Message

from ANNIEMUSIC import app
from ANNIEMUSIC.utils.content_filter import is_bad_text
from ANNIEMUSIC.utils.database import (
    content_guard_off,
    content_guard_on,
    is_content_guard_on,
)


async def _is_admin(client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )
    except Exception:
        return False


async def _delete_and_warn(message: Message, reason: str):
    try:
        await message.delete()
    except Exception:
        return
    try:
        warning = await message.reply_text(
            "<blockquote>"
            "⛔ <b>ᴄᴏɴᴛᴇɴᴛ ʀᴇᴍᴏᴠᴇᴅ</b>\n\n"
            f"🚫 <b>Reason :</b> {reason}\n\n"
            "🛡 <b>NSFW Filter</b> is active in this group."
            "</blockquote>\n"
            "<i>⏳ Deleting in 8 seconds...</i>",
            parse_mode=ParseMode.HTML,
        )
        await asyncio.sleep(8)
        await warning.delete()
    except Exception:
        pass


@app.on_message(
    filters.command(["nsfw"]) & filters.group
)
async def content_guard_cmd(client, message: Message):
    if not message.from_user:
        return await message.reply_text(
            "<blockquote>"
            "🚫 <b>ᴀɴᴏɴʏᴍᴏᴜs ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ</b>\n\n"
            "Anonymous admins cannot use this command."
            "</blockquote>",
            parse_mode=ParseMode.HTML,
        )

    if not await _is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text(
            "<blockquote>"
            "🚫 <b>ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ</b>\n\n"
            "Only group admins can use this command."
            "</blockquote>",
            parse_mode=ParseMode.HTML,
        )

    args = message.command
    if len(args) < 2 or args[1].lower() not in ("on", "off"):
        enabled = await is_content_guard_on(message.chat.id)
        status_icon = "✅ ᴏɴ" if enabled else "🚫 ᴏꜰꜰ"
        return await message.reply_text(
            "<blockquote>"
            f"🛡 <b>ɴsꜰᴡ ꜰɪʟᴛᴇʀ</b> — {status_icon}\n\n"
            "ℹ️ <b>Usage :</b>\n"
            "  <code>/nsfw on</code>  — Enable filter\n"
            "  <code>/nsfw off</code> — Disable filter\n\n"
            "🛡 <b>What it protects :</b>\n"
            "  • 18+ images auto-deleted\n"
            "  • Explicit keywords in messages deleted\n"
            "  • NSFW sticker packs blocked\n"
            "  • NSFW song thumbnails blocked\n\n"
            "ℹ️ Filter is <b>ON by default</b> in all groups."
            "</blockquote>",
            parse_mode=ParseMode.HTML,
        )

    if args[1].lower() == "on":
        await content_guard_on(message.chat.id)
        await message.reply_text(
            "<blockquote>"
            "✅ <b>ɴsꜰᴡ ꜰɪʟᴛᴇʀ : ᴇɴᴀʙʟᴇᴅ</b>\n\n"
            "🛡 This group is now protected:\n"
            "  • 18+ &amp; explicit images → auto-deleted\n"
            "  • NSFW stickers → blocked\n"
            "  • Explicit keywords → removed\n\n"
            "✅ <i>Group is safe! 🔒</i>"
            "</blockquote>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await content_guard_off(message.chat.id)
        await message.reply_text(
            "<blockquote>"
            "🚫 <b>ɴsꜰᴡ ꜰɪʟᴛᴇʀ : ᴅɪsᴀʙʟᴇᴅ</b>\n\n"
            "NSFW filtering has been turned off for this group.\n"
            "Use <code>/nsfw on</code> to re-enable."
            "</blockquote>",
            parse_mode=ParseMode.HTML,
        )


@app.on_message(
    filters.text & filters.group
)
async def check_text_nsfw(client, message: Message):
    if not await is_content_guard_on(message.chat.id):
        return

    try:
        sender_id = message.from_user.id if message.from_user else None
        if sender_id and await _is_admin(client, message.chat.id, sender_id):
            return
    except Exception:
        pass

    text = message.text or ""
    if text:
        bad_word = is_bad_text(text)
        if bad_word:
            await _delete_and_warn(
                message,
                f"Explicit keyword detected: <code>{bad_word}</code>",
            )
