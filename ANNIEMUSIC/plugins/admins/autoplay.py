from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup

from ANNIEMUSIC import app
from ANNIEMUSIC.utils.database import autoplay_off, autoplay_on, is_autoplay
from ANNIEMUSIC.utils.decorators import AdminRightsCheck
from ANNIEMUSIC.utils.inline import close_markup, InlineKeyboardButton
from config import BANNED_USERS

BANNER = (
    "<emoji id='5296587316201005019'>💕</emoji>"
    "<emoji id='6095843123252957701'>⚡️</emoji>"
    " <b>ᴀɴɴɪᴇ ✘ ᴀᴜᴛᴏᴘʟᴀʏ</b> "
    "<emoji id='6095843123252957701'>⚡️</emoji>"
    "<emoji id='5296587316201005019'>💕</emoji>\n"
    "<b>▰▰▰▰▰▰▰▰▰▰▰▰▰</b>\n"
)


def autoplay_markup(_, enabled: bool):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=(
                    "<emoji id='6095843123252957701'>⚡️</emoji> ᴏɴ ✅"
                    if enabled else
                    "<emoji id='5361964771509808811'>🍷</emoji> ᴏɴ"
                ),
                callback_data="AUTOPLAY_TOGGLE_ON",
                style="success" if enabled else "primary",
            ),
            InlineKeyboardButton(
                text=(
                    "<emoji id='4956222745814762495'>❤️‍🔥</emoji> ᴏғғ"
                    if enabled else
                    "<emoji id='4956222745814762495'>❤️‍🔥</emoji> ᴏғғ ✅"
                ),
                callback_data="AUTOPLAY_TOGGLE_OFF",
                style="primary" if enabled else "danger",
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data="close",
                style="danger",
            )
        ],
    ])


@app.on_message(
    filters.command(["autoplay", "ap"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def autoplay_command(cli, message: Message, _, chat_id):
    enabled = await is_autoplay(chat_id)

    status_line = (
        "<emoji id='6095843123252957701'>⚡️</emoji> <b>ᴀᴜᴛᴏᴘʟᴀʏ :</b> "
        + ("<b>ᴇɴᴀʙʟᴇᴅ ✅</b>" if enabled else "<b>ᴅɪsᴀʙʟᴇᴅ ❌</b>")
    )

    text = (
        f"{BANNER}"
        f"{status_line}\n"
        f"<b>▰▰▰▰▰▰▰▰▰▰▰▰▰</b>\n\n"
        f"<emoji id='4958719848390591540'>🦋</emoji> <b>ᴡʜᴇɴ ᴇɴᴀʙʟᴇᴅ, ᴀɴɴɪᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ\n"
        f"ᴘʟᴀʏs ᴀ ʀᴇʟᴀᴛᴇᴅ sᴏɴɢ ᴡʜᴇɴ ǫᴜᴇᴜᴇ ɪs ᴇᴍᴘᴛʏ.</b>\n\n"
        f"<emoji id='5298709502491637271'>🌈</emoji> <b>ᴜsᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴏʀ:</b>\n"
        f"  <code>/autoplay on</code> — ᴇɴᴀʙʟᴇ\n"
        f"  <code>/autoplay off</code> — ᴅɪsᴀʙʟᴇ"
    )

    if len(message.command) == 2:
        arg = message.command[1].lower()
        if arg == "on":
            if enabled:
                return await message.reply_text(
                    f"{BANNER}"
                    f"<emoji id='6095843123252957701'>⚡️</emoji> <b>ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴇɴᴀʙʟᴇᴅ ✅</b>"
                )
            await autoplay_on(chat_id)
            return await message.reply_text(
                f"{BANNER}"
                f"<emoji id='6095843123252957701'>⚡️</emoji> <b>ᴀᴜᴛᴏᴘʟᴀʏ ᴇɴᴀʙʟᴇᴅ ✅</b>\n\n"
                f"<b>ᴀɴɴɪᴇ ᴡɪʟʟ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴘʟᴀʏ ʀᴇʟᴀᴛᴇᴅ sᴏɴɢs ⚡️</b>",
                reply_markup=close_markup(_),
            )
        elif arg == "off":
            if not enabled:
                return await message.reply_text(
                    f"{BANNER}"
                    f"<emoji id='4956222745814762495'>❤️‍🔥</emoji> <b>ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴅɪsᴀʙʟᴇᴅ ❌</b>"
                )
            await autoplay_off(chat_id)
            return await message.reply_text(
                f"{BANNER}"
                f"<emoji id='4956222745814762495'>❤️‍🔥</emoji> <b>ᴀᴜᴛᴏᴘʟᴀʏ ᴅɪsᴀʙʟᴇᴅ ❌</b>\n\n"
                f"<b>ᴀɴɴɪᴇ ᴡɪʟʟ sᴛᴏᴘ ᴀғᴛᴇʀ ǫᴜᴇᴜᴇ ᴇɴᴅs.</b>",
                reply_markup=close_markup(_),
            )
        else:
            return await message.reply_text(
                f"{BANNER}"
                f"<b>ᴜsᴀɢᴇ:</b> <code>/autoplay on</code> ᴏʀ <code>/autoplay off</code>"
            )

    await message.reply_text(text, reply_markup=autoplay_markup(_, enabled))


@app.on_callback_query(filters.regex("^AUTOPLAY_TOGGLE_") & ~BANNED_USERS)
async def autoplay_toggle_cb(client, callback):
    from ANNIEMUSIC.utils.decorators import languageCB
    from strings import get_string
    from ANNIEMUSIC.utils.database import get_lang

    chat_id = callback.message.chat.id
    user = callback.from_user

    from ANNIEMUSIC.misc import SUDOERS
    from ANNIEMUSIC.utils.database import is_nonadmin_chat
    from config import adminlist

    if not await is_nonadmin_chat(chat_id) and user.id not in SUDOERS:
        admins = adminlist.get(chat_id)
        if not admins or user.id not in admins:
            return await callback.answer(
                "ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴄʜᴀɴɢᴇ ᴀᴜᴛᴏᴘʟᴀʏ sᴇᴛᴛɪɴɢs!",
                show_alert=True,
            )

    lang = await get_lang(chat_id)
    _ = get_string(lang)

    action = callback.data.split("_")[-1]
    enabled = await is_autoplay(chat_id)

    if action == "ON":
        if enabled:
            await callback.answer("ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴏɴ ✅", show_alert=True)
            return
        await autoplay_on(chat_id)
        await callback.answer("✅ ᴀᴜᴛᴏᴘʟᴀʏ ᴇɴᴀʙʟᴇᴅ!")
    else:
        if not enabled:
            await callback.answer("ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴏғғ ❌", show_alert=True)
            return
        await autoplay_off(chat_id)
        await callback.answer("❌ ᴀᴜᴛᴏᴘʟᴀʏ ᴅɪsᴀʙʟᴇᴅ!")

    new_enabled = await is_autoplay(chat_id)
    try:
        await callback.message.edit_reply_markup(
            reply_markup=autoplay_markup(_, new_enabled)
        )
    except Exception:
        pass
