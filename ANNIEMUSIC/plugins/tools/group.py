from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatType
from pyrogram.errors import ChatSendPlainForbidden, ChatWriteForbidden, Forbidden, ChannelPrivate

from ANNIEMUSIC import app
from config import OWNER_ID


async def _safe_reply_text(message: Message, *args, **kwargs):
    chat = getattr(message, "chat", None)
    if not chat or chat.type == ChatType.CHANNEL:
        return
    try:
        await message.reply_text(*args, **kwargs)
    except (ChatSendPlainForbidden, ChatWriteForbidden, Forbidden, ChannelPrivate):
        pass


@app.on_message(filters.video_chat_started & filters.group)
async def on_voice_chat_started(_, message: Message):
    await _safe_reply_text(message, "🎙 <b>ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ʜᴀs sᴛᴀʀᴛᴇᴅ!</b>")


@app.on_message(filters.video_chat_ended & filters.group)
async def on_voice_chat_ended(_, message: Message):
    await _safe_reply_text(message, "🔕 <b>ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ᴇɴᴅᴇᴅ.</b>")


@app.on_message(filters.video_chat_members_invited & filters.group)
async def on_voice_chat_members_invited(_, message: Message):
    inviter = "Someone"
    if message.from_user:
        try:
            inviter = message.from_user.mention(message.from_user.first_name)
        except Exception:
            inviter = message.from_user.first_name or "Someone"

    invited = []
    vcmi = getattr(message, "video_chat_members_invited", None)
    users = getattr(vcmi, "users", []) if vcmi else []
    for user in users:
        try:
            name = user.first_name or "User"
            invited.append(f"<a href=\"tg://user?id={user.id}\">{name}</a>")
        except Exception:
            continue

    if invited:
        await _safe_reply_text(
            message,
            f"👥 {inviter} ɪɴᴠɪᴛᴇᴅ {', '.join(invited)} ᴛᴏ ᴛʜᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ. 😉",
        )


@app.on_message(filters.command("leavegroup") & filters.user(OWNER_ID) & filters.group)
async def leave_group(_, message: Message):
    await _safe_reply_text(message, "👋 <b>ʟᴇᴀᴠɪɴɢ ᴛʜɪs ɢʀᴏᴜᴘ...</b>")
    try:
        await app.leave_chat(chat_id=message.chat.id, delete=True)
    except (ChatWriteForbidden, Forbidden, ChannelPrivate):
        pass