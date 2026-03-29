"""
Broadcast Plugin — Annie Music Bot
/broadcast  (or /bc) — SUDOERS only
Flags:
  -pin        : pin in groups silently
  -pinloud    : pin in groups with notification
  -user       : also broadcast to served users
  -nf         : remove forward tag (copies the message cleanly)
Premium emoji entities are always preserved regardless of the -nf flag.
"""

import asyncio
import logging

from pyrogram import filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message

from ANNIEMUSIC import app
from ANNIEMUSIC.misc import SUDOERS
from ANNIEMUSIC.utils.database import (
    get_active_chats,
    get_authuser_names,
    get_served_chats,
    get_served_users,
)
from ANNIEMUSIC.utils.decorators.language import language
from ANNIEMUSIC.utils.formatters import alpha_to_int
from config import adminlist
from pyrogram.enums import ChatMembersFilter

logger = logging.getLogger(__name__)

IS_BROADCASTING = False

_ANNIE = (
    "<blockquote>"
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
    "</blockquote>"
)


async def _send_or_copy(
    chat_id: int,
    from_chat_id: int,
    message_id: int,
    no_forward: bool,
    text_msg: str = None,
):
    """
    If no_forward=True  → copy_message (no forward tag, entities/premium emoji preserved).
    If no_forward=False → forward_messages (shows 'Forwarded from ...' tag).
    If text_msg is set  → plain send_message (no reply needed).
    """
    if text_msg is not None:
        return await app.send_message(chat_id, text=text_msg)
    if no_forward:
        return await app.copy_message(
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
        )
    else:
        return await app.forward_messages(
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_ids=message_id,
        )


async def _do_broadcast(client, message: Message):
    global IS_BROADCASTING

    flags_all = ["-pin", "-pinloud", "-user", "-nf", "-noforward"]
    no_forward = "-nf" in message.text or "-noforward" in message.text
    do_pin = "-pin" in message.text and "-pinloud" not in message.text
    do_pinloud = "-pinloud" in message.text
    do_user = "-user" in message.text

    text_msg = None
    from_chat_id = None
    message_id = None

    if message.reply_to_message:
        from_chat_id = message.chat.id
        message_id = message.reply_to_message.id
    else:
        if len(message.command) < 2:
            return await message.reply_text(
                f"{_ANNIE}\n\n"
                "<blockquote>"
                "<emoji id='5042334757040423886'>⚡️</emoji> "
                "<b>ʙʀᴏᴀᴅᴄᴀsᴛ ᴜsᴀɢᴇ</b>\n\n"
                "Reply to a message OR:\n"
                "<code>/bc [text]</code>\n\n"
                "<b>Flags:</b>\n"
                "• <code>-pin</code>   — pin silently\n"
                "• <code>-pinloud</code>   — pin with notification\n"
                "• <code>-user</code>  — also send to users\n"
                "• <code>-nf</code>    — remove forward tag</blockquote>"
            )
        query = message.text.split(None, 1)[1]
        for flag in flags_all:
            query = query.replace(flag, "")
        query = query.strip()
        if not query:
            return await message.reply_text(
                f"{_ANNIE}\n\n"
                "<blockquote><emoji id='5042334757040423886'>⚡️</emoji> "
                "<b>ᴘʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ sᴏᴍᴇ ᴛᴇxᴛ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ.</b></blockquote>"
            )
        text_msg = query

    IS_BROADCASTING = True
    nf_note = " <code>[ɴᴏ ꜰᴏʀᴡᴀʀᴅ ᴛᴀɢ]</code>" if no_forward else ""
    await message.reply_text(
        f"{_ANNIE}\n\n"
        f"<blockquote><emoji id='5041975203853239332'>🎁</emoji> "
        f"<b>ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ...{nf_note}</b></blockquote>"
    )

    sent = 0
    pin = 0
    chats = [int(c["chat_id"]) for c in await get_served_chats()]

    for chat_id in chats:
        try:
            m = await _send_or_copy(
                chat_id=chat_id,
                from_chat_id=from_chat_id,
                message_id=message_id,
                no_forward=no_forward,
                text_msg=text_msg,
            )
            if do_pin:
                try:
                    await m.pin(disable_notification=True)
                    pin += 1
                except Exception:
                    pass
            elif do_pinloud:
                try:
                    await m.pin(disable_notification=False)
                    pin += 1
                except Exception:
                    pass
            sent += 1
            await asyncio.sleep(0.2)
        except FloodWait as fw:
            flood_time = int(fw.value)
            if flood_time > 200:
                continue
            await asyncio.sleep(flood_time)
        except Exception:
            continue

    try:
        await message.reply_text(
            f"{_ANNIE}\n\n"
            f"<blockquote>"
            f"<emoji id='5041975203853239332'>🎁</emoji> <b>ʙʀᴏᴀᴅᴄᴀsᴛ ᴅᴏɴᴇ</b>\n\n"
            f"<emoji id='5972072533833289156'>🔹</emoji> "
            f"ʙʀᴏᴀᴅᴄᴀsᴛᴇᴅ ᴛᴏ <code>{sent}</code> ɢʀᴏᴜᴩs "
            f"ᴡɪᴛʜ <code>{pin}</code> ᴩɪɴs.</blockquote>"
        )
    except Exception:
        pass

    if do_user:
        susr = 0
        users = [int(u["user_id"]) for u in await get_served_users()]
        for user_id in users:
            try:
                await _send_or_copy(
                    chat_id=user_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                    no_forward=no_forward,
                    text_msg=text_msg,
                )
                susr += 1
                await asyncio.sleep(0.2)
            except FloodWait as fw:
                flood_time = int(fw.value)
                if flood_time > 200:
                    continue
                await asyncio.sleep(flood_time)
            except Exception:
                continue
        try:
            await message.reply_text(
                f"{_ANNIE}\n\n"
                f"<blockquote>"
                f"<emoji id='5041975203853239332'>🎁</emoji> <b>ᴜsᴇʀ ʙʀᴏᴀᴅᴄᴀsᴛ ᴅᴏɴᴇ</b>\n\n"
                f"<emoji id='5972072533833289156'>🔹</emoji> "
                f"ʙʀᴏᴀᴅᴄᴀsᴛᴇᴅ ᴛᴏ <code>{susr}</code> ᴜsᴇʀs.</blockquote>"
            )
        except Exception:
            pass

    IS_BROADCASTING = False


@app.on_message(
    filters.command(["broadcast", "bc"], prefixes=["/", "!", "."]) & SUDOERS
)
@language
async def broadcast_command(client, message: Message, _):
    await _do_broadcast(client, message)


async def _admin_list_refresh():
    """Background task — keeps adminlist fresh every 10 seconds."""
    while not await asyncio.sleep(10):
        try:
            served_chats = await get_active_chats()
            for chat_id in served_chats:
                if chat_id not in adminlist:
                    adminlist[chat_id] = []
                    async for user in app.get_chat_members(
                        chat_id, filter=ChatMembersFilter.ADMINISTRATORS
                    ):
                        if getattr(user.privileges, "can_manage_video_chats", False):
                            adminlist[chat_id].append(user.user.id)
                    authusers = await get_authuser_names(chat_id)
                    for user in authusers:
                        uid = await alpha_to_int(user)
                        adminlist[chat_id].append(uid)
        except Exception:
            continue


asyncio.create_task(_admin_list_refresh())
