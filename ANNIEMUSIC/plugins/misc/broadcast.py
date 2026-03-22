import asyncio
import logging

from pyrogram import filters
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import FloodWait

from ANNIEMUSIC import app
from ANNIEMUSIC.misc import SUDOERS
from ANNIEMUSIC.utils.database import (
    get_active_chats,
    get_authuser_names,
    get_client,
    get_served_chats,
    get_served_users,
)
from ANNIEMUSIC.utils.decorators.language import language
from ANNIEMUSIC.utils.formatters import alpha_to_int
from config import OWNER_ID, adminlist

logger = logging.getLogger(__name__)

IS_BROADCASTING = False
_BROADCAST_ENABLED = False


async def _do_broadcast(client, message, _):
    global IS_BROADCASTING

    if message.reply_to_message:
        x = message.reply_to_message.id
        y = message.chat.id
    else:
        if len(message.command) < 2:
            return await message.reply_text(_["broad_2"])
        query = message.text.split(None, 1)[1]
        for flag in ["-pin", "-nobot", "-pinloud", "-assistant", "-user"]:
            query = query.replace(flag, "")
        if query.strip() == "":
            return await message.reply_text(_["broad_8"])

    IS_BROADCASTING = True
    await message.reply_text(_["broad_1"])

    if "-nobot" not in message.text:
        sent = 0
        pin = 0
        chats = []
        schats = await get_served_chats()
        for chat in schats:
            chats.append(int(chat["chat_id"]))
        for i in chats:
            try:
                m = (
                    await app.forward_messages(i, y, x)
                    if message.reply_to_message
                    else await app.send_message(i, text=query)
                )
                if "-pin" in message.text:
                    try:
                        await m.pin(disable_notification=True)
                        pin += 1
                    except Exception:
                        continue
                elif "-pinloud" in message.text:
                    try:
                        await m.pin(disable_notification=False)
                        pin += 1
                    except Exception:
                        continue
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
            await message.reply_text(_["broad_3"].format(sent, pin))
        except Exception:
            pass

    if "-user" in message.text:
        susr = 0
        served_users = []
        susers = await get_served_users()
        for user in susers:
            served_users.append(int(user["user_id"]))
        for i in served_users:
            try:
                m = (
                    await app.forward_messages(i, y, x)
                    if message.reply_to_message
                    else await app.send_message(i, text=query)
                )
                susr += 1
                await asyncio.sleep(0.2)
            except FloodWait as fw:
                flood_time = int(fw.value)
                if flood_time > 200:
                    continue
                await asyncio.sleep(flood_time)
            except Exception:
                pass
        try:
            await message.reply_text(_["broad_4"].format(susr))
        except Exception:
            pass

    if "-assistant" in message.text:
        aw = await message.reply_text(_["broad_5"])
        text = _["broad_6"]
        from ANNIEMUSIC.core.userbot import assistants

        for num in assistants:
            sent = 0
            cl = await get_client(num)
            async for dialog in cl.get_dialogs():
                try:
                    await cl.forward_messages(
                        dialog.chat.id, y, x
                    ) if message.reply_to_message else await cl.send_message(
                        dialog.chat.id, text=query
                    )
                    sent += 1
                    await asyncio.sleep(3)
                except FloodWait as fw:
                    flood_time = int(fw.value)
                    if flood_time > 200:
                        continue
                    await asyncio.sleep(flood_time)
                except Exception:
                    continue
            text += _["broad_7"].format(num, sent)
        try:
            await aw.edit_text(text)
        except Exception:
            pass

    IS_BROADCASTING = False


# ─────────────────────────────────────────────────────────────────────────────
# /br — NO decorator, raw handler, owner check inside
# ─────────────────────────────────────────────────────────────────────────────
@app.on_message(filters.command("br"))
async def br_command(client, message):
    global _BROADCAST_ENABLED

    # Ignore anyone who isn't the owner
    if not message.from_user or message.from_user.id != OWNER_ID:
        return

    args = message.command
    sub = args[1].lower() if len(args) > 1 else ""

    logger.info(f"[BR] sub='{sub}' enabled={_BROADCAST_ENABLED}")

    # ── Toggle ON ────────────────────────────────────────────────────────
    if sub == "on":
        _BROADCAST_ENABLED = True
        logger.info("[BR] Broadcast ENABLED")
        try:
            await message.delete()
        except Exception:
            pass
        return

    # ── Toggle OFF ───────────────────────────────────────────────────────
    if sub == "off":
        _BROADCAST_ENABLED = False
        logger.info("[BR] Broadcast DISABLED")
        try:
            await message.delete()
        except Exception:
            pass
        return

    # ── Broadcast locked — silently delete and ignore ────────────────────
    if not _BROADCAST_ENABLED:
        logger.info("[BR] Blocked — broadcast not enabled")
        try:
            await message.delete()
        except Exception:
            pass
        return

    # ── Do broadcast (needs language strings) ───────────────────────────
    from strings import get_string
    from ANNIEMUSIC.utils.database import get_lang
    try:
        lang_code = await get_lang(message.chat.id)
        _ = get_string(lang_code)
    except Exception:
        _ = get_string("en")

    await _do_broadcast(client, message, _)


# ─────────────────────────────────────────────────────────────────────────────
# /broadcast — owner only via SUDOERS, requires toggle ON
# ─────────────────────────────────────────────────────────────────────────────
@app.on_message(filters.command("broadcast") & SUDOERS)
@language
async def broadcast_message(client, message, _):
    if not message.from_user or message.from_user.id != OWNER_ID:
        return

    if not _BROADCAST_ENABLED:
        try:
            await message.delete()
        except Exception:
            pass
        return

    await _do_broadcast(client, message, _)


# ─────────────────────────────────────────────────────────────────────────────
# Admin list auto-refresh
# ─────────────────────────────────────────────────────────────────────────────
async def auto_clean():
    while not await asyncio.sleep(10):
        try:
            served_chats = await get_active_chats()
            for chat_id in served_chats:
                if chat_id not in adminlist:
                    adminlist[chat_id] = []
                    async for user in app.get_chat_members(
                        chat_id, filter=ChatMembersFilter.ADMINISTRATORS
                    ):
                        if getattr(user.privileges, 'can_manage_video_chats', False):
                            adminlist[chat_id].append(user.user.id)
                    authusers = await get_authuser_names(chat_id)
                    for user in authusers:
                        user_id = await alpha_to_int(user)
                        adminlist[chat_id].append(user_id)
        except Exception:
            continue


asyncio.create_task(auto_clean())
