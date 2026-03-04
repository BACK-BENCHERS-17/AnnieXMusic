import asyncio
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import ChatJoinRequest
from pyrogram.errors import (
    ChatAdminRequired,
    UserAlreadyParticipant,
    UserNotParticipant,
    ChannelPrivate,
    FloodWait,
    PeerIdInvalid,
    ChatWriteForbidden,
)

from ANNIEMUSIC import app
from ANNIEMUSIC.utils.admin_filters import dev_filter, admin_filter, sudo_filter
from ANNIEMUSIC.utils.database import get_assistant


ACTIVE_STATUSES = {
    ChatMemberStatus.OWNER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.RESTRICTED,
}


async def _is_participant(client, chat_id, user_id) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ACTIVE_STATUSES
    except UserNotParticipant:
        return False
    except PeerIdInvalid:
        return False
    except Exception:
        return False


async def join_userbot(app, chat_id, chat_username=None):
    userbot = await get_assistant(chat_id)

    try:
        member = await app.get_chat_member(chat_id, userbot.id)
        if member.status == ChatMemberStatus.BANNED:
            try:
                await app.unban_chat_member(chat_id, userbot.id)
            except ChatAdminRequired:
                return "<b>❌ I need unban permission to add the assistant.</b>"
        if member.status in ACTIVE_STATUSES:
            return "<b>🤖 Assistant is already in the chat.</b>"
    except UserNotParticipant:
        pass
    except PeerIdInvalid:
        return "<b>❌ Invalid chat ID.</b>"

    invite = None
    if chat_username:
        invite = chat_username if chat_username.startswith("@") else f"@{chat_username}"
    else:
        try:
            link = await app.create_chat_invite_link(chat_id)
            invite = link.invite_link
        except ChatAdminRequired:
            return "<b>❌ I need permission to create invite links or a public @username to add the assistant.</b>"

    try:
        await userbot.join_chat(invite)
        return "<b>✅ Assistant joined successfully.</b>"
    except UserAlreadyParticipant:
        return "<b>🤖 Assistant is already a participant.</b>"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        try:
            await userbot.join_chat(invite)
            return "<b>✅ Assistant joined successfully.</b>"
        except UserAlreadyParticipant:
            return "<b>🤖 Assistant is already a participant.</b>"
        except Exception as ex:
            return f"<b>❌ Failed to add assistant after wait:</b> `{str(ex)}`"
    except Exception as e:
        if "USER_ALREADY_PARTICIPANT" in str(e):
            return "<b>🤖 Assistant is already a participant.</b>"
        return f"<b>❌ Failed to add assistant:</b> `{str(e)}`"


@app.on_chat_join_request()
async def approve_join_request(client, chat_join_request: ChatJoinRequest):
    userbot = await get_assistant(chat_join_request.chat.id)
    if chat_join_request.from_user.id != userbot.id:
        return
    chat_id = chat_join_request.chat.id

    try:
        if await _is_participant(client, chat_id, userbot.id):
            return
        try:
            await client.approve_chat_join_request(chat_id, userbot.id)
        except UserAlreadyParticipant:
            return
        except FloodWait as e:
            await asyncio.sleep(e.value)
            try:
                await client.approve_chat_join_request(chat_id, userbot.id)
            except UserAlreadyParticipant:
                return
        try:
            await client.send_message(chat_id, "<b>✅ Assistant has been approved and joined the chat.</b>")
        except ChatWriteForbidden:
            pass
    except ChatAdminRequired:
        return
    except PeerIdInvalid:
        return
    except Exception:
        return


@app.on_message(
    filters.command(["userbotjoin", "assistantjoin"], prefixes=[".", "/"])
    & (filters.group | filters.private)
    & admin_filter
    & sudo_filter
)
async def join_group(app, message):
    chat_id = message.chat.id
    status_message = await message.reply("<b>⏳ Please wait, inviting assistant...</b>")

    try:
        me = await app.get_me()
        chat_member = await app.get_chat_member(chat_id, me.id)
        if chat_member.status != ChatMemberStatus.ADMINISTRATOR:
            await status_message.edit_text("<b>❌ I need to be admin to invite the assistant.</b>")
            return
    except ChatAdminRequired:
        await status_message.edit_text("<b>❌ I don't have permission to check admin status in this chat.</b>")
        return
    except Exception as e:
        await status_message.edit_text(f"<b>❌ Failed to verify permissions:</b> `{str(e)}`")
        return

    chat_username = message.chat.username or None
    response = await join_userbot(app, chat_id, chat_username)
    try:
        await status_message.edit_text(response)
    except ChatWriteForbidden:
        pass


@app.on_message(
    filters.command("userbotleave", prefixes=[".", "/"])
    & filters.group
    & admin_filter
    & sudo_filter
)
async def leave_one(app, message):
    chat_id = message.chat.id
    try:
        userbot = await get_assistant(chat_id)
        try:
            member = await userbot.get_chat_member(chat_id, userbot.id)
        except UserNotParticipant:
            await message.reply("<b>🤖 Assistant is not currently in this chat.</b>")
            return

        if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            await message.reply("<b>🤖 Assistant is not currently in this chat.</b>")
            return

        await userbot.leave_chat(chat_id)
        try:
            await app.send_message(chat_id, "<b>✅ Assistant has left this chat.</b>")
        except ChatWriteForbidden:
            pass
    except ChannelPrivate:
        await message.reply("<b>❌ Error: This chat is not accessible or has been deleted.</b>")
    except UserNotParticipant:
        await message.reply("<b>🤖 Assistant is not in this chat.</b>")
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await message.reply("<b>✅ Retried after flood wait; try the command again if needed.</b>")
    except Exception as e:
        await message.reply(f"<b>❌ Failed to remove assistant:</b> `{str(e)}`")


@app.on_message(filters.command("leaveall", prefixes=["."]) & dev_filter)
async def leave_all(app, message):
    left = 0
    failed = 0
    status_message = await message.reply("🔄 <b>Assistant is leaving all chats...</b>")

    try:
        userbot = await get_assistant(message.chat.id)
        async for dialog in userbot.get_dialogs():
            if dialog.chat.id == -1002014167331:
                continue
            try:
                await userbot.leave_chat(dialog.chat.id)
                left += 1
            except FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await userbot.leave_chat(dialog.chat.id)
                    left += 1
                except Exception:
                    failed += 1
            except Exception:
                failed += 1

            try:
                await status_message.edit_text(
                    f"<b>Leaving chats...</b>\n✅ Left: `{left}`\n❌ Failed: `{failed}`"
                )
            except ChatWriteForbidden:
                pass
            await asyncio.sleep(1)
    except FloodWait as e:
        await asyncio.sleep(e.value)
    finally:
        try:
            await app.send_message(
                message.chat.id,
                f"<b>✅ Left from:</b> `{left}` chats.\n<b>❌ Failed in:</b> `{failed}` chats.",
            )
        except ChatWriteForbidden:
            pass