from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.types import CallbackQuery

from ANNIEMUSIC import app
from ANNIEMUSIC.utils.stream.stream import NSFW_WHITELIST


@app.on_callback_query(filters.regex(r"^nsfw_unblock#"))
async def nsfw_unblock_callback(client: Client, cb: CallbackQuery):
    try:
        member = await client.get_chat_member(cb.message.chat.id, cb.from_user.id)
        if member.status not in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
            return await cb.answer(
                "❌ Sirf group owner ya admin hi unblock kar sakta hai!",
                show_alert=True,
            )
    except Exception:
        return await cb.answer("❌ Permission check fail ho gaya.", show_alert=True)

    try:
        parts = cb.data.split("#", 3)
        _, chat_id_str, vidid, track_title = parts
        chat_id = int(chat_id_str)
    except Exception:
        return await cb.answer("❌ Invalid unblock data.", show_alert=True)

    if chat_id not in NSFW_WHITELIST:
        NSFW_WHITELIST[chat_id] = set()
    NSFW_WHITELIST[chat_id].add(vidid)

    admin_mention = f"<a href='tg://user?id={cb.from_user.id}'>{cb.from_user.first_name}</a>"

    await cb.answer("✅ Track unblock ho gaya! Ab play kar sakte hain.", show_alert=True)

    try:
        await cb.message.edit_text(
            "<blockquote>"
            "✅ <b>Track Unblocked!</b>\n\n"
            f"🎵 <b>Track:</b> {track_title}\n"
            f"👤 <b>Unblock kiya:</b> {admin_mention}\n\n"
            "Is track ko admin ne allow kar diya hai.\n"
            "Ab yeh track is group mein play ho sakta hai."
            "</blockquote>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass
