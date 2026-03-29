from pyrogram import filters
from pyrogram.types import Message

from ANNIEMUSIC import app
from ANNIEMUSIC.core.call import JARVIS
from ANNIEMUSIC.utils.database import get_volume, is_active_chat, set_volume
from ANNIEMUSIC.utils.decorators import AdminRightsCheck
from ANNIEMUSIC.utils.decorators.language import language
from ANNIEMUSIC.utils.inline import close_markup
from config import BANNED_USERS


@app.on_message(
    filters.command(["volume", "vol", "cvol", "cvolume"], prefixes=["/", ".", "!"])
    & filters.group
    & ~BANNED_USERS
)
@AdminRightsCheck
async def volume_command(cli, message: Message, _, chat_id):
    if not await is_active_chat(chat_id):
        return await message.reply_text(_["general_5"])

    if len(message.command) < 2:
        current = await get_volume(chat_id)
        return await message.reply_text(
            f"<blockquote><b>🔊 ᴄᴜʀʀᴇɴᴛ ᴠᴏʟᴜᴍᴇ : <code>{current}%</code></b>\n\n"
            f"ᴜsᴀɢᴇ: /volume [0-200]\n"
            f"ᴇxᴀᴍᴘʟᴇ: /volume 150</blockquote>",
            reply_markup=close_markup(_),
        )

    try:
        vol = int(message.command[1])
    except ValueError:
        return await message.reply_text(
            "<blockquote>» ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ ʙᴇᴛᴡᴇᴇɴ 0 ᴀɴᴅ 200.</blockquote>"
        )

    if vol < 0 or vol > 200:
        return await message.reply_text(
            "<blockquote>» ᴠᴏʟᴜᴍᴇ ᴍᴜsᴛ ʙᴇ ʙᴇᴛᴡᴇᴇɴ <code>0</code> ᴀɴᴅ <code>200</code>.</blockquote>"
        )

    try:
        assistant = await JARVIS.group_assistant(chat_id)
        client = JARVIS.pytgcalls[assistant]
        await client.change_volume_call(chat_id, vol)
    except Exception:
        return await message.reply_text(
            "<blockquote>» ғᴀɪʟᴇᴅ ᴛᴏ ᴄʜᴀɴɢᴇ ᴠᴏʟᴜᴍᴇ. ᴍᴀᴋᴇ sᴜʀᴇ sᴛʀᴇᴀᴍ ɪs ᴀᴄᴛɪᴠᴇ.</blockquote>"
        )

    await set_volume(chat_id, vol)
    bar = "█" * (vol // 20) + "░" * (10 - vol // 20)
    await message.reply_text(
        f"<blockquote><b>🔊 ᴠᴏʟᴜᴍᴇ ᴄʜᴀɴɢᴇᴅ</b>\n\n"
        f"[{bar}] <code>{vol}%</code>\n\n"
        f"<b>ʙʏ :</b> {message.from_user.mention}</blockquote>",
        reply_markup=close_markup(_),
    )
