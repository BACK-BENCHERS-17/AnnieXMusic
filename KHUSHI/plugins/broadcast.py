"""KHUSHI — Broadcast Plugin (forward-tag removal + premium emoji)."""

import asyncio

from pyrogram import filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, Message

from KHUSHI.utils.inline import InlineKeyboardButton

from KHUSHI import app
from KHUSHI.utils.database import get_served_chats, get_served_users
from config import OWNER_ID, adminlist
from pyrogram.enums import ChatMembersFilter
from KHUSHI.utils.database import get_active_chats, get_authuser_names
from KHUSHI.utils.formatters import alpha_to_int

_BRAND = (
    "<blockquote>"
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
    "</blockquote>"
)

_USAGE = (
    f"{_BRAND}\n\n"
    "<blockquote>"
    "<emoji id='5042334757040423886'>⚡️</emoji> <b>ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴜꜱᴀɢᴇ</b>\n\n"
    "Reply to a message <b>OR</b> write text:\n"
    "  <code>/bc [text]</code>\n"
    "  <code>/broadcast [text]</code>\n\n"
    "<b>Flags:</b>\n"
    "  <code>-pin</code>      — ꜱɪʟᴇɴᴛ ᴘɪɴ\n"
    "  <code>-pinloud</code>  — ᴘɪɴ ᴡɪᴛʜ ɴᴏᴛɪꜰɪᴄᴀᴛɪᴏɴ\n"
    "  <code>-user</code>     — ꜱᴇɴᴅ ᴛᴏ ᴜꜱᴇʀꜱ ᴛᴏᴏ\n"
    "  <code>-nf</code>       — ʀᴇᴍᴏᴠᴇ ꜰᴏʀᴡᴀʀᴅ ᴛᴀɢ\n"
    "  (ᴘʀᴇᴍɪᴜᴍ ᴇᴍᴏᴊɪ ᴀʟᴡᴀʏꜱ ᴘʀᴇꜱᴇʀᴠᴇᴅ)"
    "</blockquote>"
)

_FLAGS = ["-pin", "-pinloud", "-user", "-nf", "-noforward"]


async def _deliver(chat_id, from_chat, msg_id, no_fwd, text=None):
    if text is not None:
        return await app.send_message(chat_id, text=text)
    if no_fwd:
        return await app.copy_message(
            chat_id=chat_id, from_chat_id=from_chat, message_id=msg_id
        )
    return await app.forward_messages(
        chat_id=chat_id, from_chat_id=from_chat, message_ids=msg_id
    )


async def _do_broadcast(message: Message):
    no_fwd = any(f in message.text for f in ["-nf", "-noforward"])
    do_pin = "-pin" in message.text and "-pinloud" not in message.text
    do_pinloud = "-pinloud" in message.text
    do_user = "-user" in message.text

    text_msg = from_chat = msg_id = None

    if message.reply_to_message:
        from_chat = message.chat.id
        msg_id = message.reply_to_message.id
    else:
        if len(message.command) < 2:
            return await message.reply_text(_USAGE)
        q = message.text.split(None, 1)[1]
        for f in _FLAGS:
            q = q.replace(f, "")
        q = q.strip()
        if not q:
            return await message.reply_text(_USAGE)
        text_msg = q

    nf_badge = " <code>[ɴᴏ-ꜰᴡᴅ]</code>" if no_fwd else ""
    await message.reply_text(
        f"{_BRAND}\n\n"
        f"<blockquote><emoji id='5041975203853239332'>🎁</emoji> "
        f"<b>ʙʀᴏᴀᴅᴄᴀꜱᴛɪɴɢ...{nf_badge}</b></blockquote>"
    )

    sent = pin = 0
    chats = [int(c["chat_id"]) for c in await get_served_chats()]

    for cid in chats:
        try:
            m = await _deliver(cid, from_chat, msg_id, no_fwd, text_msg)
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
            if fw.value > 200:
                continue
            await asyncio.sleep(fw.value)
        except Exception:
            continue

    _close_btn = InlineKeyboardMarkup([[
        InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close"),
    ]])

    await message.reply_text(
        f"{_BRAND}\n\n"
        f"<blockquote>"
        f"<emoji id='5041975203853239332'>🎁</emoji> <b>ᴅᴏɴᴇ</b>\n\n"
        f"<emoji id='5972072533833289156'>🔹</emoji> "
        f"ꜱᴇɴᴛ ᴛᴏ <code>{sent}</code> ɢʀᴏᴜᴘꜱ · <code>{pin}</code> ᴘɪɴꜱ"
        f"</blockquote>",
        reply_markup=_close_btn,
    )

    if do_user:
        susr = 0
        users = [int(u["user_id"]) for u in await get_served_users()]
        for uid in users:
            try:
                await _deliver(uid, from_chat, msg_id, no_fwd, text_msg)
                susr += 1
                await asyncio.sleep(0.2)
            except FloodWait as fw:
                if fw.value > 200:
                    continue
                await asyncio.sleep(fw.value)
            except Exception:
                continue

        await message.reply_text(
            f"{_BRAND}\n\n"
            f"<blockquote>"
            f"<emoji id='5041975203853239332'>🎁</emoji> <b>ᴜꜱᴇʀ ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴅᴏɴᴇ</b>\n\n"
            f"<emoji id='5972072533833289156'>🔹</emoji> "
            f"ꜱᴇɴᴛ ᴛᴏ <code>{susr}</code> ᴜꜱᴇʀꜱ"
            f"</blockquote>",
            reply_markup=_close_btn,
        )


@app.on_message(
    filters.command(["broadcast", "bc"], prefixes=["/", "!", "."]) & filters.user(OWNER_ID)
)
async def broadcast_cmd(_, message: Message):
    await _do_broadcast(message)


async def _refresh_adminlist():
    await asyncio.sleep(30)
    while True:
        try:
            for chat_id in await get_active_chats():
                if chat_id not in adminlist:
                    adminlist[chat_id] = []
                    async for m in app.get_chat_members(
                        chat_id, filter=ChatMembersFilter.ADMINISTRATORS
                    ):
                        if getattr(m.privileges, "can_manage_video_chats", False):
                            adminlist[chat_id].append(m.user.id)
                    for u in await get_authuser_names(chat_id):
                        adminlist[chat_id].append(await alpha_to_int(u))
        except Exception:
            pass
        await asyncio.sleep(10)
