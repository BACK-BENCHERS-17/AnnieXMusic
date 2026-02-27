from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from ANNIEMUSIC import app
from config import BOT_USERNAME

repo_caption = f"""**
<tg-emoji emoji-id=\"6197443727145835757\">✈️</tg-emoji> ᴄʟᴏɴᴇ ᴀɴᴅ ᴅᴇᴘʟᴏʏ – ᴘɢʟ_ʙ4ᴄʜɪ ʀᴇᴘᴏ <tg-emoji emoji-id=\"6197443727145835757\">✈️</tg-emoji>

➤ ᴅᴇᴘʟᴏʏ ᴇᴀsɪʟʏ ᴏɴ ʜᴇʀᴏᴋᴜ ᴡɪᴛʜᴏᴜᴛ ᴇʀʀᴏʀꜱ  
➤ ɴᴏ ʜᴇʀᴏᴋᴜ ʙᴀɴ ɪꜱꜱᴜᴇ  
➤ ɴᴏ ɪᴅ ʙᴀɴ ɪꜱꜱᴜᴇ  
➤ ᴜɴʟɪᴍɪᴛᴇᴅ ᴅʏɴᴏꜱ  
➤ ʀᴜɴ 24/7 ʟᴀɢ ꜰʀᴇᴇ

ɪꜰ ʏᴏᴜ ꜰᴀᴄᴇ ᴀɴʏ ᴘʀᴏʙʟᴇᴍ, ꜱᴇɴᴅ ꜱꜱ ɪɴ ꜱᴜᴘᴘᴏʀᴛ
**"""

@app.on_message(filters.command("repo"))
async def show_repo(_, msg):
    buttons = [
        [InlineKeyboardButton(
            "➕ ᴀᴅᴅ ᴍᴇ ʙᴀʙʏ ✨", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"
        )],
        [
            InlineKeyboardButton(
                "👑 ᴏᴡɴᴇʀ", url="https://t.me/PGL_B4CHI"
            ),
            InlineKeyboardButton(
                "💬 ꜱᴜᴘᴘᴏʀᴛ", url="https://t.me/AnnieSupportGroup"
            )
        ],
        [
            InlineKeyboardButton(
                "🛠️ ꜱᴜᴘᴘᴏʀᴛ ᴄʜᴀᴛ", url="https://t.me/AnnieSupportGroup"
            ),
            InlineKeyboardButton(
                "🎵 ɢɪᴛʜᴜʙ", url="https://github.com/PGL_B4CHI"
            )
        ]
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