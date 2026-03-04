from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message

from ANNIEMUSIC import app


@app.on_message(filters.command("id"))
async def get_id(client, message: Message):
    chat, user, reply = message.chat, message.from_user, message.reply_to_message
    out = []

    if message.link:
        out.append(f"<b><a href=\"{message.link}\">ᴍᴇssᴀɢᴇ ɪᴅ:</a></b> <code>{message.id}</code>")
    else:
        out.append(f"<b>ᴍᴇssᴀɢᴇ ɪᴅ:</b> <code>{message.id}</code>")

    out.append(f"<b><a href=\"tg://user?id={user.id}\">ʏᴏᴜʀ ɪᴅ:</a></b> <code>{user.id}</code>")

    if len(message.command) == 2:
        try:
            target = message.text.split(maxsplit=1)[1]
            tgt_user = await client.get_users(target)
            out.append(f"<b><a href=\"tg://user?id={tgt_user.id}\">ᴜsᴇʀ ɪᴅ:</a></b> <code>{tgt_user.id}</code>")
        except Exception:
            return await message.reply_text("<b>ᴛʜɪs ᴜsᴇʀ ᴅᴏᴇsɴ'ᴛ ᴇxɪsᴛ.</b>", quote=True)

    if chat.username and chat.type != "private":
        out.append(f"<b><a href=\"https://t.me/{chat.username}\">ᴄʜᴀᴛ ɪᴅ:</a></b> <code>{chat.id}</code>")
    else:
        out.append(f"<b>ᴄʜᴀᴛ ɪᴅ:</b> <code>{chat.id}</code>")

    if reply:
        if reply.link:
            out.append(f"<b><a href=\"{reply.link}\">ʀᴇᴘʟɪᴇᴅ ᴍᴇssᴀɢᴇ ɪᴅ:</a></b> <code>{reply.id}</code>")
        else:
            out.append(f"<b>ʀᴇᴘʟɪᴇᴅ ᴍᴇssᴀɢᴇ ɪᴅ:</b> <code>{reply.id}</code>")

        if reply.from_user:
            out.append(
                f"<b><a href=\"tg://user?id={reply.from_user.id}\">ʀᴇᴘʟɪᴇᴅ ᴜsᴇʀ ɪᴅ:</a></b> "
                f"<code>{reply.from_user.id}</code>"
            )

        if reply.forward_from_chat:
            out.append(
                f"ᴛʜᴇ ғᴏʀᴡᴀʀᴅᴇᴅ ᴄʜᴀɴɴᴇʟ <b>{reply.forward_from_chat.title}</b> "
                f"ʜᴀs ɪᴅ <code>{reply.forward_from_chat.id}</code>"
            )

        if reply.sender_chat:
            out.append(f"ɪᴅ ᴏғ ᴛʜᴇ ʀᴇᴘʟɪᴇᴅ ᴄʜᴀᴛ/ᴄʜᴀɴɴᴇʟ: <code>{reply.sender_chat.id}</code>")

    await message.reply_text(
        "\n".join(out),
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML,
    )
