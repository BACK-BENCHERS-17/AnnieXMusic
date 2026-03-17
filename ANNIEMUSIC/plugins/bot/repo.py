from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup
from ANNIEMUSIC.utils.inline import InlineKeyboardButton
from ANNIEMUSIC import app
from config import BOT_USERNAME

repo_caption = f"""<b>
<emoji id=\"6197443727145835757\">✈️</emoji> ᴀɴɴɪᴇ xᴍᴜsɪᴄ – ᴘʀᴇᴍɪᴜᴍ ᴍᴜsɪᴄ ʙᴏᴛ <emoji id=\"6197443727145835757\">✈️</emoji>

➤ ʟᴀɢ ꜰʀᴇᴇ ᴍᴜsɪᴄ sᴛʀᴇᴀᴍɪɴɢ
➤ ʜɪɢʜ ǫᴜᴀʟɪᴛʏ ᴀᴜᴅɪᴏ & ᴠɪᴅᴇᴏ
➤ 24/7 ᴜᴘᴛɪᴍᴇ
➤ ɴᴏ ᴘʀᴏᴍᴏ

ɪꜰ ʏᴏᴜ ꜰᴀᴄᴇ ᴀɴʏ ᴘʀᴏʙʟᴇᴍ, ꜱᴇɴᴅ ꜱꜱ ɪɴ ꜱᴜᴘᴘᴏʀᴛ
</b>"""

@app.on_message(filters.command("repo"))
async def show_repo(_, msg):
    buttons = [
        [InlineKeyboardButton(
            "˹ᴋɪᴅɴᴀᴘ ᴍᴇ ʙᴀʙᴇs˼", url=f"https://t.me/{BOT_USERNAME}?startgroup=true", style="primary"
        )],
        [
            InlineKeyboardButton(
                "˹sᴜᴘᴘᴏʀᴛ˼", url="https://t.me/AnnieSupportGroup", style="success"
            ),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    try:  
        await msg.reply_photo(
            photo="https://telegra.ph/file/58afe55fee5ae99d6901b.jpg",
            caption=repo_caption,
            reply_markup=reply_markup,
            has_spoiler=True,
        )
    except:
        pass