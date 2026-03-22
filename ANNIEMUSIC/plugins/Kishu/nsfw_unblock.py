from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.types import CallbackQuery

from ANNIEMUSIC import app
from ANNIEMUSIC.utils.stream.stream import NSFW_WHITELIST


@app.on_callback_query(filters.regex(r"^nsfw_unblock#"))
async def nsfw_unblock_callback(client: Client, cb: CallbackQuery):
    try:
        parts = cb.data.split("#", 3)
        _, group_chat_id_str, vidid, track_title = parts
        group_chat_id = int(group_chat_id_str)
    except Exception:
        return await cb.answer("❌ Invalid unblock data.", show_alert=True)

    # Verify the person clicking is owner/admin of the actual group
    try:
        member = await client.get_chat_member(group_chat_id, cb.from_user.id)
        if member.status not in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
            return await cb.answer(
                "❌ Sirf group owner ya admin hi unblock kar sakta hai!",
                show_alert=True,
            )
    except Exception:
        return await cb.answer("❌ Permission check fail ho gaya.", show_alert=True)

    # Add to whitelist
    if group_chat_id not in NSFW_WHITELIST:
        NSFW_WHITELIST[group_chat_id] = set()
    NSFW_WHITELIST[group_chat_id].add(vidid)

    await cb.answer("✅ Track unblock ho gaya! Ab group mein play kar sakte hain.", show_alert=True)

    try:
        await cb.message.edit_text(
            "<blockquote>"
            "✅ <b>Track Unblocked!</b>\n\n"
            f"🎵 <b>Track:</b> {track_title}\n\n"
            "Aapne is track ko allow kar diya hai.\n"
            "Ab yeh track us group mein play ho sakta hai."
            "</blockquote>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass
