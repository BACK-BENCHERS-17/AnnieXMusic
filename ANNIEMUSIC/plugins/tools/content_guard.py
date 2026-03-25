import asyncio
from concurrent.futures import ThreadPoolExecutor

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.types import Message

from ANNIEMUSIC import app
from ANNIEMUSIC.utils.content_filter import analyze_image_bytes, is_bad_text
from ANNIEMUSIC.utils.database import (
    content_guard_off,
    content_guard_on,
    is_content_guard_on,
)

_executor = ThreadPoolExecutor(max_workers=2)


async def _run_image_check(image_bytes: bytes) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, analyze_image_bytes, image_bytes)


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
    (filters.photo | filters.sticker | filters.animation) & filters.group
)
async def check_media(client, message: Message):
    if not await is_content_guard_on(message.chat.id):
        return

    try:
        sender_id = message.from_user.id if message.from_user else None
        if sender_id and await _is_admin(client, message.chat.id, sender_id):
            return
    except Exception:
        pass

    caption = message.caption or ""
    if caption:
        bad_word = is_bad_text(caption)
        if bad_word:
            await _delete_and_warn(
                message,
                f"Explicit keyword in caption: <code>{bad_word}</code>",
            )
            return

    if message.sticker:
        sticker = message.sticker
        set_name = (sticker.set_name or "").lower()
        emoji = sticker.emoji or ""
        combined = f"{set_name} {emoji}"
        bad_word = is_bad_text(combined)
        if bad_word:
            await _delete_and_warn(
                message,
                f"NSFW sticker pack detected: <code>{bad_word}</code>",
            )
        return

    if message.photo or message.animation:
        try:
            if message.photo:
                file_id = message.photo.file_id
            else:
                anim = message.animation
                size = getattr(anim, "file_size", None) or 0
                file_id = anim.file_id if size <= 5_000_000 else None
                if not file_id:
                    return

            downloaded = await client.download_media(file_id, in_memory=True)
            if not downloaded:
                return
            image_bytes = bytes(downloaded.getvalue()) if hasattr(downloaded, "getvalue") else bytes(downloaded)
        except Exception:
            return

        is_nsfw = await _run_image_check(image_bytes)
        if is_nsfw:
            await _delete_and_warn(
                message,
                "18+ / explicit visual content detected.",
            )
