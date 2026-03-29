from pyrogram import filters
from pyrogram.types import Message

from ANNIEMUSIC import app
from ANNIEMUSIC.utils.database import (
    disable_247,
    enable_247,
    is_24_7,
    is_active_chat,
)
from ANNIEMUSIC.utils.decorators import AdminRightsCheck
from ANNIEMUSIC.utils.inline import close_markup
from config import BANNED_USERS


@app.on_message(
    filters.command(["247", "nonstop"], prefixes=["/", ".", "!"])
    & filters.group
    & ~BANNED_USERS
)
@AdminRightsCheck
async def mode_247(cli, message: Message, _, chat_id):
    current = await is_24_7(chat_id)

    if current:
        await disable_247(chat_id)
        await message.reply_text(
            "<blockquote><b>⚡️ 24/7 ᴍᴏᴅᴇ ᴅɪsᴀʙʟᴇᴅ</b>\n\n"
            "ʙᴏᴛ ᴡɪʟʟ ɴᴏᴡ ʟᴇᴀᴠᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ᴡʜᴇɴ ǫᴜᴇᴜᴇ ɪs ᴇᴍᴘᴛʏ.\n\n"
            f"<b>ʙʏ :</b> {message.from_user.mention}</blockquote>",
            reply_markup=close_markup(_),
        )
    else:
        await enable_247(chat_id)
        await message.reply_text(
            "<blockquote><b>⚡️ 24/7 ᴍᴏᴅᴇ ᴇɴᴀʙʟᴇᴅ</b>\n\n"
            "ʙᴏᴛ ᴡɪʟʟ sᴛᴀʏ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ᴇᴠᴇɴ ᴡʜᴇɴ ǫᴜᴇᴜᴇ ɪs ᴇᴍᴘᴛʏ.\n\n"
            f"<b>ʙʏ :</b> {message.from_user.mention}</blockquote>",
            reply_markup=close_markup(_),
        )
