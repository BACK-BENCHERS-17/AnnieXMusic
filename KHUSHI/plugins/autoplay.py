"""KHUSHI — Autoplay: /autoplay, /ap"""

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, Message

from KHUSHI import app
from KHUSHI.utils.database import autoplay_off, autoplay_on, is_autoplay
from KHUSHI.utils.decorators import GroupAdminCheck as AdminRightsCheck
from KHUSHI.utils.inline import close_markup, InlineKeyboardButton
from config import BANNED_USERS


_BRAND = ""
_E_CHECK     = '<emoji id="5852871561983299073">✅</emoji>'
_E_CROSS     = '<emoji id="5040042498634810056">❌</emoji>'
_E_REPEAT    = '<emoji id="6030657343744644592">🔁</emoji>'
_E_NOTES     = '<emoji id="5039771357349413873">🎶</emoji>'
_E_ZAP       = '<emoji id="5042334757040423886">⚡️</emoji>'
_E_HOURGLASS = '<emoji id="5454415424319931791">⏳</emoji>'
_E_DOT       = '<emoji id="5972072533833289156">🔹</emoji>'


def _panel(title: str, rows: list[str]) -> str:
    bar_open  = f"┌────── ˹ {title} ˼ ─── ⏤‌●"
    bar_close = "└──────────────────●"
    body = bar_open + "\n" + "\n".join(f"┆{r}" for r in rows) + "\n" + bar_close
    return f"<blockquote>{body}</blockquote>"


def _autoplay_text(enabled: bool) -> str:
    status_em  = _E_CHECK if enabled else _E_CROSS
    status_txt = "ᴇɴᴀʙʟᴇᴅ" if enabled else "ᴅɪsᴀʙʟᴇᴅ"
    return _BRAND + _panel(
        "ᴀᴜᴛᴏᴘʟᴀʏ",
        [
            f"{_E_REPEAT} <b>ꜱᴛᴀᴛᴜs:</b>  {status_em} <b>{status_txt}</b>",
            f"{_E_NOTES}  ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴘʟᴀʏs ᴀ ʀᴇʟᴀᴛᴇᴅ sᴏɴɢ ᴡʜᴇɴ ǫᴜᴇᴜᴇ ᴇɴᴅs",
            f"{_E_ZAP}   ᴍᴜsɪᴄ ɴᴇᴠᴇʀ sᴛᴏᴘs ᴇᴠᴇɴ ᴀꜰᴛᴇʀ ᴛʜᴇ ʟᴀsᴛ ᴛʀᴀᴄᴋ!",
        ],
    )


def autoplay_markup(_, enabled: bool, from_settings: bool = False):
    rows = [
        [
            InlineKeyboardButton(
                text="✅ ᴏɴ" if enabled else "ᴏɴ",
                callback_data="AUTOPLAY_TOGGLE_ON",
                style="success" if enabled else "primary",
            ),
            InlineKeyboardButton(
                text="ᴏꜰꜰ" if enabled else "❌ ᴏꜰꜰ",
                callback_data="AUTOPLAY_TOGGLE_OFF",
                style="primary" if enabled else "danger",
            ),
        ],
    ]
    if from_settings:
        rows.append([
            InlineKeyboardButton(
                text=_["BACK_BUTTON"],
                callback_data="SETTINGS_BACK",
                style="primary",
            ),
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data="close",
                style="danger",
            ),
        ])
    else:
        rows.append([
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data="close",
                style="danger",
            )
        ])
    return InlineKeyboardMarkup(rows)


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
                    _BRAND + _panel("ᴀᴜᴛᴏᴘʟᴀʏ", [
                        f"{_E_CHECK} ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ <b>ᴇɴᴀʙʟᴇᴅ</b>.",
                    ])
                )
            await autoplay_on(chat_id)
            return await message.reply_text(
                _BRAND + _panel("ᴀᴜᴛᴏᴘʟᴀʏ", [
                    f"{_E_CHECK} <b>ᴀᴜᴛᴏᴘʟᴀʏ ᴇɴᴀʙʟᴇᴅ!</b>",
                    f"{_E_NOTES} ᴡɪʟʟ ᴀᴜᴛᴏ-ᴘʟᴀʏ ʀᴇʟᴀᴛᴇᴅ sᴏɴɢs ᴡʜᴇɴ ǫᴜᴇᴜᴇ ᴇɴᴅs.",
                ]),
                reply_markup=close_markup(_),
            )
        elif arg == "off":
            if not enabled:
                return await message.reply_text(
                    _BRAND + _panel("ᴀᴜᴛᴏᴘʟᴀʏ", [
                        f"{_E_CROSS} ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴀʟʀᴇᴀᴅʏ <b>ᴅɪsᴀʙʟᴇᴅ</b>.",
                    ])
                )
            await autoplay_off(chat_id)
            return await message.reply_text(
                _BRAND + _panel("ᴀᴜᴛᴏᴘʟᴀʏ", [
                    f"{_E_CROSS} <b>ᴀᴜᴛᴏᴘʟᴀʏ ᴅɪsᴀʙʟᴇᴅ.</b>",
                    f"{_E_HOURGLASS} ᴍᴜsɪᴄ ᴡɪʟʟ sᴛᴏᴘ ᴀꜰᴛᴇʀ ᴄᴜʀʀᴇɴᴛ ǫᴜᴇᴜᴇ ᴇɴᴅs.",
                ]),
                reply_markup=close_markup(_),
            )
        else:
            return await message.reply_text(
                _BRAND + _panel("ᴀᴜᴛᴏᴘʟᴀʏ", [
                    f"{_E_DOT} <code>/autoplay on</code>   — ᴇɴᴀʙʟᴇ ᴀᴜᴛᴏᴘʟᴀʏ",
                    f"{_E_DOT} <code>/autoplay off</code>  — ᴅɪsᴀʙʟᴇ ᴀᴜᴛᴏᴘʟᴀʏ",
                ])
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
    from_settings = any(
        getattr(btn, "callback_data", "") == "SETTINGS_BACK"
        for row in (callback.message.reply_markup.inline_keyboard if callback.message.reply_markup else [])
        for btn in row
    )
    try:
        await callback.message.edit_text(
            text=_autoplay_text(new_enabled),
            reply_markup=autoplay_markup(_, new_enabled, from_settings=from_settings),
        )
    except Exception:
        try:
            await callback.message.edit_reply_markup(reply_markup=autoplay_markup(_, new_enabled, from_settings=from_settings))
        except Exception:
            pass
