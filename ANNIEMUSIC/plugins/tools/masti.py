import random
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from ANNIEMUSIC import app
from config import SUPPORT_CHAT

BUTTON = InlineKeyboardMarkup([[InlineKeyboardButton("ꜱᴜᴘᴘᴏʀᴛ", url=SUPPORT_CHAT)]])

MEDIA = {
    "cutie": "https://graph.org/file/24375c6e54609c0e4621c.mp4",
    "horny": "https://graph.org/file/eaa834a1cbfad29bd1fe4.mp4",
    "hot": "https://graph.org/file/745ba3ff07c1270958588.mp4",
    "sexy": "https://graph.org/file/58da22eb737af2f8963e6.mp4",
    "gay": "https://graph.org/file/850290f1f974c5421ce54.mp4",
    "lesbian": "https://graph.org/file/ff258085cf31f5385db8a.mp4",
    "boob": "https://i.gifer.com/8ZUg.gif",
    "cock": "https://telegra.ph/file/423414459345bf18310f5.gif",
}

TEMPLATES = {
    "cutie": "🍑 {mention} ɪꜱ {percent}% ᴄᴜᴛᴇ ʙᴀʙʏ🥀",
    "horny": "🔥 {mention} ɪꜱ {percent}% ʜᴏʀɴʏ!",
    "hot": "🔥 {mention} ɪꜱ {percent}% ʜᴏᴛ!",
    "sexy": "💋 {mention} ɪꜱ {percent}% ꜱᴇxʏ!",
    "gay": "🍷 {mention} ɪꜱ {percent}% ɢᴀʏ!",
    "lesbian": "💜 {mention} ɪꜱ {percent}% ʟᴇꜱʙɪᴀɴ!",
    "boob": "🍒 {mention}ꜱ ʙᴏᴏʙ ꜱɪᴢᴇ ɪꜱ {percent}!",
    "cock": "🍆 {mention} ᴄᴏᴄᴋ ꜱɪᴢᴇ ɪꜱ {percent}ᴄᴍ!",
}


def get_reply_id(message: Message) -> int | None:
    return message.reply_to_message.message_id if message.reply_to_message else None


async def get_user_mention(client, message: Message) -> str:
    user = None
    if message.reply_to_message:
        user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            user = await client.get_users(message.command[1])
        except Exception:
            pass
    
    if not user:
        return None

    return f"<a href=\"tg://user?id={user.id}\">{user.first_name}</a>"


async def handle_percentage_command(client, message: Message):
    command = message.command[0].lower()
    if command not in MEDIA or command not in TEMPLATES:
        return

    mention = await get_user_mention(client, message)
    if not mention:
         return await message.reply_text(f"⚠️ ᴘʟᴇᴀsᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜsᴇʀ ᴏʀ ᴍᴇɴᴛɪᴏɴ sᴏᴍᴇᴏɴᴇ ᴛᴏ ᴄʜᴇᴄᴋ {command} ᴘᴇʀᴄᴇɴᴛᴀɢᴇ!")

    percent = random.randint(1, 100)
    text = TEMPLATES[command].format(mention=mention, percent=percent)
    media_url = MEDIA[command]

    await app.send_document(
        message.chat.id,
        media_url,
        caption=text,
        reply_markup=BUTTON,
        reply_to_message_id=get_reply_id(message),
        parse_mode=enums.ParseMode.HTML,
    )


for cmd in ["cutie", "horny", "hot", "sexy", "gay", "lesbian", "boob", "cock"]:
    app.on_message(filters.command(cmd))(handle_percentage_command)
