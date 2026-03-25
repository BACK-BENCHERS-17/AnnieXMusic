from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from ANNIEMUSIC import app
from ANNIEMUSIC.utils.database import is_thumb_enabled, thumb_on, thumb_off
from config import OWNER_ID, BANNED_USERS

OWNER_FILTER = filters.user(OWNER_ID) & ~BANNED_USERS


def thumb_markup(enabled: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text="✅ Thumbnail ON" if enabled else "📸 Thumbnail ON",
                callback_data="GTHUMB_ON",
            ),
            InlineKeyboardButton(
                text="🎬 Video Mode OFF" if enabled else "❌ Video Mode ON",
                callback_data="GTHUMB_OFF",
            ),
        ],
        [
            InlineKeyboardButton(text="✖ Close", callback_data="close"),
        ],
    ])


def status_text(enabled: bool) -> str:
    if enabled:
        return (
            "<b>📸 Global Thumbnail Settings</b>\n\n"
            "<b>Status:</b> <code>ON ✅</code> — Thumbnail photo send hoga\n\n"
            "<b>/thumbnail on</b>  — Thumbnail enable karo\n"
            "<b>/thumbnail off</b> — Video mode enable karo\n\n"
            "<i>Ye setting sabhi groups par apply hogi.</i>"
        )
    else:
        return (
            "<b>🎬 Global Thumbnail Settings</b>\n\n"
            "<b>Status:</b> <code>OFF ❌</code> — Video mode active hai\n\n"
            "<b>/thumbnail on</b>  — Thumbnail enable karo\n"
            "<b>/thumbnail off</b> — Video mode enable karo\n\n"
            "<i>Ye setting sabhi groups par apply hogi. 🔒</i>"
        )


@app.on_message(filters.command(["thumbnail", "thumb"]) & OWNER_FILTER)
async def thumbnail_command(client, message: Message):
    enabled = await is_thumb_enabled()

    if len(message.command) == 2:
        arg = message.command[1].lower()

        if arg == "on":
            if enabled:
                return await message.reply_text(
                    "📸 <b>Thumbnail pehle se ON hai!</b>"
                )
            await thumb_on()
            return await message.reply_text(
                "✅ <b>Thumbnail globally ON kar diya!</b>\n"
                "Sabhi groups mein thumbnail photo aayegi."
            )

        elif arg == "off":
            if not enabled:
                return await message.reply_text(
                    "🎬 <b>Video mode pehle se active hai!</b>"
                )
            await thumb_off()
            return await message.reply_text(
                "❌ <b>Thumbnail globally OFF kar diya!</b>\n"
                "Sabhi groups mein video aayegi. 🔒"
            )

        else:
            return await message.reply_text(
                "<b>Usage:</b>\n"
                "/thumbnail on — Thumbnail enable karo\n"
                "/thumbnail off — Video mode enable karo"
            )

    await message.reply_text(
        status_text(enabled),
        reply_markup=thumb_markup(enabled),
    )


@app.on_callback_query(filters.regex("^GTHUMB_(ON|OFF)$") & OWNER_FILTER)
async def thumb_toggle_cb(client, callback):
    action = callback.data.split("_")[-1]
    enabled = await is_thumb_enabled()

    if action == "ON":
        if enabled:
            return await callback.answer("Thumbnail is already ON ✅", show_alert=True)
        await thumb_on()
        await callback.answer("✅ Thumbnail globally enabled!")
    else:
        if not enabled:
            return await callback.answer("Video mode is already active ❌", show_alert=True)
        await thumb_off()
        await callback.answer("❌ Video mode globally active!")

    new_enabled = await is_thumb_enabled()
    try:
        await callback.message.edit_text(
            status_text(new_enabled),
            reply_markup=thumb_markup(new_enabled),
        )
    except Exception:
        pass
