from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup

from ANNIEMUSIC import app
from ANNIEMUSIC.utils.database import autoplay_off, autoplay_on, is_autoplay
from ANNIEMUSIC.utils.decorators import AdminRightsCheck
from ANNIEMUSIC.utils.inline import close_markup, InlineKeyboardButton
from config import BANNED_USERS

# Same emojis as stream_1 in en.yml
E_BEAR  = "<emoji id='5042192219960771668'>🧸</emoji>"
E_TIME  = "<emoji id='4979027931234830344'>⏳</emoji>"
E_DOT   = "<emoji id='5972072533833289156'>🔹</emoji>"

ANNIE_ROW = (
    f"<emoji id='5042192219960771668'>🧸</emoji>"
    f"<emoji id='5210820276748566172'>🔤</emoji>"
    f"<emoji id='5213301251722203632'>🔤</emoji>"
    f"<emoji id='5213301251722203632'>🔤</emoji>"
    f"<emoji id='5211032856154885824'>🔤</emoji>"
    f"<emoji id='5213337333742454261'>🔤</emoji>"
)


def autoplay_markup(_, enabled: bool):
    bar_on  = "▰▰▰▰▰▰▱▱▱▱▱"
    bar_off = "▱▱▱▱▱▰▰▰▰▰▰"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=f"✅ ᴏɴ  {bar_on}" if enabled else f"ᴏɴ  {bar_on}",
                callback_data="AUTOPLAY_TOGGLE_ON",
                style="success" if enabled else "primary",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"ᴏꜰꜰ  {bar_off}" if enabled else f"❌ ᴏꜰꜰ  {bar_off}",
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

    status = "ᴇɴᴀʙʟᴇᴅ ✅" if enabled else "ᴅɪsᴀʙʟᴇᴅ ❌"

    text = (
        f"<blockquote>"
        f"┌────── ˹ ᴀᴜᴛᴏᴘʟᴀʏ ˼─── ⏤‌‌●\n"
        f"┆{E_BEAR} <b>sᴛᴀᴛᴜs :</b> <b>{status}</b>\n"
        f"┆{E_TIME} <b>ᴀɴɴɪᴇ ᴀᴜᴛᴏ-ᴘʟᴀʏs ᴀ ɴᴇᴡ sᴏɴɢ ᴡʜᴇɴ ǫᴜᴇᴜᴇ ɪs ᴇᴍᴘᴛʏ</b>\n"
        f"┆{E_DOT} <code>/autoplay on</code>  ᴏʀ  <code>/autoplay off</code>\n"
        f"└──────────────────────●"
        f"</blockquote>\n"
        f"<blockquote>{ANNIE_ROW}</blockquote>"
    )

    if len(message.command) == 2:
        arg = message.command[1].lower()
        if arg == "on":
            if enabled:
                return await message.reply_text(
                    f"<blockquote>"
                    f"┌────── ˹ ᴀᴜᴛᴏᴘʟᴀʏ ˼─── ⏤‌‌●\n"
                    f"┆{E_BEAR} <b>ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴇɴᴀʙʟᴇᴅ ✅</b>\n"
                    f"└──────────────────────●"
                    f"</blockquote>\n"
                    f"<blockquote>{ANNIE_ROW}</blockquote>"
                )
            await autoplay_on(chat_id)
            return await message.reply_text(
                f"<blockquote>"
                f"┌────── ˹ ᴀᴜᴛᴏᴘʟᴀʏ ˼─── ⏤‌‌●\n"
                f"┆{E_BEAR} <b>ᴀᴜᴛᴏᴘʟᴀʏ ᴇɴᴀʙʟᴇᴅ ✅</b>\n"
                f"┆{E_TIME} <b>ᴀɴɴɪᴇ ᴡɪʟʟ ᴀᴜᴛᴏ-ᴘʟᴀʏ ʀᴇʟᴀᴛᴇᴅ sᴏɴɢs !</b>\n"
                f"└──────────────────────●"
                f"</blockquote>\n"
                f"<blockquote>{ANNIE_ROW}</blockquote>",
                reply_markup=close_markup(_),
            )
        elif arg == "off":
            if not enabled:
                return await message.reply_text(
                    f"<blockquote>"
                    f"┌────── ˹ ᴀᴜᴛᴏᴘʟᴀʏ ˼─── ⏤‌‌●\n"
                    f"┆{E_BEAR} <b>ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴅɪsᴀʙʟᴇᴅ ❌</b>\n"
                    f"└──────────────────────●"
                    f"</blockquote>\n"
                    f"<blockquote>{ANNIE_ROW}</blockquote>"
                )
            await autoplay_off(chat_id)
            return await message.reply_text(
                f"<blockquote>"
                f"┌────── ˹ ᴀᴜᴛᴏᴘʟᴀʏ ˼─── ⏤‌‌●\n"
                f"┆{E_BEAR} <b>ᴀᴜᴛᴏᴘʟᴀʏ ᴅɪsᴀʙʟᴇᴅ ❌</b>\n"
                f"┆{E_TIME} <b>ᴀɴɴɪᴇ ᴡɪʟʟ sᴛᴏᴘ ᴀғᴛᴇʀ ᴄᴜʀʀᴇɴᴛ ǫᴜᴇᴜᴇ ᴇɴᴅs.</b>\n"
                f"└──────────────────────●"
                f"</blockquote>\n"
                f"<blockquote>{ANNIE_ROW}</blockquote>",
                reply_markup=close_markup(_),
            )
        else:
            return await message.reply_text(
                f"<blockquote>"
                f"┌────── ˹ ᴀᴜᴛᴏᴘʟᴀʏ ˼─── ⏤‌‌●\n"
                f"┆{E_DOT} <b>ᴜsᴀɢᴇ :</b> <code>/autoplay on</code> ᴏʀ <code>/autoplay off</code>\n"
                f"└──────────────────────●"
                f"</blockquote>\n"
                f"<blockquote>{ANNIE_ROW}</blockquote>"
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
