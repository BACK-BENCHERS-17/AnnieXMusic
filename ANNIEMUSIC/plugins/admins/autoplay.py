from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup

from ANNIEMUSIC import app
from ANNIEMUSIC.utils.database import autoplay_off, autoplay_on, is_autoplay
from ANNIEMUSIC.utils.decorators import AdminRightsCheck
from ANNIEMUSIC.utils.inline import close_markup, InlineKeyboardButton
from config import BANNED_USERS

E_MUSIC  = "<emoji id='5463107823946717464'>🎵</emoji>"
E_SPARK  = "<emoji id='5039827436737397847'>✨</emoji>"
E_ZAP    = "<emoji id='5042334757040423886'>⚡️</emoji>"
E_CROSS  = "<emoji id='5040042498634810056'>❌</emoji>"
E_NOTE   = "<emoji id='5039771357349413873'>🎶</emoji>"
E_CLOCK  = "<emoji id='5123230779593196220'>⏰</emoji>"
E_REPEAT = "<emoji id='6030657343744644592'>🔁</emoji>"
E_STAR   = "<emoji id='5042200814190330758'>💫</emoji>"

BANNER = (
    f"{E_MUSIC}\n\n"
    f"<b>ᴀᴜᴛᴏᴘʟᴀʏ</b>\n\n"
)


def autoplay_markup(_, enabled: bool):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=f"{E_ZAP} ᴏɴ ✅" if enabled else f"{E_ZAP} ᴏɴ",
                callback_data="AUTOPLAY_TOGGLE_ON",
                style="success" if enabled else "primary",
            ),
            InlineKeyboardButton(
                text=f"{E_CROSS} ᴏғғ" if enabled else f"{E_CROSS} ᴏғғ ✅",
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

    status = (
        f"{E_ZAP} <b>ᴀᴜᴛᴏᴘʟᴀʏ :</b> <b>ᴇɴᴀʙʟᴇᴅ ✅</b>"
        if enabled else
        f"{E_CROSS} <b>ᴀᴜᴛᴏᴘʟᴀʏ :</b> <b>ᴅɪsᴀʙʟᴇᴅ</b>"
    )

    text = (
        f"{BANNER}"
        f"{status}\n"
        f"<b>┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄</b>\n\n"
        f"<blockquote>"
        f"{E_NOTE} <b>ᴡʜᴇɴ ᴇɴᴀʙʟᴇᴅ, ᴀɴɴɪᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴘʟᴀʏs\n"
        f"ᴀ ʀᴇʟᴀᴛᴇᴅ sᴏɴɢ ᴡʜᴇɴ ǫᴜᴇᴜᴇ ɪs ᴇᴍᴘᴛʏ.</b>\n\n"
        f"{E_SPARK} <b>ᴜsᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴏʀ:</b>\n"
        f"  <code>/autoplay on</code>  —  ᴇɴᴀʙʟᴇ\n"
        f"  <code>/autoplay off</code>  —  ᴅɪsᴀʙʟᴇ"
        f"</blockquote>"
    )

    if len(message.command) == 2:
        arg = message.command[1].lower()
        if arg == "on":
            if enabled:
                return await message.reply_text(
                    f"{BANNER}"
                    f"<blockquote>"
                    f"{E_ZAP} <b>ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴇɴᴀʙʟᴇᴅ ✅</b>"
                    f"</blockquote>"
                )
            await autoplay_on(chat_id)
            return await message.reply_text(
                f"{BANNER}"
                f"<blockquote>"
                f"{E_ZAP} <b>ᴀᴜᴛᴏᴘʟᴀʏ ᴇɴᴀʙʟᴇᴅ ✅</b>\n\n"
                f"{E_REPEAT} <b>ᴀɴɴɪᴇ ᴡɪʟʟ ᴀᴜᴛᴏ-ᴘʟᴀʏ ʀᴇʟᴀᴛᴇᴅ sᴏɴɢs!</b>"
                f"</blockquote>",
                reply_markup=close_markup(_),
            )
        elif arg == "off":
            if not enabled:
                return await message.reply_text(
                    f"{BANNER}"
                    f"<blockquote>"
                    f"{E_CROSS} <b>ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴅɪsᴀʙʟᴇᴅ</b>"
                    f"</blockquote>"
                )
            await autoplay_off(chat_id)
            return await message.reply_text(
                f"{BANNER}"
                f"<blockquote>"
                f"{E_CROSS} <b>ᴀᴜᴛᴏᴘʟᴀʏ ᴅɪsᴀʙʟᴇᴅ ❌</b>\n\n"
                f"{E_NOTE} <b>ᴀɴɴɪᴇ ᴡɪʟʟ sᴛᴏᴘ ᴀғᴛᴇʀ ǫᴜᴇᴜᴇ ᴇɴᴅs.</b>"
                f"</blockquote>",
                reply_markup=close_markup(_),
            )
        else:
            return await message.reply_text(
                f"{BANNER}"
                f"<blockquote>"
                f"{E_SPARK} <b>ᴜsᴀɢᴇ:</b> "
                f"<code>/autoplay on</code> ᴏʀ <code>/autoplay off</code>"
                f"</blockquote>"
            )

    await message.reply_text(text, reply_markup=autoplay_markup(_, enabled))


@app.on_callback_query(filters.regex("^AUTOPLAY_TOGGLE_") & ~BANNED_USERS)
async def autoplay_toggle_cb(client, callback):
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
