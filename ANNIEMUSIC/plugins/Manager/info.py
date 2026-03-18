import asyncio
from pyrogram import filters, enums, types
from pyrogram.errors import PeerIdInvalid, RPCError, FloodWait
from pyrogram.types import Message, InlineKeyboardMarkup
from ANNIEMUSIC.utils.inline import InlineKeyboardButton

from ANNIEMUSIC import app


def get_full_name(user):
    return f"{user.first_name} {user.last_name}" if user.last_name else user.first_name


def get_last_seen(status):
    if isinstance(status, str):
        status = status.replace("UserStatus.", "").lower()
    elif isinstance(status, enums.UserStatus):
        status = status.name.lower()

    return {
        "online": "☑️ ᴏɴʟɪɴᴇ",
        "offline": "❄️ ᴏғғʟɪɴᴇ",
        "recently": "⏱ ʀᴇᴄᴇɴᴛʟʏ",
        "last_week": "🗓 ʟᴀsᴛ ᴡᴇᴇᴋ",
        "last_month": "📆 ʟᴀsᴛ ᴍᴏɴᴛʜ",
        "long_ago": "😴 ʟᴏɴɢ ᴛɪᴍᴇ ᴀɢᴏ"
    }.get(status, "❓ ᴜɴᴋɴᴏᴡɴ")


@app.on_message(filters.command(["info", "userinfo", "whois"]))
async def whois_handler(_, message: Message):
    try:
        if message.reply_to_message:
            user = message.reply_to_message.from_user
        elif len(message.command) > 1:
            user = await app.get_users(message.command[1])
        else:
            user = message.from_user

        loading = await message.reply(
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>ɢᴀᴛʜᴇʀɪɴɢ ᴜsᴇʀ ɪɴғᴏ...</b></blockquote>",
            parse_mode=enums.ParseMode.HTML
        )
        await asyncio.sleep(0.5)

        chat_user = await app.get_chat(user.id)

        name = get_full_name(user)
        username = f"@{user.username}" if user.username else "ɴ/ᴀ"
        bio = chat_user.bio or "ɴᴏ ʙɪᴏ"
        dc_id = getattr(user, "dc_id", "ɴ/ᴀ")
        last_seen = get_last_seen(user.status)
        lang = getattr(user, "language_code", "ɴ/ᴀ")

        text = (
            f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>ᴜsᴇʀ ɪɴғᴏ</b></blockquote>\n"
            f"<blockquote>"
            f"<emoji id=\"5449449325434266744\">❄️</emoji> <b>ɪᴅ:</b> <code>{user.id}</code>\n"
            f"<emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>ɴᴀᴍᴇ:</b> {name}\n"
            f"<emoji id=\"5972072533833289156\">🔹</emoji> <b>ᴜsᴇʀɴᴀᴍᴇ:</b> {username}\n"
            f"<emoji id=\"5041975203853239332\">🎁</emoji> <b>ʟᴀsᴛ sᴇᴇɴ:</b> {last_seen}\n"
            f"<emoji id=\"5042334757040423886\">⚡️</emoji> <b>ᴅᴀᴛᴀᴄᴇɴᴛᴇʀ:</b> {dc_id}\n"
            f"<emoji id=\"5449449325434266744\">❄️</emoji> <b>ʟᴀɴɢᴜᴀɢᴇ:</b> {lang}"
            f"</blockquote>\n"
            f"<blockquote>"
            f"<emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>ᴠᴇʀɪғɪᴇᴅ:</b> {'ʏᴇs ✅' if user.is_verified else 'ɴᴏ'}\n"
            f"<emoji id=\"5972072533833289156\">🔹</emoji> <b>ᴘʀᴇᴍɪᴜᴍ:</b> {'ʏᴇs ☑️' if user.is_premium else 'ɴᴏ'}\n"
            f"<emoji id=\"5041975203853239332\">🎁</emoji> <b>ʙᴏᴛ:</b> {'ʏᴇs 🤖' if user.is_bot else 'ɴᴏ 👤'}\n"
            f"<emoji id=\"5042334757040423886\">⚡️</emoji> <b>sᴄᴀᴍ:</b> {'ʏᴇs ⚠️' if getattr(user, 'is_scam', False) else 'ɴᴏ ☑️'}\n"
            f"<emoji id=\"5449449325434266744\">❄️</emoji> <b>ғᴀᴋᴇ:</b> {'ʏᴇs 🎭' if getattr(user, 'is_fake', False) else 'ɴᴏ ☑️'}\n"
            f"<emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>ᴘʜᴏᴛᴏ:</b> {'ʏᴇs 🌠' if user.photo else 'ɴᴏ'}"
            f"</blockquote>\n"
            f"<blockquote><emoji id=\"5972072533833289156\">🔹</emoji> <b>ʙɪᴏ:</b> <code>{bio}</code></blockquote>"
        )

        profile_url = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton("👤 ᴠɪᴇᴡ ᴘʀᴏғɪʟᴇ", url=profile_url),
        ]])

        await app.edit_message_text(
            chat_id=message.chat.id,
            message_id=loading.id,
            text=text,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=buttons
        )

    except PeerIdInvalid:
        await message.reply(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Couldn't find that user.</b></blockquote>",
            parse_mode=enums.ParseMode.HTML
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await whois_handler(_, message)
    except RPCError as e:
        await message.reply(
            f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>RPC Error:</b>\n<code>{e}</code></blockquote>",
            parse_mode=enums.ParseMode.HTML
        )
    except Exception as e:
        await message.reply(
            f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Error:</b>\n<code>{e}</code></blockquote>",
            parse_mode=enums.ParseMode.HTML
        )
