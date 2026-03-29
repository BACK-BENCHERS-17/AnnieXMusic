"""KHUSHI — Sudo Commands: gban, block, blchat, sudoers, maintenance."""

import asyncio

from pyrogram import filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message

from KHUSHI import app
from KHUSHI.misc import SUDOERS
from ANNIEMUSIC.utils.database import (
    add_banned_user,
    add_gban_user,
    get_banned_count,
    get_banned_users,
    get_served_chats,
    is_banned_user,
    is_maintenance,
    maintenance_off,
    maintenance_on,
    remove_banned_user,
    remove_gban_user,
)
from ANNIEMUSIC.utils.extraction import extract_user
from config import BANNED_USERS, OWNER_ID

_BRAND = (
    "<blockquote>"
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
    "</blockquote>"
)

_dot = "<emoji id='5972072533833289156'>🔹</emoji>"
_zap = "<emoji id='5042334757040423886'>⚡️</emoji>"


def _r(t):
    return f"{_BRAND}\n\n<blockquote>{t}</blockquote>"


# ── GBAN ──────────────────────────────────────────────────────────────────────
@app.on_message(filters.command(["gban", "globalban"]) & SUDOERS)
async def gban_user(_, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text(_r("ᴜꜱᴀɢᴇ: /gban [user | reply]"))
    user = await extract_user(message)
    if user.id in SUDOERS:
        return await message.reply_text(_r("❌ ᴄᴀɴɴᴏᴛ ɢʙᴀɴ ᴀ ꜱᴜᴅᴏᴇʀ."))
    if await is_banned_user(user.id):
        return await message.reply_text(_r(f"{user.mention} ɪꜱ ᴀʟʀᴇᴀᴅʏ ɢʙᴀɴɴᴇᴅ."))
    BANNED_USERS.add(user.id)
    chats = [int(c["chat_id"]) for c in await get_served_chats()]
    msg = await message.reply_text(_r(f"⏳ ɢʙᴀɴɴɪɴɢ {user.mention} ɪɴ {len(chats)} ɢʀᴏᴜᴘꜱ..."))
    banned = 0
    for cid in chats:
        try:
            await app.ban_chat_member(cid, user.id)
            banned += 1
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
        except Exception:
            continue
    await add_banned_user(user.id)
    await msg.edit(_r(
        f"🔨 <b>ɢʙᴀɴɴᴇᴅ</b> : {user.mention}\n"
        f"{_dot} ʙᴀɴɴᴇᴅ ɪɴ <code>{banned}</code> ɢʀᴏᴜᴘꜱ"
    ))


@app.on_message(filters.command(["ungban"]) & SUDOERS)
async def ungban_user(_, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text(_r("ᴜꜱᴀɢᴇ: /ungban [user | reply]"))
    user = await extract_user(message)
    if not await is_banned_user(user.id):
        return await message.reply_text(_r(f"{user.mention} ɪꜱ ɴᴏᴛ ɢʙᴀɴɴᴇᴅ."))
    BANNED_USERS.discard(user.id)
    await remove_banned_user(user.id)
    await message.reply_text(_r(f"✅ <b>ᴜɴɢʙᴀɴɴᴇᴅ</b> : {user.mention}"))


# ── BLOCK/UNBLOCK ─────────────────────────────────────────────────────────────
@app.on_message(filters.command(["block"]) & SUDOERS)
async def block_user(_, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text(_r("ᴜꜱᴀɢᴇ: /block [user | reply]"))
    user = await extract_user(message)
    if user.id in BANNED_USERS:
        return await message.reply_text(_r(f"{user.mention} ᴀʟʀᴇᴀᴅʏ ʙʟᴏᴄᴋᴇᴅ."))
    await add_gban_user(user.id)
    BANNED_USERS.add(user.id)
    await message.reply_text(_r(f"🚫 <b>ʙʟᴏᴄᴋᴇᴅ</b> : {user.mention}"))


@app.on_message(filters.command(["unblock"]) & SUDOERS)
async def unblock_user(_, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text(_r("ᴜꜱᴀɢᴇ: /unblock [user | reply]"))
    user = await extract_user(message)
    if user.id not in BANNED_USERS:
        return await message.reply_text(_r(f"{user.mention} ɪꜱ ɴᴏᴛ ʙʟᴏᴄᴋᴇᴅ."))
    await remove_gban_user(user.id)
    BANNED_USERS.discard(user.id)
    await message.reply_text(_r(f"✅ <b>ᴜɴʙʟᴏᴄᴋᴇᴅ</b> : {user.mention}"))


# ── MAINTENANCE ───────────────────────────────────────────────────────────────
@app.on_message(filters.command(["maintenance"]) & SUDOERS)
async def maint(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(_r("ᴜꜱᴀɢᴇ: /maintenance [enable | disable]"))
    state = message.command[1].lower()
    if state == "enable":
        if await is_maintenance():
            return await message.reply_text(_r("⚠️ ᴀʟʀᴇᴀᴅʏ ɪɴ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ."))
        await maintenance_on()
        await message.reply_text(_r(f"{_zap} <b>ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ ᴏɴ</b>\nᴏɴʟʏ ꜱᴜᴅᴏᴇʀꜱ ᴄᴀɴ ᴜꜱᴇ ᴛʜᴇ ʙᴏᴛ."))
    elif state == "disable":
        if not await is_maintenance():
            return await message.reply_text(_r("⚠️ ɴᴏᴛ ɪɴ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ."))
        await maintenance_off()
        await message.reply_text(_r(f"✅ <b>ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ ᴏꜰꜰ</b>\nʙᴏᴛ ɪꜱ ᴘᴜʙʟɪᴄ ᴀɢᴀɪɴ."))
    else:
        await message.reply_text(_r("ᴜꜱᴀɢᴇ: /maintenance [enable | disable]"))


# ── SUDOERS ───────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["addsudo"], prefixes=["/", "!", "."]) & filters.user(OWNER_ID)
)
async def add_sudo(_, message: Message):
    from ANNIEMUSIC.utils.database import add_sudo as _add
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text(_r("ᴜꜱᴀɢᴇ: /addsudo [user | reply]"))
    user = await extract_user(message)
    if user.id in SUDOERS:
        return await message.reply_text(_r(f"{user.mention} ɪꜱ ᴀʟʀᴇᴀᴅʏ ᴀ ꜱᴜᴅᴏᴇʀ."))
    await _add(user.id)
    SUDOERS.add(user.id)
    await message.reply_text(_r(f"✅ <b>ꜱᴜᴅᴏ ɢʀᴀɴᴛᴇᴅ</b> : {user.mention}"))


@app.on_message(
    filters.command(["delsudo", "rmsudo"], prefixes=["/", "!", "."]) & filters.user(OWNER_ID)
)
async def del_sudo(_, message: Message):
    from ANNIEMUSIC.utils.database import remove_sudo as _rm
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text(_r("ᴜꜱᴀɢᴇ: /delsudo [user | reply]"))
    user = await extract_user(message)
    if user.id not in SUDOERS:
        return await message.reply_text(_r(f"{user.mention} ɪꜱ ɴᴏᴛ ᴀ ꜱᴜᴅᴏᴇʀ."))
    await _rm(user.id)
    SUDOERS.discard(user.id)
    await message.reply_text(_r(f"✅ <b>ꜱᴜᴅᴏ ʀᴇᴠᴏᴋᴇᴅ</b> : {user.mention}"))
