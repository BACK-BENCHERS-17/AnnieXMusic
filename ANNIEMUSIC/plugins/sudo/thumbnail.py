from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from ANNIEMUSIC import app
from ANNIEMUSIC.utils.database import is_thumb_enabled, thumb_on, thumb_off
from config import OWNER_ID, BANNED_USERS

E_BEAR = "<emoji id='5042192219960771668'>🧸</emoji>"
E_CAM  = "<emoji id='5787544344906959608'>📸</emoji>"
E_VID  = "<emoji id='5373141891321699086'>🎬</emoji>"
E_DOT  = "<emoji id='5972072533833289156'>🔹</emoji>"
E_LOCK = "<emoji id='5821116489428057931'>🔒</emoji>"

ANNIE_ROW = (
    f"<emoji id='5042192219960771668'>🧸</emoji>"
    f"<emoji id='5210820276748566172'>🔤</emoji>"
    f"<emoji id='5213301251722203632'>🔤</emoji>"
    f"<emoji id='5213301251722203632'>🔤</emoji>"
    f"<emoji id='5211032856154885824'>🔤</emoji>"
    f"<emoji id='5213337333742454261'>🔤</emoji>"
)


def thumb_markup(enabled: bool) -> InlineKeyboardMarkup:
    bar_on  = "▰▰▰▰▰▱▱▱▱▱"
    bar_off = "▱▱▱▱▱▰▰▰▰▰"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=f"✅ ᴛʜᴜᴍʙɴᴀɪʟ ᴏɴ {bar_on}" if enabled else f"ᴛʜᴜᴍʙɴᴀɪʟ ᴏɴ {bar_on}",
                callback_data="GTHUMB_ON",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ {bar_off}" if enabled else f"❌ ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ {bar_off}",
                callback_data="GTHUMB_OFF",
            ),
        ],
        [
            InlineKeyboardButton(text="✖ ᴄʟᴏsᴇ", callback_data="close"),
        ],
    ])


OWNER_FILTER = filters.user(OWNER_ID) & ~BANNED_USERS


@app.on_message(filters.command(["thumbnail", "thumb"]) & OWNER_FILTER)
async def thumbnail_command(client, message: Message):
    enabled = await is_thumb_enabled()
    status = "ᴇɴᴀʙʟᴇᴅ ✅" if enabled else "ᴅɪsᴀʙʟᴇᴅ ❌ — ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ ᴀᴄᴛɪᴠᴇ"

    if len(message.command) == 2:
        arg = message.command[1].lower()

        if arg == "on":
            if enabled:
                return await message.reply_text(
                    f"<blockquote>"
                    f"┌────── ˹ ɢʟᴏʙᴀʟ ᴛʜᴜᴍʙɴᴀɪʟ ˼─── ⏤‌‌●\n"
                    f"┆{E_CAM} <b>ᴛʜᴜᴍʙɴᴀɪʟ ɪs ᴀʟʀᴇᴀᴅʏ ᴇɴᴀʙʟᴇᴅ ✅</b>\n"
                    f"└──────────────────────●"
                    f"</blockquote>\n"
                    f"<blockquote>{ANNIE_ROW}</blockquote>"
                )
            await thumb_on()
            return await message.reply_text(
                f"<blockquote>"
                f"┌────── ˹ ɢʟᴏʙᴀʟ ᴛʜᴜᴍʙɴᴀɪʟ ˼─── ⏤‌‌●\n"
                f"┆{E_CAM} <b>ᴛʜᴜᴍʙɴᴀɪʟ ᴇɴᴀʙʟᴇᴅ ɢʟᴏʙᴀʟʟʏ ✅</b>\n"
                f"┆{E_DOT} sᴀʙʜɪ ɢʀᴏᴜᴘs ᴍᴇɪɴ ᴛʜᴜᴍʙɴᴀɪʟ ᴅɪᴋʜᴇɢᴀ!\n"
                f"└──────────────────────●"
                f"</blockquote>\n"
                f"<blockquote>{ANNIE_ROW}</blockquote>"
            )

        elif arg == "off":
            if not enabled:
                return await message.reply_text(
                    f"<blockquote>"
                    f"┌────── ˹ ɢʟᴏʙᴀʟ ᴛʜᴜᴍʙɴᴀɪʟ ˼─── ⏤‌‌●\n"
                    f"┆{E_VID} <b>ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ ᴘᴇʜʟᴇ sᴇ ᴀᴄᴛɪᴠᴇ ʜᴀɪ ❌</b>\n"
                    f"└──────────────────────●"
                    f"</blockquote>\n"
                    f"<blockquote>{ANNIE_ROW}</blockquote>"
                )
            await thumb_off()
            return await message.reply_text(
                f"<blockquote>"
                f"┌────── ˹ ɢʟᴏʙᴀʟ ᴛʜᴜᴍʙɴᴀɪʟ ˼─── ⏤‌‌●\n"
                f"┆{E_VID} <b>ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ ᴀᴄᴛɪᴠᴀᴛᴇᴅ ɢʟᴏʙᴀʟʟʏ ❌</b>\n"
                f"┆{E_LOCK} sᴀʙʜɪ ɢʀᴏᴜᴘs ᴍᴇɪɴ ᴠɪᴅᴇᴏ ᴀᴀɪɢᴀ!\n"
                f"┆{E_DOT} ɢʀᴏᴜᴘ ꜰᴜʟʟ ᴘʀᴏᴛᴇᴄᴛ ʀᴀʜᴇɢᴀ 🔒\n"
                f"└──────────────────────●"
                f"</blockquote>\n"
                f"<blockquote>{ANNIE_ROW}</blockquote>"
            )

        else:
            return await message.reply_text(
                f"<blockquote>"
                f"┌────── ˹ ɢʟᴏʙᴀʟ ᴛʜᴜᴍʙɴᴀɪʟ ˼─── ⏤‌‌●\n"
                f"┆{E_DOT} <b>ᴜsᴀɢᴇ :</b>\n"
                f"┆  <code>/thumbnail on</code>  — ᴛʜᴜᴍʙɴᴀɪʟ ᴏɴ\n"
                f"┆  <code>/thumbnail off</code> — ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ\n"
                f"└──────────────────────●"
                f"</blockquote>\n"
                f"<blockquote>{ANNIE_ROW}</blockquote>"
            )

    await message.reply_text(
        f"<blockquote>"
        f"┌────── ˹ ɢʟᴏʙᴀʟ ᴛʜᴜᴍʙɴᴀɪʟ ˼─── ⏤‌‌●\n"
        f"┆{E_BEAR} <b>sᴛᴀᴛᴜs :</b> <b>{status}</b>\n"
        f"┆{E_CAM} <b>ᴏɴ</b>  → ɴᴏʀᴍᴀʟ ᴛʜᴜᴍʙɴᴀɪʟ ᴘʜᴏᴛᴏ\n"
        f"┆{E_VID} <b>ᴏꜰꜰ</b> → ᴠɪᴅᴇᴏ sᴇɴᴅ ʜᴏɢᴀ (ɢʀᴏᴜᴘ ᴘʀᴏᴛᴇᴄᴛ)\n"
        f"┆{E_LOCK} <b>ɢʟᴏʙᴀʟ</b> — sᴀʙʜɪ ɢʀᴏᴜᴘs ᴘᴀʀ ʟᴀɢᴜ ʜᴏɢᴀ\n"
        f"┆{E_DOT} <code>/thumbnail on</code> | <code>/thumbnail off</code>\n"
        f"└──────────────────────●"
        f"</blockquote>\n"
        f"<blockquote>{ANNIE_ROW}</blockquote>",
        reply_markup=thumb_markup(enabled),
    )


@app.on_callback_query(filters.regex("^GTHUMB_(ON|OFF)$") & OWNER_FILTER)
async def thumb_toggle_cb(client, callback):
    action = callback.data.split("_")[-1]
    enabled = await is_thumb_enabled()

    if action == "ON":
        if enabled:
            return await callback.answer("ᴛʜᴜᴍʙɴᴀɪʟ ɪs ᴀʟʀᴇᴀᴅʏ ᴏɴ ✅", show_alert=True)
        await thumb_on()
        await callback.answer("✅ ᴛʜᴜᴍʙɴᴀɪʟ ᴇɴᴀʙʟᴇᴅ ɢʟᴏʙᴀʟʟʏ!")
    else:
        if not enabled:
            return await callback.answer("ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ ᴘᴇʜʟᴇ sᴇ ᴀᴄᴛɪᴠᴇ ❌", show_alert=True)
        await thumb_off()
        await callback.answer("❌ ᴠɪᴅᴇᴏ ᴍᴏᴅᴇ ᴀᴄᴛɪᴠᴇ ɢʟᴏʙᴀʟʟʏ!")

    new_enabled = await is_thumb_enabled()
    try:
        await callback.message.edit_reply_markup(reply_markup=thumb_markup(new_enabled))
    except Exception:
        pass
