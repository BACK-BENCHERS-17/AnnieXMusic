import os
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChannelInvalid, ChannelPrivate
from ANNIEMUSIC import app
from ANNIEMUSIC.misc import SUDOERS


@app.on_message(filters.command("givelink"))
async def give_link_command(client: Client, message: Message):
    try:
        link = await app.export_chat_invite_link(message.chat.id)
        await message.reply_text(
            f"<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>ɪɴᴠɪᴛᴇ ʟɪɴᴋ ғᴏʀ</b> <code>{message.chat.title}</code></blockquote>\n"
            f"<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> {link}</blockquote>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.reply_text(
            f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Error generating link:</b>\n<code>{e}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )


@app.on_message(filters.command(["link", "invitelink"], prefixes=["/", "!", ".", "#", "?"]) & SUDOERS)
async def link_command_handler(client: Client, message: Message):
    if len(message.command) != 2:
        return await message.reply(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Usage:</b> <code>/link &lt;group_id&gt;</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

    group_id = message.command[1]
    file_name = f"group_info_{group_id}.txt"

    try:
        chat = await client.get_chat(int(group_id))
        if not chat:
            return await message.reply(
                "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Could not fetch group info.</b></blockquote>",
                parse_mode=ParseMode.HTML
            )

        try:
            invite_link = await client.export_chat_invite_link(chat.id)
        except (ChannelInvalid, ChannelPrivate):
            return await message.reply(
                "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>I don't have access to this group/channel.</b></blockquote>",
                parse_mode=ParseMode.HTML
            )
        except FloodWait as e:
            return await message.reply(
                f"<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>Rate limit:</b> wait <code>{e.value}</code> seconds.</blockquote>",
                parse_mode=ParseMode.HTML
            )

        group_data = {
            "id": chat.id,
            "type": str(chat.type),
            "title": chat.title,
            "members_count": chat.members_count,
            "description": chat.description,
            "invite_link": invite_link,
            "is_verified": chat.is_verified,
            "is_restricted": chat.is_restricted,
            "is_creator": chat.is_creator,
            "is_scam": chat.is_scam,
            "is_fake": chat.is_fake,
            "dc_id": chat.dc_id,
            "has_protected_content": chat.has_protected_content,
        }

        with open(file_name, "w", encoding="utf-8") as file:
            for key, value in group_data.items():
                file.write(f"{key}: {value}\n")

        await client.send_document(
            chat_id=message.chat.id,
            document=file_name,
            caption=(
                f"<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>ɢʀᴏᴜᴘ ɪɴғᴏ ꜰᴏʀ</b> <code>{chat.title}</code></blockquote>\n"
                f"<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>sᴄʀᴀᴘᴇᴅ ʙʏ:</b> @{app.username}</blockquote>"
            ),
            parse_mode=ParseMode.HTML
        )

    except ValueError:
        await message.reply(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Invalid group ID.</b> Please provide a valid group ID.</blockquote>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.reply_text(
            f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Error:</b>\n<code>{str(e)}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

    finally:
        if os.path.exists(file_name):
            os.remove(file_name)
