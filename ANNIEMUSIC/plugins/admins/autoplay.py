import random
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup

from ANNIEMUSIC import app
from ANNIEMUSIC.utils.database import autoplay_off, autoplay_on, is_autoplay
from ANNIEMUSIC.utils.decorators import AdminRightsCheck
from ANNIEMUSIC.utils.inline import close_markup, InlineKeyboardButton
from config import BANNED_USERS

E1 = "<emoji id='5210820276748566172'>🔤</emoji>"
E2 = "<emoji id='5213301251722203632'>🔤</emoji>"
E3 = "<emoji id='5211032856154885824'>🔤</emoji>"
E4 = "<emoji id='5213337333742454261'>🔤</emoji>"

EMOJIS_ROW = f"{E1}{E2}{E3}{E4}{E2}"

BANNER = (
    f"<b>{EMOJIS_ROW}</b>\n"
    f"<b>━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
    f"<b>      ˹ ᴀɴɴɪᴇ ✘ ᴀᴜᴛᴏᴘʟᴀʏ ˼</b>\n"
    f"<b>━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
)


def autoplay_markup(_, enabled: bool):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=f"{E2} ᴇɴᴀʙʟᴇ ✅" if enabled else f"{E2} ᴇɴᴀʙʟᴇ",
                callback_data="AUTOPLAY_TOGGLE_ON",
                style="success" if enabled else "primary",
            ),
            InlineKeyboardButton(
                text=f"{E4} ᴅɪsᴀʙʟᴇ" if enabled else f"{E4} ᴅɪsᴀʙʟᴇ ✅",
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

    if enabled:
        status_line = f"{E2} <b>sᴛᴀᴛᴜs :</b> <b>ᴇɴᴀʙʟᴇᴅ ✅</b>"
    else:
        status_line = f"{E4} <b>sᴛᴀᴛᴜs :</b> <b>ᴅɪsᴀʙʟᴇᴅ ❌</b>"

    text = (
        f"{BANNER}"
        f"{status_line}\n\n"
        f"<blockquote>"
        f"{E3} <b>ᴡʜᴇɴ ᴇɴᴀʙʟᴇᴅ, ᴀɴɴɪᴇ ᴡɪʟʟ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴘʟᴀʏ\n"
        f"   ᴀ ɴᴇᴡ sᴏɴɢ ᴡʜᴇɴ ǫᴜᴇᴜᴇ ʙᴇᴄᴏᴍᴇs ᴇᴍᴘᴛʏ.\n\n"
        f"{E1} <b>ᴄᴏᴍᴍᴀɴᴅs :</b>\n"
        f"  • <code>/autoplay on</code>  —  ᴇɴᴀʙʟᴇ\n"
        f"  • <code>/autoplay off</code>  —  ᴅɪsᴀʙʟᴇ"
        f"</blockquote>"
    )

    if len(message.command) == 2:
        arg = message.command[1].lower()
        if arg == "on":
            if enabled:
                return await message.reply_text(
                    f"{BANNER}"
                    f"<blockquote>"
                    f"{E2} <b>ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴇɴᴀʙʟᴇᴅ ✅</b>"
                    f"</blockquote>"
                )
            await autoplay_on(chat_id)
            return await message.reply_text(
                f"{BANNER}"
                f"<blockquote>"
                f"{E2} <b>ᴀᴜᴛᴏᴘʟᴀʏ ᴇɴᴀʙʟᴇᴅ ✅</b>\n\n"
                f"{E3} <b>ᴀɴɴɪᴇ ᴡɪʟʟ ᴀᴜᴛᴏ-ᴘʟᴀʏ ʀᴇʟᴀᴛᴇᴅ sᴏɴɢs !</b>"
                f"</blockquote>",
                reply_markup=close_markup(_),
            )
        elif arg == "off":
            if not enabled:
                return await message.reply_text(
                    f"{BANNER}"
                    f"<blockquote>"
                    f"{E4} <b>ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴅɪsᴀʙʟᴇᴅ ❌</b>"
                    f"</blockquote>"
                )
            await autoplay_off(chat_id)
            return await message.reply_text(
                f"{BANNER}"
                f"<blockquote>"
                f"{E4} <b>ᴀᴜᴛᴏᴘʟᴀʏ ᴅɪsᴀʙʟᴇᴅ ❌</b>\n\n"
                f"{E3} <b>ᴀɴɴɪᴇ ᴡɪʟʟ sᴛᴏᴘ ᴀғᴛᴇʀ ᴄᴜʀʀᴇɴᴛ ǫᴜᴇᴜᴇ ᴇɴᴅs.</b>"
                f"</blockquote>",
                reply_markup=close_markup(_),
            )
        else:
            return await message.reply_text(
                f"{BANNER}"
                f"<blockquote>"
                f"{E1} <b>ᴜsᴀɢᴇ :</b> "
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
