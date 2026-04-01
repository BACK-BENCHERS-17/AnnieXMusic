"""KHUSHI — Autoplay: /autoplay, /ap"""

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, Message

from KHUSHI import app
from KHUSHI.utils.database import autoplay_off, autoplay_on, is_autoplay
from KHUSHI.utils.decorators import AdminRightsCheck
from KHUSHI.utils.inline import close_markup, InlineKeyboardButton
from config import BANNED_USERS

E_BEAR = "<emoji id='5042192219960771668'>🧸</emoji>"
E_TIME = "<emoji id='4979027931234830344'>⏳</emoji>"
E_DOT  = "<emoji id='5972072533833289156'>🔹</emoji>"

ANNIE_ROW = (
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
)


def _autoplay_text(enabled: bool) -> str:
    status = "ᴇɴᴀʙʟᴇᴅ ✅" if enabled else "ᴅɪsᴀʙʟᴇᴅ ❌"
    return (
        f"<blockquote>"
        f"┌────── ˹ ᴀᴜᴛᴏᴘʟᴀʏ ˼─── ⏤‌‌●\n"
        f"┆{E_BEAR} <b>Status:</b> <b>{status}</b>\n"
        f"┆{E_TIME} <b>Automatically plays a related song when the queue ends</b> — "
        f"so the music never stops even after the last track.\n"
        f"└──────────────────────●"
        f"</blockquote>\n"
        f"<blockquote>{ANNIE_ROW}</blockquote>"
    )


def autoplay_markup(_, enabled: bool):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text="✅ ᴏɴ" if enabled else "ᴏɴ",
                callback_data="AUTOPLAY_TOGGLE_ON",
                style="success" if enabled else "primary",
            ),
        ],
        [
            InlineKeyboardButton(
                text="ᴏꜰꜰ" if enabled else "❌ ᴏꜰꜰ",
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

    if len(message.command) == 2:
        arg = message.command[1].lower()
        if arg == "on":
            if enabled:
                return await message.reply_text(
                    f"<blockquote>┌────── ˹ ᴀᴜᴛᴏᴘʟᴀʏ ˼─── ⏤‌‌●\n"
                    f"┆{E_BEAR} <b>ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴇɴᴀʙʟᴇᴅ ✅</b>\n"
                    f"└──────────────────────●</blockquote>\n"
                    f"<blockquote>{ANNIE_ROW}</blockquote>"
                )
            await autoplay_on(chat_id)
            return await message.reply_text(
                f"<blockquote>┌────── ˹ ᴀᴜᴛᴏᴘʟᴀʏ ˼─── ⏤‌‌●\n"
                f"┆{E_BEAR} <b>ᴀᴜᴛᴏᴘʟᴀʏ ᴇɴᴀʙʟᴇᴅ ✅</b>\n"
                f"┆{E_TIME} <b>ᴡɪʟʟ ᴀᴜᴛᴏ-ᴘʟᴀʏ ʀᴇʟᴀᴛᴇᴅ sᴏɴɢs!</b>\n"
                f"└──────────────────────●</blockquote>\n"
                f"<blockquote>{ANNIE_ROW}</blockquote>",
                reply_markup=close_markup(_),
            )
        elif arg == "off":
            if not enabled:
                return await message.reply_text(
                    f"<blockquote>┌────── ˹ ᴀᴜᴛᴏᴘʟᴀʏ ˼─── ⏤‌‌●\n"
                    f"┆{E_BEAR} <b>ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴅɪsᴀʙʟᴇᴅ ❌</b>\n"
                    f"└──────────────────────●</blockquote>\n"
                    f"<blockquote>{ANNIE_ROW}</blockquote>"
                )
            await autoplay_off(chat_id)
            return await message.reply_text(
                f"<blockquote>┌────── ˹ ᴀᴜᴛᴏᴘʟᴀʏ ˼─── ⏤‌‌●\n"
                f"┆{E_BEAR} <b>ᴀᴜᴛᴏᴘʟᴀʏ ᴅɪsᴀʙʟᴇᴅ ❌</b>\n"
                f"┆{E_TIME} <b>ᴡɪʟʟ sᴛᴏᴘ ᴀꜰᴛᴇʀ ᴄᴜʀʀᴇɴᴛ ǫᴜᴇᴜᴇ ᴇɴᴅs.</b>\n"
                f"└──────────────────────●</blockquote>\n"
                f"<blockquote>{ANNIE_ROW}</blockquote>",
                reply_markup=close_markup(_),
            )
        else:
            return await message.reply_text(
                f"<blockquote>┌────── ˹ ᴀᴜᴛᴏᴘʟᴀʏ ˼─── ⏤‌‌●\n"
                f"┆{E_DOT} <b>ᴜsᴀɢᴇ:</b> <code>/autoplay on</code> ᴏʀ <code>/autoplay off</code>\n"
                f"└──────────────────────●</blockquote>\n"
                f"<blockquote>{ANNIE_ROW}</blockquote>"
            )

    await message.reply_text(_autoplay_text(enabled), reply_markup=autoplay_markup(_, enabled))


@app.on_callback_query(filters.regex("^AUTOPLAY_TOGGLE_") & ~BANNED_USERS)
async def autoplay_toggle_cb(client, callback):
    from strings import get_string
    from KHUSHI.utils.database import get_lang
    from KHUSHI.misc import SUDOERS
    from KHUSHI.utils.database import is_nonadmin_chat
    from config import adminlist

    chat_id = callback.message.chat.id
    user = callback.from_user

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
            return await callback.answer("ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴏɴ ✅", show_alert=True)
        await autoplay_on(chat_id)
        await callback.answer("✅ ᴀᴜᴛᴏᴘʟᴀʏ ᴇɴᴀʙʟᴇᴅ!")
    else:
        if not enabled:
            return await callback.answer("ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴏꜰꜰ ❌", show_alert=True)
        await autoplay_off(chat_id)
        await callback.answer("❌ ᴀᴜᴛᴏᴘʟᴀʏ ᴅɪsᴀʙʟᴇᴅ!")

    new_enabled = await is_autoplay(chat_id)
    try:
        await callback.message.edit_text(
            text=_autoplay_text(new_enabled),
            reply_markup=autoplay_markup(_, new_enabled),
        )
    except Exception:
        try:
            await callback.message.edit_reply_markup(reply_markup=autoplay_markup(_, new_enabled))
        except Exception:
            pass
