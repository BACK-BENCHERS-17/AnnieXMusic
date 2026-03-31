"""KHUSHI — Song Recommendation Plugin: /reco, /rconfig."""

import random

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from KHUSHI import app
from KHUSHI.core.mongo import mongodb
from KHUSHI.utils.decorators import KhushiAdminCheck as AdminRightsCheck
from config import BANNED_USERS, SUPPORT_CHAT

_recodb = mongodb.reco_settings

_BRAND = (
    "<emoji id='5042192219960771668'>🧸</emoji>"
    "<emoji id='5210820276748566172'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5213301251722203632'>🔤</emoji>"
    "<emoji id='5211032856154885824'>🔤</emoji>"
    "<emoji id='5213337333742454261'>🔤</emoji>"
)

_EM = {
    "music":  "<emoji id='5463107823946717464'>🎵</emoji>",
    "star":   "<emoji id='5041975203853239332'>🎁</emoji>",
    "dot":    "<emoji id='5972072533833289156'>🔹</emoji>",
    "zap":    "<emoji id='5042334757040423886'>⚡️</emoji>",
}

_GENRES = {
    "pop":     ["Shape of You", "Blinding Lights", "Stay", "Levitating", "Watermelon Sugar"],
    "hiphop":  ["God's Plan", "Rockstar", "HUMBLE.", "Sicko Mode", "Lucid Dreams"],
    "lofi":    ["lofi hip hop radio", "Chill Lofi Study", "Coffee Shop Lofi", "Night Lofi", "Rainy Lofi"],
    "rock":    ["Bohemian Rhapsody", "Hotel California", "Smells Like Teen Spirit", "Back In Black", "Stairway to Heaven"],
    "indie":   ["Sunflower", "Sofia", "Electric Feel", "Do I Wanna Know?", "Mr. Brightside"],
    "rnb":     ["Blinding Lights", "Save Your Tears", "Good Days", "Golden", "Peaches"],
    "edm":     ["Titanium", "Levels", "Animals", "Lean On", "Alone"],
    "classic": ["Beethoven 5th", "Moonlight Sonata", "Fur Elise", "Canon in D", "Claire de Lune"],
    "bollywood": ["Tum Hi Ho", "Channa Mereya", "Kal Ho Naa Ho", "Ae Dil Hai Mushkil", "Raabta"],
}

_reco_cache: dict[int, dict] = {}


def _reply(text: str) -> str:
    return f"<blockquote>{_BRAND}</blockquote>\n\n<blockquote>{text}</blockquote>"


def _close_kb():
    _sc = SUPPORT_CHAT if SUPPORT_CHAT.startswith("http") else f"https://t.me/{SUPPORT_CHAT.lstrip('@')}"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("˹ꜱᴜᴘᴘᴏʀᴛ˼", url=_sc),
        InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close"),
    ]])


async def _get_rconfig(chat_id: int) -> dict:
    if chat_id in _reco_cache:
        return _reco_cache[chat_id]
    doc = await _recodb.find_one({"chat_id": chat_id})
    cfg = doc if doc else {"chat_id": chat_id, "genre": "pop", "count": 5}
    _reco_cache[chat_id] = cfg
    return cfg


async def _save_rconfig(chat_id: int, data: dict):
    _reco_cache[chat_id] = data
    await _recodb.update_one({"chat_id": chat_id}, {"$set": data}, upsert=True)


@app.on_message(
    filters.command(["reco", "recommend"], prefixes=["/", ".", "!"]) & ~BANNED_USERS
)
async def reco_cmd(client, message: Message):
    chat_id = message.chat.id
    query = message.text.split(None, 1)[1].strip() if len(message.command) > 1 else None

    cfg = await _get_rconfig(chat_id)
    count = cfg.get("count", 5)
    genre = cfg.get("genre", "pop")

    if query:
        songs_pool = []
        q_lower = query.lower()
        for g, songs in _GENRES.items():
            if g in q_lower or any(q_lower in s.lower() for s in songs):
                songs_pool.extend(songs)
        if not songs_pool:
            songs_pool = _GENRES.get(genre, _GENRES["pop"])
    else:
        songs_pool = _GENRES.get(genre, _GENRES["pop"])

    picks = random.sample(songs_pool, min(count, len(songs_pool)))

    lines = "\n".join(
        f"{_EM['dot']} <code>{i+1}.</code> <b>{s}</b>" for i, s in enumerate(picks)
    )
    caption = (
        f"{_EM['music']} <b>sᴏɴɢ ʀᴇᴄᴏᴍᴍᴇɴᴅᴀᴛɪᴏɴs</b>\n"
        + (f"{_EM['zap']} ǫᴜᴇʀʏ: <code>{query}</code>\n" if query else f"{_EM['zap']} ɢᴇɴʀᴇ: <code>{genre}</code>\n")
        + f"\n{lines}\n\n"
        f"{_EM['star']} ᴜꜱᴇ <code>/play [song name]</code> ᴛᴏ ᴘʟᴀʏ ᴀɴʏ!"
    )

    await message.reply_text(
        _reply(caption),
        reply_markup=_close_kb(),
    )


@app.on_message(
    filters.command(["rconfig"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def rconfig_cmd(client, message: Message, lang, chat_id):
    args = message.command[1:]
    cfg = await _get_rconfig(chat_id)

    if not args:
        genre = cfg.get("genre", "pop")
        count = cfg.get("count", 5)
        genres_list = " | ".join(f"<code>{g}</code>" for g in _GENRES)
        return await message.reply_text(
            _reply(
                f"{_EM['music']} <b>ʀᴇᴄᴏ ᴄᴏɴꜰɪɢ</b>\n\n"
                f"{_EM['dot']} ɢᴇɴʀᴇ: <code>{genre}</code>\n"
                f"{_EM['dot']} ᴄᴏᴜɴᴛ: <code>{count}</code>\n\n"
                f"<b>ᴀᴠᴀɪʟᴀʙʟᴇ ɢᴇɴʀᴇs:</b>\n{genres_list}\n\n"
                f"{_EM['zap']} ᴜꜱᴇ: <code>/rconfig genre [name]</code> ᴏʀ <code>/rconfig count [1-10]</code>"
            ),
            reply_markup=_close_kb(),
        )

    sub = args[0].lower()
    if sub == "genre" and len(args) >= 2:
        new_genre = args[1].lower()
        if new_genre not in _GENRES:
            return await message.reply_text(
                _reply(
                    f"❌ ɪɴᴠᴀʟɪᴅ ɢᴇɴʀᴇ.\n"
                    f"{_EM['dot']} ᴀᴠᴀɪʟᴀʙʟᴇ: {', '.join(_GENRES.keys())}"
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close"),
                ]]),
            )
        cfg["genre"] = new_genre
        await _save_rconfig(chat_id, cfg)
        return await message.reply_text(
            _reply(
                f"{_EM['music']} ɢᴇɴʀᴇ ꜱᴇᴛ ᴛᴏ <code>{new_genre}</code>\n"
                f"{_EM['dot']} ʙʏ: {message.from_user.mention}"
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close"),
            ]]),
        )

    if sub == "count" and len(args) >= 2:
        try:
            new_count = max(1, min(int(args[1]), 10))
        except ValueError:
            return await message.reply_text(
                _reply("❌ ᴘʀᴏᴠɪᴅᴇ ᴀ ɴᴜᴍʙᴇʀ ʙᴇᴛᴡᴇᴇɴ <code>1-10</code>."),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close"),
                ]]),
            )
        cfg["count"] = new_count
        await _save_rconfig(chat_id, cfg)
        return await message.reply_text(
            _reply(
                f"{_EM['music']} ʀᴇᴄᴏ ᴄᴏᴜɴᴛ ꜱᴇᴛ ᴛᴏ <code>{new_count}</code>\n"
                f"{_EM['dot']} ʙʏ: {message.from_user.mention}"
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close"),
            ]]),
        )

    await message.reply_text(
        _reply(
            f"{_EM['zap']} ᴜꜱᴇ:\n"
            f"{_EM['dot']} <code>/rconfig genre [name]</code>\n"
            f"{_EM['dot']} <code>/rconfig count [1-10]</code>"
        ),
        reply_markup=_close_kb(),
    )
