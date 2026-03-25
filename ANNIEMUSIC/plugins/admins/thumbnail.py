from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup

from ANNIEMUSIC import app
from ANNIEMUSIC.utils.database import is_thumb_enabled, thumb_on, thumb_off
from ANNIEMUSIC.utils.decorators import AdminRightsCheck
from ANNIEMUSIC.utils.inline import close_markup, InlineKeyboardButton
from config import BANNED_USERS

E_BEAR = "<emoji id='5042192219960771668'>🧸</emoji>"
E_CAM  = "<emoji id='5787544344906959608'>📸</emoji>"
E_VID  = "<emoji id='5373141891321699086'>🎬</emoji>"
E_DOT  = "<emoji id='5972072533833289156'>🔹</emoji>"

ANNIE_ROW = (
    f"<emoji id='5042192219960771668'>🧸</emoji>"
    f"<emoji id='5210820276748566172'>🔤</emoji>"
    f"<emoji id='5213301251722203632'>🔤</emoji>"
    f"<emoji id='5213301251722203632'>🔤</emoji>"
    f"<emoji id='5211032856154885824'>🔤</emoji>"
    f"<emoji id='5213337333742454261'>🔤</emoji>"
)

THUMB_VIDEO_URL = "https://files.catbox.moe/1ohavg.mp4"


def thumb_markup(_, enabled: bool):
    bar_on  = "▰▰▰▰▰▰▱▱▱▱▱"
    bar_off = "▱▱▱▱▱▰▰▰▰▰▰"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=f"✅ ᴛʜᴜᴍʙɴᴀɪʟ ᴏɴ  {bar_on}" if enabled else f"ᴛʜᴜᴍʙɴᴀɪʟ ᴏɴ  {bar_on}",
                callback_data="THUMB_TOGGLE_ON",
                style="success" if enabled else "primary",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ ᴏꜰꜰ  {bar_off}" if enabled else f"❌ ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ ᴏɴ  {bar_off}",
                callback_data="THUMB_TOGGLE_OFF",
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
    filters.command(["thumbnail", "thumb"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def thumbnail_command(cli, message: Message, _, chat_id):
    enabled = await is_thumb_enabled(chat_id)
    status = "ᴇɴᴀʙʟᴇᴅ ✅" if enabled else "ᴅɪsᴀʙʟᴇᴅ ❌ (ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ)"

    text = (
        f"<blockquote>"
        f"┌────── ˹ ᴛʜᴜᴍʙɴᴀɪʟ ˼─── ⏤‌‌●\n"
        f"┆{E_BEAR} <b>sᴛᴀᴛᴜs :</b> <b>{status}</b>\n"
        f"┆{E_CAM} <b>ᴏɴ</b>  → ɴᴏʀᴍᴀʟ ᴛʜᴜᴍʙɴᴀɪʟ ᴘʜᴏᴛᴏ\n"
        f"┆{E_VID} <b>ᴏꜰꜰ</b> → ᴠɪᴅᴇᴏ sᴇɴᴅ ʜᴏɢᴀ (ɢʀᴏᴜᴘ ᴘʀᴏᴛᴇᴄᴛ)\n"
        f"┆{E_DOT} <code>/thumbnail on</code>  ᴏʀ  <code>/thumbnail off</code>\n"
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
                    f"┌────── ˹ ᴛʜᴜᴍʙɴᴀɪʟ ˼─── ⏤‌‌●\n"
                    f"┆{E_CAM} <b>ᴛʜᴜᴍʙɴᴀɪʟ ɪs ᴀʟʀᴇᴀᴅʏ ᴇɴᴀʙʟᴇᴅ ✅</b>\n"
                    f"└──────────────────────●"
                    f"</blockquote>\n"
                    f"<blockquote>{ANNIE_ROW}</blockquote>"
                )
            await thumb_on(chat_id)
            return await message.reply_text(
                f"<blockquote>"
                f"┌────── ˹ ᴛʜᴜᴍʙɴᴀɪʟ ˼─── ⏤‌‌●\n"
                f"┆{E_CAM} <b>ᴛʜᴜᴍʙɴᴀɪʟ ᴇɴᴀʙʟᴇᴅ ✅</b>\n"
                f"┆{E_DOT} ᴀʙ ᴘʟᴀʏ ᴍᴇssᴀɢᴇ ᴍᴇɪɴ ᴛʜᴜᴍʙɴᴀɪʟ ᴅɪᴋʜᴇɢᴀ!\n"
                f"└──────────────────────●"
                f"</blockquote>\n"
                f"<blockquote>{ANNIE_ROW}</blockquote>",
                reply_markup=close_markup(_),
            )
        elif arg == "off":
            if not enabled:
                return await message.reply_text(
                    f"<blockquote>"
                    f"┌────── ˹ ᴛʜᴜᴍʙɴᴀɪʟ ˼─── ⏤‌‌●\n"
                    f"┆{E_VID} <b>ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ ᴘᴇʜʟᴇ sᴇ ᴀᴄᴛɪᴠᴇ ʜᴀɪ ❌</b>\n"
                    f"└──────────────────────●"
                    f"</blockquote>\n"
                    f"<blockquote>{ANNIE_ROW}</blockquote>"
                )
            await thumb_off(chat_id)
            return await message.reply_text(
                f"<blockquote>"
                f"┌────── ˹ ᴛʜᴜᴍʙɴᴀɪʟ ˼─── ⏤‌‌●\n"
                f"┆{E_VID} <b>ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ ᴀᴄᴛɪᴠᴇ ❌</b>\n"
                f"┆{E_DOT} ᴀʙ ᴘʟᴀʏ ᴍᴇssᴀɢᴇ ᴍᴇɪɴ ᴠɪᴅᴇᴏ ᴀᴀɪɢᴀ!\n"
                f"┆{E_DOT} ɢʀᴏᴜᴘ ꜰᴜʟʟ ᴘʀᴏᴛᴇᴄᴛ ʀᴀʜᴇɢᴀ 🔒\n"
                f"└──────────────────────●"
                f"</blockquote>\n"
                f"<blockquote>{ANNIE_ROW}</blockquote>",
                reply_markup=close_markup(_),
            )
        else:
            return await message.reply_text(
                f"<blockquote>"
                f"┌────── ˹ ᴛʜᴜᴍʙɴᴀɪʟ ˼─── ⏤‌‌●\n"
                f"┆{E_DOT} <b>ᴜsᴀɢᴇ :</b> <code>/thumbnail on</code> ᴏʀ <code>/thumbnail off</code>\n"
                f"└──────────────────────●"
                f"</blockquote>\n"
                f"<blockquote>{ANNIE_ROW}</blockquote>"
            )

    await message.reply_text(text, reply_markup=thumb_markup(_, enabled))


@app.on_callback_query(filters.regex("^THUMB_TOGGLE_") & ~BANNED_USERS)
async def thumb_toggle_cb(client, callback):
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
                "ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴄʜᴀɴɢᴇ ᴛʜᴜᴍʙɴᴀɪʟ sᴇᴛᴛɪɴɢs!",
                show_alert=True,
            )

    lang = await get_lang(chat_id)
    _ = get_string(lang)

    action = callback.data.split("_")[-1]
    enabled = await is_thumb_enabled(chat_id)

    if action == "ON":
        if enabled:
            await callback.answer("ᴛʜᴜᴍʙɴᴀɪʟ ɪs ᴀʟʀᴇᴀᴅʏ ᴏɴ ✅", show_alert=True)
            return
        await thumb_on(chat_id)
        await callback.answer("✅ ᴛʜᴜᴍʙɴᴀɪʟ ᴇɴᴀʙʟᴇᴅ!")
    else:
        if not enabled:
            await callback.answer("ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ ᴘᴇʜʟᴇ sᴇ ᴀᴄᴛɪᴠᴇ ❌", show_alert=True)
            return
        await thumb_off(chat_id)
        await callback.answer("❌ ᴛʜᴜᴍʙɴᴀɪʟ ᴏꜰꜰ — ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ ᴀᴄᴛɪᴠᴇ!")

    new_enabled = await is_thumb_enabled(chat_id)
    try:
        await callback.message.edit_reply_markup(
            reply_markup=thumb_markup(_, new_enabled)
        )
    except Exception:
        pass
