import io

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


async def _is_admin(client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )
    except Exception:
        return False


@app.on_message(
    filters.command(["contentguard", "cguard"]) & filters.group
)
async def content_guard_cmd(client, message: Message):
    if not message.from_user:
        return await message.reply_text(
            "<b>❌ Anonymous admins cannot use this command.</b>"
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
            f"<b>🛡️ Content Guard - {status}</b>\n\n"
            "<b>Usage:</b>\n"
            "<code>/contentguard on</code> — Enable protection\n"
            "<code>/contentguard off</code> — Disable protection\n\n"
            "<b>Kya karta hai:</b>\n"
            "• 18+ images/stickers automatically delete hoti hain\n"
            "• Drugs/explicit content ki images delete hoti hain\n"
            "• Play command mein bhi bad keywords block hote hain"
        )

    if args[1].lower() == "on":
        await content_guard_on(message.chat.id)
        await message.reply_text(
            "<b>🛡️ Content Guard: ✅ ON</b>\n\n"
            "Ab is group mein:\n"
            "• 18+ aur drugs wali images/stickers auto-delete ho jayengi\n"
            "• Bad keywords wale songs/videos play nahi honge\n\n"
            "<i>Group safe hai! 🔒</i>"
        )
    else:
        await content_guard_off(message.chat.id)
        await message.reply_text(
            "<b>🛡️ Content Guard: ❌ OFF</b>\n\n"
            "Content filtering disabled kar diya gaya hai."
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
    if caption and is_bad_text(caption):
        try:
            await message.delete()
            warning = await message.reply_text(
                "🚫 <b>Message delete kar diya gaya!</b>\n"
                "Caption mein inappropriate content tha.\n"
                "<i>Content Guard active hai is group mein.</i>"
            )
            import asyncio
            await asyncio.sleep(8)
            await warning.delete()
        except Exception:
            pass
        return

    if message.sticker:
        sticker = message.sticker
        sticker_name = (sticker.set_name or "").lower()
        emoji = sticker.emoji or ""
        combined = f"{sticker_name} {emoji}"
        if is_bad_text(combined):
            try:
                await message.delete()
                warning = await message.reply_text(
                    "🚫 <b>Sticker delete kar diya gaya!</b>\n"
                    "Inappropriate sticker pack detect hua.\n"
                    "<i>Content Guard active hai is group mein.</i>"
                )
                import asyncio
                await asyncio.sleep(8)
                await warning.delete()
            except Exception:
                pass
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

        is_nsfw = await analyze_image_bytes(image_bytes)
        if is_nsfw:
            try:
                await message.delete()
                warning = await message.reply_text(
                    "🚫 <b>Image delete kar diya gaya!</b>\n"
                    "18+ ya explicit content detect hua.\n"
                    "<i>Content Guard active hai is group mein.</i>"
                )
                import asyncio
                await asyncio.sleep(8)
                await warning.delete()
            except Exception:
                pass
