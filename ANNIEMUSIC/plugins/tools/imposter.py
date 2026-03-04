from pyrogram import filters
from pyrogram.types import Message
from ANNIEMUSIC import app
from ANNIEMUSIC.mongo.pretenderdb import (
    impo_off, impo_on, check_pretender,
    add_userdata, get_userdata, usr_data
)
from ANNIEMUSIC.utils.admin_filters import admin_filter

@app.on_message(filters.group & ~filters.bot & ~filters.via_bot, group=69)
async def chk_usr(_, message: Message):
    if message.sender_chat or not await check_pretender(message.chat.id):
        return
    if not await usr_data(message.from_user.id):
        return await add_userdata(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
    usernamebefore, first_name, lastname_before = await get_userdata(message.from_user.id)
    msg = ""
    if (
        usernamebefore != message.from_user.username
        or first_name != message.from_user.first_name
        or lastname_before != message.from_user.last_name
    ):
        msg += f"""
<b>🔓 ᴘʀᴇᴛᴇɴᴅᴇʀ ᴅᴇᴛᴇᴄᴛᴇᴅ 🔓</b>
━━━━━━━━━━━━━━━  
<b>🍊 ɴᴀᴍᴇ</b> : {message.from_user.mention}
<b>🍅 ᴜsᴇʀ ɪᴅ</b> : {message.from_user.id}
━━━━━━━━━━━━━━━  \n
"""
    if usernamebefore != message.from_user.username:
        usernamebefore = f"@{usernamebefore}" if usernamebefore else "NO USERNAME"
        usernameafter = (
            f"@{message.from_user.username}"
            if message.from_user.username
            else "NO USERNAME"
        )
        msg += """
<b>🐻‍❄️ ᴄʜᴀɴɢᴇᴅ ᴜsᴇʀɴᴀᴍᴇ 🐻‍❄️</b>
━━━━━━━━━━━━━━━  
<b>🎭 ғʀᴏᴍ</b> : {bef}
<b>🍜 ᴛᴏ</b> : {aft}
━━━━━━━━━━━━━━━  \n
""".format(bef=usernamebefore, aft=usernameafter)
        await add_userdata(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
    if first_name != message.from_user.first_name:
        msg += """
<b>🪧 ᴄʜᴀɴɢᴇs ғɪʀsᴛ ɴᴀᴍᴇ 🪧</b>
━━━━━━━━━━━━━━━  
<b>🔐 ғʀᴏᴍ</b> : {bef}
<b>🍓 ᴛᴏ</b> : {aft}
━━━━━━━━━━━━━━━  \n
""".format(
            bef=first_name, aft=message.from_user.first_name
        )
        await add_userdata(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
    if lastname_before != message.from_user.last_name:
        lastname_before = lastname_before or "NO LAST NAME"
        lastname_after = message.from_user.last_name or "NO LAST NAME"
        msg += """
<b>🪧 ᴄʜᴀɴɢᴇs ʟᴀsᴛ ɴᴀᴍᴇ 🪧</b>
━━━━━━━━━━━━━━━  
<b>🚏ғʀᴏᴍ</b> : {bef}
<b>🍕 ᴛᴏ</b> : {aft}
━━━━━━━━━━━━━━━  \n
""".format(
            bef=lastname_before, aft=lastname_after
        )
        await add_userdata(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
    if msg != "":
        await message.reply_photo("https://telegra.ph/file/58afe55fee5ae99d6901b.jpg", caption=msg)


@app.on_message(filters.group & filters.command("imposter") & ~filters.bot & ~filters.via_bot & admin_filter)
async def set_mataa(_, message: Message):
    if len(message.command) == 1:
        return await message.reply("ᴅᴇᴛᴇᴄᴛ ᴘʀᴇᴛᴇɴᴅᴇʀ ᴜsᴇʀs <b>ᴜsᴀɢᴇ:</b> `/imposter enable|disable`")
    if message.command[1] == "enable":
        cekset = await impo_on(message.chat.id)
        if cekset:
            await message.reply("<b>ᴘʀᴇᴛᴇɴᴅᴇʀ ᴍᴏᴅᴇ ɪs ᴀʟʀᴇᴀᴅʏ ᴇɴᴀʙʟᴇᴅ.</b>")
        else:
            await impo_on(message.chat.id)
            await message.reply(f"<b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴇɴᴀʙʟᴇᴅ ᴘʀᴇᴛᴇɴᴅᴇʀ ᴍᴏᴅᴇ ғᴏʀ</b> {message.chat.title}")
    elif message.command[1] == "disable":
        cekset = await impo_off(message.chat.id)
        if not cekset:
            await message.reply("<b>ᴘʀᴇᴛᴇɴᴅᴇʀ ᴍᴏᴅᴇ ɪs ᴀʟʀᴇᴀᴅʏ ᴅɪsᴀʙʟᴇᴅ.</b>")
        else:
            await impo_off(message.chat.id)
            await message.reply(f"<b>sᴜᴄᴄᴇssғᴜʟʟʏ ᴅɪsᴀʙʟᴇᴅ ᴘʀᴇᴛᴇɴᴅᴇʀ ᴍᴏᴅᴇ ғᴏʀ</b> {message.chat.title}")
    else:
        await message.reply("<b>ᴅᴇᴛᴇᴄᴛ ᴘʀᴇᴛᴇɴᴅᴇʀ ᴜsᴇʀs ᴜsᴀɢᴇ : ᴘʀᴇᴛᴇɴᴅᴇʀ ᴏɴ|ᴏғғ</b>")
