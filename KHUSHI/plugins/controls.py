"""KHUSHI — Music Controls: pause, resume, skip, stop, loop, seek, shuffle, volume, 247, speed."""

import random

from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from KHUSHI.utils.inline import InlineKeyboardButton

from KHUSHI import app
from KHUSHI.core.call import JARVIS
from KHUSHI.misc import db
from KHUSHI.utils import seconds_to_min
from KHUSHI.utils.database import (
    autoplay_off,
    autoplay_on,
    disable_247,
    enable_247,
    get_lang,
    get_loop,
    get_volume,
    is_24_7,
    is_active_chat,
    is_autoplay,
    is_music_playing,
    music_off,
    music_on,
    set_loop,
    set_volume,
)
from KHUSHI.utils.decorators import KhushiAdminCheck as AdminRightsCheck
from KHUSHI.utils.decorators_annie.admins import ActualAdminCB
from KHUSHI.utils.stream.autoclear import auto_clean
from strings import get_string
from config import BANNED_USERS

from KHUSHI.utils.ui import BRAND as _BRAND, E as _E_UI

_EM = {
    "fire":   _E_UI["fire"],
    "dot":    _E_UI["dot"],
    "zap":    _E_UI["zap"],
    "star":   _E_UI["gift"],
    "warn":   _E_UI["warn"],
    "cross":  _E_UI["cross"],
    "shuffle": _E_UI["shuffle"],
    "queue":  _E_UI["queue"],
    "pause":  _E_UI["pause"],
    "play":   _E_UI["live"],
    "stop":   _E_UI["stop"],
}

def _close():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close", style="danger")
    ]])

def _reply(text):
    return f"<blockquote>{_BRAND}</blockquote>\n\n<blockquote>{text}</blockquote>"


# ── PAUSE ─────────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["pause", "cpause"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def kpause(_, message: Message, lang, chat_id):
    if not await is_music_playing(chat_id):
        return await message.reply_text(_reply(f"{_EM['play']} ɴᴏᴛʜɪɴɢ ɪꜱ ᴘʟᴀʏɪɴɢ ʀɪɢʜᴛ ɴᴏᴡ."))
    await music_off(chat_id)
    await JARVIS.pause_stream(chat_id)
    await message.reply_text(
        _reply(f"{_EM['zap']} <b>ᴘᴀᴜꜱᴇᴅ</b>\n{_EM['dot']} ʙʏ : {message.from_user.mention}"),
        reply_markup=_close(),
    )


# ── RESUME ────────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["resume", "cresume"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def kresume(_, message: Message, lang, chat_id):
    if await is_music_playing(chat_id):
        return await message.reply_text(_reply(f"{_EM['play']} ᴀʟʀᴇᴀᴅʏ ᴘʟᴀʏɪɴɢ."))
    await music_on(chat_id)
    await JARVIS.resume_stream(chat_id)
    await message.reply_text(
        _reply(f"{_EM['fire']} <b>ʀᴇꜱᴜᴍᴇᴅ</b>\n{_EM['dot']} ʙʏ : {message.from_user.mention}"),
        reply_markup=_close(),
    )


# ── RELOAD (Refresh Admin Cache) ──────────────────────────────────────────────
@app.on_message(
    filters.command(["reload", "refresh"], prefixes=["/", "!", "."]) & filters.group & ~BANNED_USERS
)
async def kreload(client, message: Message):
    """Refresh the admin list cache for this group."""
    from KHUSHI.utils.database import get_lang
    from strings import get_string
    try:
        language = await get_lang(message.chat.id)
        _ = get_string(language)
    except Exception:
        _ = get_string("en")

    if message.sender_chat:
        return await message.reply_text(_reply(f"{_EM['cross']} ᴀɴᴏɴʏᴍᴏᴜs ᴀᴅᴍɪɴs ᴄᴀɴɴᴏᴛ ᴜꜱᴇ ᴛʜɪs."))

    from KHUSHI.misc import SUDOERS
    from config import adminlist

    chat_id = message.chat.id

    try:
        from pyrogram.enums import ChatMembersFilter
        admin_ids = []
        async for m in client.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
            if not m.user.is_bot:
                admin_ids.append(m.user.id)
        adminlist[chat_id] = admin_ids
        count = len(adminlist[chat_id])
        await message.reply_text(
            _reply(
                f"{_EM['zap']} <b>ᴀᴅᴍɪɴ ʟɪsᴛ ʀᴇꜰʀᴇsʜᴇᴅ</b>\n"
                f"{_EM['dot']} <b>{count}</b> ᴀᴅᴍɪɴs ᴄᴀᴄʜᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ.\n"
                f"{_EM['dot']} ʙʏ : {message.from_user.mention}"
            ),
            reply_markup=_close(),
        )
    except Exception as e:
        await message.reply_text(
            _reply(f"{_EM['cross']} ʀᴇʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ: <code>{type(e).__name__}</code>"),
            reply_markup=_close(),
        )


# ── STOP ──────────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["stop", "end", "cstop", "cend"], prefixes=["/", "!", "."]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def kstop(_, message: Message, lang, chat_id):
    await JARVIS.stop_stream(chat_id)
    await set_loop(chat_id, 0)
    await message.reply_text(
        _reply(f"{_EM['zap']} <b>ꜱᴛᴏᴘᴘᴇᴅ & ǫᴜᴇᴜᴇ ᴄʟᴇᴀʀᴇᴅ</b>\n{_EM['dot']} ʙʏ : {message.from_user.mention}"),
        reply_markup=_close(),
    )


# ── SKIP ──────────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["skip", "next", "cskip", "cnext"], prefixes=["/", "!", "."]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def kskip(_, message: Message, lang, chat_id):
    check = db.get(chat_id)
    if not check:
        return await message.reply_text(_reply(f"{_EM['warn']} ɴᴏᴛʜɪɴɢ ɪɴ ǫᴜᴇᴜᴇ."))

    popped = None
    try:
        popped = check.pop(0)
        if popped:
            await auto_clean(popped)
        if not check:
            await message.reply_text(
                _reply(f"{_EM['star']} <b>ǫᴜᴇᴜᴇ ᴇᴍᴘᴛʏ</b> — ꜱᴛᴏᴘᴘɪɴɢ.\n{_EM['dot']} ʙʏ : {message.from_user.mention}"),
                reply_markup=_close(),
            )
            return await JARVIS.stop_or_autoplay(chat_id, popped)
    except Exception:
        return await message.reply_text(_reply(f"{_EM['cross']} ᴄᴀɴɴᴏᴛ ꜱᴋɪᴘ."))

    title = check[0].get("title", "Unknown").title()
    await message.reply_text(
        _reply(
            f"{_EM['fire']} <b>ꜱᴋɪᴘᴘᴇᴅ</b>\n"
            f"{_EM['dot']} <b>ɴᴏᴡ ᴘʟᴀʏɪɴɢ:</b> {title}\n"
            f"{_EM['dot']} ʙʏ : {message.from_user.mention}"
        ),
        reply_markup=_close(),
    )
    try:
        await JARVIS.skip_stream(chat_id, check[0]["file"])
    except Exception:
        pass


# ── LOOP ──────────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["loop", "cloop"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def kloop(_, message: Message, lang, chat_id):
    if len(message.command) != 2:
        return await message.reply_text(_reply(f"{_EM['dot']} ᴜꜱᴀɢᴇ: /loop [1-10 | enable | disable]"))
    state = message.text.split(None, 1)[1].strip()
    if state.lower() == "disable":
        await set_loop(chat_id, 0)
        return await message.reply_text(
            _reply(f"{_EM['zap']} <b>ʟᴏᴏᴘ ᴅɪꜱᴀʙʟᴇᴅ</b>\n{_EM['dot']} ʙʏ : {message.from_user.mention}"),
            reply_markup=_close(),
        )
    if state.lower() == "enable":
        state = "10"
    if state.isnumeric():
        n = int(state)
        if 1 <= n <= 10:
            await set_loop(chat_id, n)
            return await message.reply_text(
                _reply(f"{_EM['fire']} <b>ʟᴏᴏᴘ ꜱᴇᴛ ᴛᴏ {n}×</b>\n{_EM['dot']} ʙʏ : {message.from_user.mention}"),
                reply_markup=_close(),
            )
    await message.reply_text(_reply(f"{_EM['dot']} ᴜꜱᴀɢᴇ: /loop [1-10 | enable | disable]"))


# ── SHUFFLE ───────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["shuffle", "cshuffle"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def kshuffle(_, message: Message, lang, chat_id):
    check = db.get(chat_id)
    if not check:
        return await message.reply_text(_reply(f"{_EM['warn']} ǫᴜᴇᴜᴇ ɪꜱ ᴇᴍᴘᴛʏ."))
    try:
        first = check.pop(0)
        random.shuffle(check)
        check.insert(0, first)
    except Exception:
        return await message.reply_text(_reply(f"{_EM['cross']} ᴄᴀɴɴᴏᴛ ꜱʜᴜꜰꜰʟᴇ."))
    await message.reply_text(
        _reply(f"{_EM['fire']} <b>ǫᴜᴇᴜᴇ ꜱʜᴜꜰꜰʟᴇᴅ</b> {_EM['shuffle']}\n{_EM['dot']} ʙʏ : {message.from_user.mention}"),
        reply_markup=_close(),
    )


# ── VOLUME ────────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["volume", "vol", "cvol", "cvolume"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def kvolume(_, message: Message, lang, chat_id):
    if not await is_active_chat(chat_id):
        return await message.reply_text(_reply(f"{_EM['warn']} ʙᴏᴛ ɪꜱ ɴᴏᴛ ᴀᴄᴛɪᴠᴇ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ."))

    if len(message.command) < 2:
        cur = await get_volume(chat_id)
        bar = "█" * (cur // 20) + "░" * (10 - cur // 20)
        return await message.reply_text(
            _reply(
                f"{_EM['queue']} <b>ᴄᴜʀʀᴇɴᴛ ᴠᴏʟᴜᴍᴇ</b>\n"
                f"[{bar}] <code>{cur}%</code>\n\n"
                f"{_EM['dot']} ᴜꜱᴀɢᴇ: /volume [0-200]"
            ),
            reply_markup=_close(),
        )

    try:
        vol = int(message.command[1])
    except ValueError:
        return await message.reply_text(_reply(f"{_EM['cross']} ᴘʀᴏᴠɪᴅᴇ ᴀ ɴᴜᴍʙᴇʀ 0-200."))

    if not 0 <= vol <= 200:
        return await message.reply_text(_reply(f"{_EM['cross']} ᴠᴏʟᴜᴍᴇ ᴍᴜꜱᴛ ʙᴇ 0-200."))

    try:
        assistant = await JARVIS.group_assistant(chat_id)
        client = JARVIS.pytgcalls[assistant]
        await client.change_volume_call(chat_id, vol)
    except Exception:
        return await message.reply_text(_reply(f"{_EM['cross']} ᴄᴀɴɴᴏᴛ ᴄʜᴀɴɢᴇ ᴠᴏʟᴜᴍᴇ. ꜱᴛʀᴇᴀᴍ ᴀᴄᴛɪᴠᴇ?"))

    await set_volume(chat_id, vol)
    bar = "█" * (vol // 20) + "░" * (10 - vol // 20)
    await message.reply_text(
        _reply(
            f"{_EM['queue']} <b>ᴠᴏʟᴜᴍᴇ ꜱᴇᴛ</b>\n"
            f"[{bar}] <code>{vol}%</code>\n\n"
            f"{_EM['dot']} ʙʏ : {message.from_user.mention}"
        ),
        reply_markup=_close(),
    )


# ── 24/7 MODE ────────────────────────────────────────────────────────────────
@app.on_message(
    filters.command(["247", "nonstop"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def k247(_, message: Message, lang, chat_id):
    on = await is_24_7(chat_id)
    if on:
        await disable_247(chat_id)
        await message.reply_text(
            _reply(
                f"{_EM['zap']} <b>24/7 ᴅɪꜱᴀʙʟᴇᴅ</b>\n"
                f"{_EM['dot']} ʙᴏᴛ ᴡɪʟʟ ʟᴇᴀᴠᴇ ᴡʜᴇɴ ǫᴜᴇᴜᴇ ɪꜱ ᴇᴍᴘᴛʏ.\n"
                f"{_EM['dot']} ʙʏ : {message.from_user.mention}"
            ),
            reply_markup=_close(),
        )
    else:
        await enable_247(chat_id)
        await message.reply_text(
            _reply(
                f"{_EM['fire']} <b>24/7 ᴍᴏᴅᴇ ᴇɴᴀʙʟᴇᴅ</b>\n"
                f"{_EM['dot']} ʙᴏᴛ ꜱᴛᴀʏꜱ ᴇᴠᴇɴ ᴡʜᴇɴ ǫᴜᴇᴜᴇ ɪꜱ ᴇᴍᴘᴛʏ.\n"
                f"{_EM['dot']} ʙʏ : {message.from_user.mention}"
            ),
            reply_markup=_close(),
        )


# ── ADMIN Inline Button Callbacks ─────────────────────────────────────────────
@app.on_callback_query(filters.regex(r"^ADMIN (Resume|Pause|Replay|Skip|Stop|Autoplay|Mute|Unmute)\|") & ~BANNED_USERS)
@ActualAdminCB
async def admin_control_cb(client, query: CallbackQuery, _):
    data = query.data
    parts = data.split("|", 1)
    action = parts[0].replace("ADMIN ", "").strip()
    try:
        chat_id = int(parts[1])
    except (IndexError, ValueError):
        return await query.answer("ɪɴᴠᴀʟɪᴅ ᴅᴀᴛᴀ", show_alert=True)

    if action == "Resume":
        await music_on(chat_id)
        await JARVIS.resume_stream(chat_id)
        await query.answer("▶ ʀᴇꜱᴜᴍᴇᴅ", show_alert=False)

    elif action == "Pause":
        await music_off(chat_id)
        await JARVIS.pause_stream(chat_id)
        await query.answer("⏸ ᴘᴀᴜꜱᴇᴅ", show_alert=False)

    elif action == "Skip":
        check = db.get(chat_id)
        if not check:
            return await query.answer("ɴᴏᴛʜɪɴɢ ɪɴ ǫᴜᴇᴜᴇ", show_alert=True)
        popped = None
        try:
            popped = check.pop(0)
            if popped:
                await auto_clean(popped)
        except Exception:
            return await query.answer("ᴄᴀɴɴᴏᴛ ꜱᴋɪᴘ", show_alert=True)
        if not check:
            await query.answer("ǫᴜᴇᴜᴇ ᴇᴍᴘᴛʏ — ꜱᴛᴏᴘᴘɪɴɢ", show_alert=False)
            return await JARVIS.stop_or_autoplay(chat_id, popped)
        await query.answer("⏭ ꜱᴋɪᴘᴘᴇᴅ", show_alert=False)
        check[0]["played"] = 0
        try:
            await JARVIS.skip_stream(chat_id, check[0]["file"])
        except Exception:
            pass

    elif action == "Stop":
        await JARVIS.stop_stream(chat_id)
        await query.answer("⏹ ꜱᴛᴏᴘᴘᴇᴅ", show_alert=False)
        try:
            await query.message.delete()
        except Exception:
            pass

    elif action == "Replay":
        check = db.get(chat_id)
        if not check:
            return await query.answer("ɴᴏᴛʜɪɴɢ ᴘʟᴀʏɪɴɢ", show_alert=True)
        try:
            file_path = check[0].get("file", "")
            dur = check[0].get("dur", "0:00")
            mode = check[0].get("streamtype", "audio")
            await JARVIS.seek_stream(chat_id, file_path, "0:00", dur, mode)
            check[0]["played"] = 0
            await query.answer("↻ ʀᴇᴘʟᴀʏɪɴɢ ꜰʀᴏᴍ ꜱᴛᴀʀᴛ", show_alert=False)
            from KHUSHI.core.call import _start_progress_timer
            _start_progress_timer(chat_id)
        except Exception:
            await query.answer("ʀᴇᴘʟᴀʏ ꜰᴀɪʟᴇᴅ", show_alert=True)

    elif action == "Autoplay":
        ap_on = await is_autoplay(chat_id)
        if ap_on:
            await autoplay_off(chat_id)
            new_state = False
            await query.answer("❌ ᴀᴜᴛᴏᴘʟᴀʏ ᴏꜰꜰ", show_alert=False)
        else:
            await autoplay_on(chat_id)
            new_state = True
            await query.answer("✅ ᴀᴜᴛᴏᴘʟᴀʏ ᴏɴ", show_alert=False)
        try:
            check = db.get(chat_id)
            if check:
                mystic = check[0].get("mystic")
                if mystic:
                    from KHUSHI.utils.inline import stream_markup, stream_markup_timer
                    from KHUSHI.utils.formatters import seconds_to_min as _s2m
                    lang = await get_lang(chat_id)
                    _lng = get_string(lang)
                    played = int(check[0].get("played", 0))
                    dur_str = check[0].get("dur", "0:00")
                    if played > 0:
                        played_min = _s2m(played)
                        btn = stream_markup_timer(_lng, chat_id, played_min, dur_str, autoplay_on=new_state)
                    else:
                        btn = stream_markup(_lng, chat_id, autoplay_on=new_state)
                    await mystic.edit_reply_markup(InlineKeyboardMarkup(btn))
        except Exception:
            pass

    elif action == "Mute":
        await JARVIS.mute_stream(chat_id)
        await query.answer("🔇 ᴍᴜᴛᴇᴅ", show_alert=False)

    elif action == "Unmute":
        await JARVIS.unmute_stream(chat_id)
        await query.answer("🔊 ᴜɴᴍᴜᴛᴇᴅ", show_alert=False)

    else:
        await query.answer("ᴜɴᴋɴᴏᴡɴ ᴀᴄᴛɪᴏɴ", show_alert=True)
