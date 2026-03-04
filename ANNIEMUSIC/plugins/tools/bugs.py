from datetime import datetime
from pyrogram import filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from pyrogram.enums import ParseMode
from config import OWNER_ID
from ANNIEMUSIC import app


def extract_bug_content(msg: Message) -> str | None:
    return msg.text.split(None, 1)[1] if msg.text and " " in msg.text else None


def escape_md(text: str) -> str:
    return text.replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')


@app.on_message(filters.command("bug"))
async def report_bug(_, msg: Message):
    if msg.chat.type == "private":
        return await msg.reply_text("<b>ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪs ᴏɴʟʏ ғᴏʀ ɢʀᴏᴜᴘs.</b>")

    bug_description = extract_bug_content(msg)
    if not bug_description:
        return await msg.reply_text("<b>ɴᴏ ʙᴜɢ ᴅᴇsᴄʀɪᴘᴛɪᴏɴ ᴘʀᴏᴠɪᴅᴇᴅ. ᴘʟᴇᴀsᴇ sᴘᴇᴄɪғʏ ᴛʜᴇ ʙᴜɢ.</b>")

    user_id = msg.from_user.id
    user_name = escape_md(msg.from_user.first_name)
    mention = f"<a href=\"tg://user?id={user_id}\">{user_name}</a>"

    chat_reference = (
        f"@{msg.chat.username}/`{msg.chat.id}`"
        if msg.chat.username
        else f"ᴘʀɪᴠᴀᴛᴇ ɢʀᴏᴜᴘ/`{msg.chat.id}`"
    )

    current_date = datetime.utcnow().strftime("%d-%m-%Y")

    bug_report = (
        f"<b>#ʙᴜɢ ʀᴇᴘᴏʀᴛ</b>\n"
        f"<b>ʀᴇᴘᴏʀᴛᴇᴅ ʙʏ:</b> {mention}\n"
        f"<b>ᴜsᴇʀ ɪᴅ:</b> `{user_id}`\n"
        f"<b>ᴄʜᴀᴛ:</b> {chat_reference}\n"
        f"<b>ʙᴜɢ ᴅᴇsᴄʀɪᴘᴛɪᴏɴ:</b> `{escape_md(bug_description)}`\n"
        f"<b>ᴅᴀᴛᴇ:</b> `{current_date}`"
    )

    if user_id == OWNER_ID:
        return await msg.reply_text(
            "<b>ʏᴏᴜ ᴀʀᴇ ᴛʜᴇ ᴏᴡɴᴇʀ ᴏғ ᴛʜᴇ ʙᴏᴛ. ᴘʟᴇᴀsᴇ ᴀᴅᴅʀᴇss ᴛʜᴇ ʙᴜɢ ᴅɪʀᴇᴄᴛʟʏ.</b>"
        )

    await msg.reply_text(
        "<b>ʙᴜɢ ʀᴇᴘᴏʀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close_data")]]
        ),
    )

    # Send report to log group
    buttons = [[InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close_send_photo")]]
    if msg.chat.username:
        link = f"https://t.me/{msg.chat.username}/{msg.id}"
        buttons.insert(0, [InlineKeyboardButton("ᴠɪᴇᴡ ʙᴜɢ", url=link)])

    await app.send_message(
        -1002077986660,
        bug_report,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )


@app.on_callback_query(filters.regex("close_send_photo"))
async def close_bug_report(_, query: CallbackQuery):
    try:
        member = await app.get_chat_member(query.message.chat.id, query.from_user.id)
        if not member.privileges or not member.privileges.can_delete_messages:
            return await query.answer("ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪssɪᴏɴ ᴛᴏ ᴅᴇʟᴇᴛᴇ ᴛʜɪs.", show_alert=True)
    except:
        return await query.answer("ᴄᴏᴜʟᴅ ɴᴏᴛ ᴠᴇʀɪғʏ ᴀᴄᴄᴇss.", show_alert=True)

    await query.message.delete()
