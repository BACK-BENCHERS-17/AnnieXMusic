"""KHUSHI — Language: /language + LANGUAGE_SETTINGS callback."""

from pyrogram import filters
from pyrogram.errors import MessageNotModified
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from KHUSHI import app
from KHUSHI.utils.database import get_lang, set_lang
from KHUSHI.utils.decorators import AdminActual
from KHUSHI.utils.decorators_annie.admins import ActualAdminCB
from KHUSHI.utils.decorators_annie.language import language, languageCB
from KHUSHI.utils.inline import InlineKeyboardButton
from config import BANNED_USERS
from strings import languages_present

_BRAND = (
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
)

_LANG_FLAGS = {
    "en": "🇺🇸",
    "hi": "🇮🇳",
    "ar": "🇸🇦",
    "ru": "🇷🇺",
    "tr": "🇹🇷",
}


def _lang_markup(_, current_lang: str) -> InlineKeyboardMarkup:
    rows = []
    items = list(languages_present.items())
    for i in range(0, len(items), 2):
        row = []
        for code, name in items[i:i+2]:
            tick = "✅ " if code == current_lang else ""
            row.append(InlineKeyboardButton(
                text=f"{tick}{name}",
                callback_data=f"set_lang_{code}",
                style="success" if code == current_lang else "primary",
            ))
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text=_["BACK_BUTTON"], callback_data="SETTINGS_BACK", style="primary"),
        InlineKeyboardButton(text=_["CLOSE_BUTTON"], callback_data="close", style="danger"),
    ])
    return InlineKeyboardMarkup(rows)


def _lang_text(_) -> str:
    return (
        f"<blockquote>{_BRAND}</blockquote>\n\n"
        f"<blockquote>"
        f"┌────── ˹ ʟᴀɴɢᴜᴀɢᴇ ˼─── ⏤‌‌●\n"
        f"┆<emoji id='5972072533833289156'>🔹</emoji> {_['lang_1']}\n"
        f"└──────────────────────●"
        f"</blockquote>"
    )


@app.on_message(
    filters.command(["language", "lang", "setlang"], prefixes=["/", ".", "!"])
    & filters.group
    & ~BANNED_USERS
)
@AdminActual
async def language_cmd(client, message: Message, _):
    current = await get_lang(message.chat.id)
    await message.reply_text(
        _lang_text(_),
        reply_markup=_lang_markup(_, current),
    )


@app.on_callback_query(filters.regex(r"^LANGUAGE_SETTINGS$") & ~BANNED_USERS)
@ActualAdminCB
async def language_settings_cb(client, callback: CallbackQuery, _):
    current = await get_lang(callback.message.chat.id)
    try:
        await callback.answer(_["set_cb_1"], show_alert=True)
    except Exception:
        pass
    try:
        await callback.edit_message_text(
            _lang_text(_),
            reply_markup=_lang_markup(_, current),
        )
    except MessageNotModified:
        pass


@app.on_callback_query(filters.regex(r"^set_lang_(\w+)$") & ~BANNED_USERS)
@ActualAdminCB
async def set_lang_cb(client, callback: CallbackQuery, _):
    from strings import get_string
    code = callback.matches[0].group(1)
    if code not in languages_present:
        return await callback.answer("❌ Invalid language.", show_alert=True)
    current = await get_lang(callback.message.chat.id)
    if current == code:
        return await callback.answer(_["lang_4"], show_alert=True)
    await set_lang(callback.message.chat.id, code)
    new_lang = get_string(code)
    await callback.answer(f"✅ {languages_present[code]}")
    try:
        await callback.edit_message_text(
            _lang_text(new_lang),
            reply_markup=_lang_markup(new_lang, code),
        )
    except MessageNotModified:
        pass
