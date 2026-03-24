import asyncio
import io
from concurrent.futures import ThreadPoolExecutor

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
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
            f"🚫 <b>Message delete kar diya gaya!</b>\n"
            f"{reason}\n"
            f"<i>Content Guard active hai is group mein. 🛡️</i>"
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
            "<b>❌ Anonymous admins ye command use nahi kar sakte.</b>"
        )

    if not await _is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text(
            "<b>❌ Sirf group admins hi ye command use kar sakte hain.</b>"
        )

    args = message.command
    if len(args) < 2 or args[1].lower() not in ("on", "off"):
        enabled = await is_content_guard_on(message.chat.id)
        status = "✅ ON" if enabled else "❌ OFF"
        return await message.reply_text(
            f"<b>🛡️ NSFW Filter - {status}</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/nsfw on</code>  — Filter ON karo\n"
            "<code>/nsfw off</code> — Filter OFF karo\n\n"
            "<b>Kya protect karta hai:</b>\n"
            "• 18+ images automatic delete\n"
            "• Explicit / drugs wale keywords delete\n"
            "• NSFW sticker packs delete\n"
            "• NSFW thumbnail wale songs block"
        )

    if args[1].lower() == "on":
        await content_guard_on(message.chat.id)
        await message.reply_text(
            "<b>🛡️ NSFW Filter: ✅ ON</b>\n\n"
            "Ab is group mein:\n"
            "• 18+ aur explicit images auto-delete hongi\n"
            "• NSFW stickers bhi pakde jayenge\n"
            "• Explicit keywords wale messages delete honge\n\n"
            "<i>Group safe hai! 🔒</i>"
        )
    else:
        await content_guard_off(message.chat.id)
        await message.reply_text(
            "<b>🛡️ NSFW Filter: ❌ OFF</b>\n\n"
            "NSFW filtering disable ho gaya."
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
                f"Caption mein inappropriate content mila: <code>{bad_word}</code>"
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
                f"Inappropriate sticker pack detect hua: <code>{bad_word}</code>"
            )
        return

    if message.photo or message.animation:
        file_obj = message.photo or message.animation
        try:
            buf = io.BytesIO()
            await client.download_media(file_obj, file_name=buf)
            buf.seek(0)
            image_bytes = buf.read()
        except Exception:
            return

        is_nsfw = await _run_image_check(image_bytes)
        if is_nsfw:
            await _delete_and_warn(
                message,
                "18+ ya explicit content detect hua (skin analysis)."
            )
