"""KHUSHI — VC Tools: /vcinfo, /vclogger, /mutevc, /unmutevc."""

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from KHUSHI import app
from KHUSHI.core.call import JARVIS
from KHUSHI.core.mongo import mongodb
from KHUSHI.utils.database import is_active_chat
from KHUSHI.utils.decorators import KhushiAdminCheck as AdminRightsCheck
from config import BANNED_USERS

_vclogdb = mongodb.vclogger_settings

_BRAND = (
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
)

_EM = {
    "vc":    "<emoji id='5226772700113935347'>📞</emoji>",
    "dot":   "<emoji id='5972072533833289156'>🔹</emoji>",
    "zap":   "<emoji id='5042334757040423886'>⚡️</emoji>",
    "mute":  "<emoji id='5467666044815377227'>⚠️</emoji>",
    "log":   "<emoji id='5116468787377341336'>💬</emoji>",
}

_vclog_cache: dict[int, bool] = {}


def _reply(text: str) -> str:
    return f"<blockquote>{_BRAND}</blockquote>\n\n<blockquote>{text}</blockquote>"


def _close():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close"),
    ]])


async def _is_vclog_on(chat_id: int) -> bool:
    if chat_id in _vclog_cache:
        return _vclog_cache[chat_id]
    doc = await _vclogdb.find_one({"chat_id": chat_id})
    result = doc.get("enabled", False) if doc else False
    _vclog_cache[chat_id] = result
    return result


async def _set_vclog(chat_id: int, status: bool):
    _vclog_cache[chat_id] = status
    await _vclogdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"enabled": status}},
        upsert=True,
    )


@app.on_message(
    filters.command(["vcinfo"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def vcinfo_cmd(client, message: Message, lang, chat_id):
    active = await is_active_chat(chat_id)
    if not active:
        return await message.reply_text(
            _reply(f"{_EM['vc']} ɴᴏ ᴀᴄᴛɪᴠᴇ ᴠᴄ / sᴛʀᴇᴀᴍ ɪɴ ᴛʜɪs ɢʀᴏᴜᴘ."),
            reply_markup=_close(),
        )

    try:
        assistant_num = await JARVIS.group_assistant(chat_id)
        assistant = JARVIS.pytgcalls[assistant_num]
        participants = await assistant.get_participants(chat_id)

        if not participants:
            return await message.reply_text(
                _reply(f"{_EM['vc']} ᴠᴄ ɪs ᴇᴍᴘᴛʏ ʀɪɢʜᴛ ɴᴏᴡ."),
                reply_markup=_close(),
            )

        lines = []
        for i, p in enumerate(participants[:20], 1):
            uid = getattr(p, "user_id", "?")
            muted = "🔇" if getattr(p, "muted", False) else "🔊"
            lines.append(f"{_EM['dot']} <code>{i}.</code> <code>{uid}</code> {muted}")

        total = len(participants)
        text = (
            f"{_EM['vc']} <b>ᴠᴄ ᴘᴀʀᴛɪᴄɪᴘᴀɴᴛs</b> — <code>{total}</code>\n\n"
            + "\n".join(lines)
        )
        if total > 20:
            text += f"\n\n{_EM['zap']} +{total - 20} ᴍᴏʀᴇ..."
    except Exception as e:
        text = (
            f"{_EM['vc']} <b>ᴠᴄ ɪs ᴀᴄᴛɪᴠᴇ</b>\n"
            f"{_EM['dot']} ᴄᴏᴜʟᴅ ɴᴏᴛ ꜰᴇᴛᴄʜ ᴘᴀʀᴛɪᴄɪᴘᴀɴᴛ ʟɪsᴛ.\n"
            f"{_EM['zap']} <code>{e}</code>"
        )

    await message.reply_text(_reply(text), reply_markup=_close())


@app.on_message(
    filters.command(["vclogger"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def vclogger_cmd(client, message: Message, lang, chat_id):
    args = message.command[1:]
    on = await _is_vclog_on(chat_id)

    if not args or args[0].lower() not in ("on", "off"):
        state = "✅ ᴏɴ" if on else "❌ ᴏꜰꜰ"
        return await message.reply_text(
            _reply(
                f"{_EM['log']} <b>ᴠᴄ ʟᴏɢɢᴇʀ</b>\n\n"
                f"{_EM['dot']} ꜱᴛᴀᴛᴜꜱ: <b>{state}</b>\n"
                f"{_EM['dot']} ᴜꜱᴇ: <code>/vclogger on|off</code>"
            ),
            reply_markup=_close(),
        )

    enable = args[0].lower() == "on"
    await _set_vclog(chat_id, enable)
    state = "✅ ᴇɴᴀʙʟᴇᴅ" if enable else "❌ ᴅɪꜱᴀʙʟᴇᴅ"
    await message.reply_text(
        _reply(
            f"{_EM['log']} <b>ᴠᴄ ʟᴏɢɢᴇʀ {state}</b>\n"
            f"{_EM['dot']} ᴠᴄ ᴊᴏɪɴ/ʟᴇᴀᴠᴇ ᴡɪʟʟ ʙᴇ "
            f"{'ʟᴏɢɢᴇᴅ' if enable else 'ɴᴏᴛ ʟᴏɢɢᴇᴅ'}.\n"
            f"{_EM['dot']} ʙʏ: {message.from_user.mention}"
        ),
        reply_markup=_close(),
    )


@app.on_message(
    filters.command(["mutevc"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def mutevc_cmd(client, message: Message, lang, chat_id):
    active = await is_active_chat(chat_id)
    if not active:
        return await message.reply_text(
            _reply(f"{_EM['mute']} ɴᴏ ᴀᴄᴛɪᴠᴇ sᴛʀᴇᴀᴍ ᴛᴏ ᴍᴜᴛᴇ."),
            reply_markup=_close(),
        )
    try:
        await JARVIS.mute_stream(chat_id)
        await message.reply_text(
            _reply(
                f"{_EM['mute']} <b>ᴀssɪsᴛᴀɴᴛ ᴍᴜᴛᴇᴅ</b> ɪɴ ᴠᴄ.\n"
                f"{_EM['dot']} ᴜꜱᴇ <code>/unmutevc</code> ᴛᴏ ᴜɴᴍᴜᴛᴇ.\n"
                f"{_EM['dot']} ʙʏ: {message.from_user.mention}"
            ),
            reply_markup=_close(),
        )
    except Exception as e:
        await message.reply_text(
            _reply(f"❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ᴍᴜᴛᴇ: <code>{e}</code>"),
            reply_markup=_close(),
        )


@app.on_message(
    filters.command(["unmutevc"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def unmutevc_cmd(client, message: Message, lang, chat_id):
    active = await is_active_chat(chat_id)
    if not active:
        return await message.reply_text(
            _reply(f"{_EM['mute']} ɴᴏ ᴀᴄᴛɪᴠᴇ sᴛʀᴇᴀᴍ ᴛᴏ ᴜɴᴍᴜᴛᴇ."),
            reply_markup=_close(),
        )
    try:
        await JARVIS.unmute_stream(chat_id)
        await message.reply_text(
            _reply(
                f"{_EM['vc']} <b>ᴀssɪsᴛᴀɴᴛ ᴜɴᴍᴜᴛᴇᴅ</b> ɪɴ ᴠᴄ.\n"
                f"{_EM['dot']} ᴀᴜᴅɪᴏ ɪs ɴᴏᴡ ᴀᴄᴛɪᴠᴇ.\n"
                f"{_EM['dot']} ʙʏ: {message.from_user.mention}"
            ),
            reply_markup=_close(),
        )
    except Exception as e:
        await message.reply_text(
            _reply(f"❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ᴜɴᴍᴜᴛᴇ: <code>{e}</code>"),
            reply_markup=_close(),
        )
