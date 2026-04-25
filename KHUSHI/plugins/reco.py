"""KHUSHI — Song Recommendation Plugin: /reco, /rconfig."""

import asyncio
import html
import random

from pyrogram import enums, filters
from pyrogram.types import InlineKeyboardButton as _PlainBtn
from pyrogram.types import InlineKeyboardMarkup, Message

from KHUSHI.utils.inline import InlineKeyboardButton

from KHUSHI import app
from KHUSHI.core.mongo import mongodb
from KHUSHI.utils.decorators import KhushiGroupAdmin as AdminRightsCheck
from config import BANNED_USERS, SUPPORT_CHAT

_recodb = mongodb.reco_settings

_BRAND = ""

_EM = {
    "music":  '<emoji id="5463107823946717464">🎵</emoji>',
    "star":   '<emoji id="5039827436737397847">🌟</emoji>',
    "dot":    '<emoji id="5972072533833289156">🔹</emoji>',
    "zap":    '<emoji id="5042334757040423886">⚡️</emoji>',
    "mic":    '<emoji id="5933678317935791830">🎤</emoji>',
    "fire":   '<emoji id="5039644681583985437">🔥</emoji>',
}

# ── Massive Hindi/Punjabi-first song database ──────────────────────────────────
_GENRES: dict[str, list[str]] = {
    "bollywood": [
        "Tum Hi Ho", "Channa Mereya", "Ae Dil Hai Mushkil", "Raabta",
        "Kesariya Brahmastra", "Phir Bhi Tumko Chaahunga", "Bekhayali",
        "Hawayein", "Tera Ban Jaunga", "Pachtaoge", "Ik Vaari Aa",
        "Zaalima", "Kabira", "Tujhe Kitna Chahne Lage", "Enna Sona",
        "Ve Maahi", "Dil Diyan Gallan", "Sooraj Dooba Hai", "Ilahi",
        "Humdard", "Sab Tera", "Galliyan", "Teri Galiyan", "Judaai",
        "Agar Tum Saath Ho", "Khairiyat", "Arijit Singh Best Songs",
        "Phir Le Aaya Dil", "Tu Jaane Na", "Dooba Dooba Rehta Hoon",
        "Meri Aashiqui", "Meri Zindagi Hai Tu", "Tum Se Hi",
        "Tere Liye Prince", "Hasi Ban Gaye", "Hamari Adhuri Kahani",
        "Kalank Title Track", "Aashiqui 2 Tum Hi Ho", "Sun Saathiya",
        "Bahara", "Tere Mast Mast Do Nain", "Teri Meri Prem Kahani",
        "Jo Bhi Main", "Jeena Jeena", "O Sanam Lucky Ali",
    ],
    "punjabi": [
        "Lahore Guru Randhawa", "Morni Banke", "Kala Chashma",
        "Proper Patola", "Illegal Weapon", "Nit Khair Manga",
        "Jatt Da Muqabla", "Backbone", "Slowly Slowly Guru Randhawa",
        "Coka Sukh E", "Ban Ja Rani", "Lamberghini", "Naah Harrdy Sandhu",
        "Surma", "Nikle Currant", "Nach Punjaban", "Lover Diljit",
        "Yeah Baby Garry Sandhu", "Devil Karan Aujla", "Baller",
        "Chull", "Koi Vi Nahi", "Hasina Pagal Deewani",
        "Paani Paani Badshah", "Ik Tara Rabbi Shergill",
        "Jind Mahi Harshdeep Kaur", "Suit Suit", "Taare Ginn",
        "Burjkhalifa", "2 Phone", "Rolex Karan Aujla",
        "Ik Pal Ka Jeena", "Jatt Ludhiane Da", "Ikk Kudi Udta Punjab",
        "Dilnasheen", "Reh Ja Amrinder Gill", "Jinke Liye Neha Kakkar",
        "Tera Ghata Gajendra Verma", "Dildarian", "Sajjna",
        "Nakhre", "Chitta Kurta", "High End Yaarian Jasmine Sandlas",
        "Kali Teri Gut", "Vaaste Dhvani Bhanushali Punjab Version",
    ],
    "romantic": [
        "Tum Hi Ho", "Pehla Nasha", "Aankhon Mein Teri", "Main Shayar Toh Nahin",
        "Dil Ko Maine Di Kasam", "Tera Zikr", "Zindagi Do Pal Ki",
        "Kuch Kuch Hota Hai Title", "O Heeriye", "Sau Dard Hain",
        "Wanna Be Meri Girlfriend", "Kuch Is Tarah Atif Aslam",
        "Woh Lamhe Atif Aslam", "Tera Hone Laga Hoon",
        "Meri Zindagi Hai Tu", "Main Rang Sharbaton Ka",
        "Raabta Deepika", "Enna Sona Arijit", "Hasi Ban Gaye Shreya",
        "Kya Mujhe Pyaar Hai KK", "Aankhon Mein Teri KK",
        "Tu Hi Mera Dil Hans Raj Hans", "Sooraj Ki Baahon Mein",
        "Ek Ladki Ko Dekha To Aisa Laga Old", "Yeh Dil Deewana",
        "Mere Yaar Ki Shaadi Hai", "Dil Ne Yeh Kaha Hai",
    ],
    "sad": [
        "Bekhayali", "Pachtaoge", "Ik Vaari Aa Rockstar", "Main Agar Saamne",
        "Judaai Atif Aslam", "Phir Mohabbat Murda", "Jo Bhi Main Rockstar",
        "Tadap Tadap Ke Devdas", "Dil Ibadat KK", "Tera Hone Laga Hoon",
        "Tu Hi Mera Dil", "Woh Lamhe", "Channa Mereya", "Kya Hua Tera Wada",
        "Mere Bina Creed", "Dil Ko Karar Aaya", "Yaad Piya Ki Aane Lagi Neha",
        "Neele Neele Ambar Par Old", "Teri Yaad Atif Aslam",
        "Kal Ho Naa Ho Title", "Ae Dil Hai Mushkil Title",
        "Ae Zindagi Gale Laga Le", "Kyon Ki Atif Aslam",
        "Mujhse Dosti Karoge Title", "Pyaar Tune Kya Kiya",
        "Tere Bina Jiya Na Jaaye", "Alvida Arijit Singh",
    ],
    "party": [
        "Balam Pichkari", "Desi Beat Bodyguard", "Sheila Ki Jawani",
        "Munni Badnaam", "Fevicol Se", "Tune Maari Entriyaan",
        "Abhi Toh Party Shuru Hui Hai", "Amplifier Imran Khan",
        "Nachde Ne Saare", "Gallan Goodiyaan", "Kar Gayi Chull",
        "Alcoholia", "Husn Hai Suhana", "Dil Luteya", "London Thumakda",
        "Badtameez Dil", "Character Dheela", "Dilbar Dilbar New",
        "Kamariya Mitron", "Slow Motion Bharat",
        "Psycho Saiyaan Saaho", "Genda Phool Badshah",
        "Kala Chashma Baar Baar Dekho", "Naagin Dance",
        "Sauda Khara Khara", "Proper Patola Party",
        "Break Up Party Song", "Dua Karo 83 Film",
    ],
    "hiphop": [
        "Mere Gully Mein Gully Boy", "DIVINE Mirchi", "Emiway Machayenge",
        "Raftaar Black White", "Badshah Paagal", "MC Stan Insaan",
        "KR$NA Asal Mein", "Seedhe Maut Nanchaku", "Yo Yo Honey Singh Blue Eyes",
        "Naezy Aafat", "Gully Boy Asli Hip Hop", "Sher Aaya Sher Gully Boy",
        "Azadi Gully Boy", "BloodClaat Remix Divine", "Bhai Bhai Salman",
        "Dooriyan Badh Gayi AP Dhillon", "With You AP Dhillon",
        "Excuses AP Dhillon", "Arjan Vailly Animal", "Nseeb Karan Aujla",
        "Hundred Proof Karan Aujla", "Not Ur Friend Karan Aujla",
        "47 Karan Aujla", "23 Karan Aujla", "Softly Karan Aujla",
    ],
    "lofi": [
        "Tum Hi Ho Lofi Remix", "Bekhayali Lofi", "Kesariya Lofi Mix",
        "Slow Reverb Hindi Songs", "Channa Mereya Lofi",
        "Pachtaoge Lofi Version", "Raabta Lofi", "Zaalima Lofi Mix",
        "Night Drive Lofi Hindi", "Arijit Singh Lofi Mix Playlist",
        "Bollywood Lofi Chill", "1AM Lofi Bollywood Mix",
        "Coffee Shop Lofi Hindi", "Study Music Hindi Lofi",
        "Kho Gaye Hum Kahan Lofi", "Tera Hua Lofi", "Vaaste Lofi",
        "Bulleya Lofi Mix", "Nashe Si Chadh Gayi Lofi",
        "Sadda Haq Lofi Rockstar",
    ],
    "devotional": [
        "Hanuman Chalisa Shankar Mahadevan", "Jai Shri Ram",
        "Om Namah Shivaya", "Gayatri Mantra", "Wah Wah Ramji",
        "Shree Ram Stuti", "Jai Ganesh Deva", "Allah Ke Bande Kailash",
        "Ik Onkar Waheguru", "Ardas Bhai Gurbani",
        "Deh Shiva Bar Mohe", "Satnam Waheguru Simran",
        "Mahamrityunjaya Mantra", "Om Jai Jagdish Hare Aarti",
        "Teri Mitti Kesari Patriotic",
    ],
    "retro": [
        "Ek Ladki Ko Dekha Roop Kumar Rathod", "Bahut Pyaar Karte Hain",
        "Tere Bina Zindagi Se Koi", "Dil Dhadakne Do Old",
        "Kabhi Kabhi Amitabh", "Mere Mehboob Qayamat Hogi",
        "Yeh Dosti Hum Nahi Todenge", "Aanewala Pal Jaane Wala",
        "Gulabi Aankhen", "Ajeeb Dastan Hai Yeh", "Lag Ja Gale",
        "Tere Bina Jiya Na Jaaye Old", "Pyar Kiya To Darna Kya",
        "Teri Aankhon Mein Andha Koi", "Wada Karo Nahin Chodoge",
        "Mere Naina Sawan Bhadon", "Aapki Nazron Ne Samjha",
        "Dum Maro Dum", "O Mere Dil Ke Chain",
    ],
}

# Flat pool of popular Hindi/Punjabi songs for random suggestions
_DEFAULT_POOL = (
    _GENRES["bollywood"][:15]
    + _GENRES["punjabi"][:15]
    + _GENRES["romantic"][:10]
    + _GENRES["sad"][:8]
    + _GENRES["party"][:8]
)

_reco_cache: dict[int, dict] = {}

# ── Per-message session for the "Load More" button ─────────────────────────────
# Keyed by sent-message-id. Each entry tracks the chat, the original query (if
# any), the genre fallback, every song already shown, and the running list of
# all picks so we can rebuild the message after each Load More click.
_reco_session: dict[int, dict] = {}
_RECO_MAX_PICKS = 12  # Stop expanding after this many songs in one message


def _reply(text: str) -> str:
    return f"<blockquote>{text}</blockquote>"


def _build_reco_text(picks: list[str], query: str | None, genre: str) -> str:
    safe_picks = [html.escape(s) for s in picks]
    lines = "\n".join(
        f"{_EM['dot']} <b>{i+1}.</b> <code>{s}</code>"
        for i, s in enumerate(safe_picks)
    )
    header = (
        f"{_EM['fire']} <b>˹ ꜱᴏɴɢ ꜱᴜɢɢᴇꜱᴛɪᴏɴꜱ ˼</b>\n"
        + (
            f"{_EM['mic']} ꜰᴏʀ: <b>{html.escape(query)}</b>\n"
            if query
            else f"{_EM['zap']} ɢᴇɴʀᴇ: <code>{genre}</code>\n"
        )
        + "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        f"{lines}\n\n"
        f"{_EM['star']} ᴛᴀᴘ ᴀɴʏ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴘʟᴀʏ ɪɴsᴛᴀɴᴛʟʏ!"
    )
    return _reply(header)


def _build_reco_markup(picks: list[str], can_load_more: bool) -> InlineKeyboardMarkup:
    rows = []
    for s in picks:
        label = s[:35] + "…" if len(s) > 35 else s
        rows.append([InlineKeyboardButton(
            label, callback_data=f"rp:{s[:40]}", style="primary",
        )])
    bottom = []
    if can_load_more:
        bottom.append(InlineKeyboardButton(
            f"{_EM['zap']} ʟᴏᴀᴅ ᴍᴏʀᴇ", callback_data="rml:0", style="success",
        ))
    bottom.append(InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close", style="danger"))
    rows.append(bottom)
    rows.append([InlineKeyboardButton("˹ꜱᴜᴘᴘᴏʀᴛ˼", url=_sc_url(), style="success")])
    return InlineKeyboardMarkup(rows)


def _build_plain_markup(picks: list[str]) -> InlineKeyboardMarkup:
    rows = [
        [_PlainBtn(s[:35] + "…" if len(s) > 35 else s, callback_data=f"rp:{s[:40]}")]
        for s in picks
    ]
    rows.append([
        _PlainBtn("˹ꜱᴜᴘᴘᴏʀᴛ˼", url=_sc_url()),
        _PlainBtn("˹ᴄʟᴏꜱᴇ˼", callback_data="close"),
    ])
    return InlineKeyboardMarkup(rows)


async def _generate_more_picks(query: str | None, genre: str, exclude: set[str], n: int) -> list[str]:
    """Return up to n new song suggestions excluding any in `exclude`."""
    new_picks: list[str] = []
    if query:
        try:
            yt_picks = await _yt_related(query, n + 4)
            for p in yt_picks:
                if p not in exclude and p not in new_picks:
                    new_picks.append(p)
                    if len(new_picks) >= n:
                        return new_picks
        except Exception:
            pass
    pool = _GENRES.get(genre, _DEFAULT_POOL)
    avail = [s for s in pool if s not in exclude and s not in new_picks]
    if avail:
        random.shuffle(avail)
        for s in avail:
            new_picks.append(s)
            if len(new_picks) >= n:
                break
    return new_picks


def _sc_url() -> str:
    return SUPPORT_CHAT if SUPPORT_CHAT.startswith("http") else f"https://t.me/{SUPPORT_CHAT.lstrip('@')}"


async def _get_rconfig(chat_id: int) -> dict:
    if chat_id in _reco_cache:
        return _reco_cache[chat_id]
    doc = await _recodb.find_one({"chat_id": chat_id})
    cfg = doc if doc else {"chat_id": chat_id, "genre": "bollywood", "count": 5}
    _reco_cache[chat_id] = cfg
    return cfg


async def _save_rconfig(chat_id: int, data: dict):
    _reco_cache[chat_id] = data
    await _recodb.update_one({"chat_id": chat_id}, {"$set": data}, upsert=True)


_RECO_SKIP_KW = {
    "jukebox", "playlist", "non stop", "nonstop", "mashup",
    "top 10", "top 20", "top 50", "compilation", "jhankar",
    "ringtone", "full album", "all songs", "audio jukebox",
    "video jukebox", "best of", "hits of", "back to back",
}


async def _yt_related(query: str, n: int) -> list[str]:
    """Search YouTube for songs related to `query` and return their titles."""
    from youtubesearchpython.__future__ import VideosSearch
    titles: list[str] = []
    for suffix in [f"songs like {query}", f"{query} similar songs"]:
        try:
            res = await VideosSearch(suffix, limit=12).next()
            for item in (res.get("result") or []):
                title = item.get("title", "")
                dur = item.get("duration") or ""
                if not title or not dur:
                    continue
                if any(kw in title.lower() for kw in _RECO_SKIP_KW):
                    continue
                # Skip if it's literally the queried song itself
                if query.lower()[:15] in title.lower():
                    continue
                if title not in titles:
                    titles.append(title)
                if len(titles) >= n:
                    return titles
        except Exception:
            pass
    return titles


@app.on_message(
    filters.command(["reco", "recommend", "suggest"], prefixes=["/", ".", "!"]) & ~BANNED_USERS
)
async def reco_cmd(client, message: Message):
    try:
        await message.delete()
    except Exception:
        pass

    chat_id = message.chat.id
    query = message.text.split(None, 1)[1].strip() if len(message.command) > 1 else None

    cfg = await _get_rconfig(chat_id)
    count = min(cfg.get("count", 5), 6)
    genre = cfg.get("genre", "bollywood")

    picks: list[str] = []

    if query:
        # Try YouTube-based related song search first
        loading = await app.send_message(
            chat_id,
            f"<blockquote>{_EM['zap']} ꜱᴇᴀʀᴄʜɪɴɢ ʀᴇʟᴀᴛᴇᴅ ꜱᴏɴɢꜱ…</blockquote>",
        )
        picks = await _yt_related(query, count)
        try:
            await loading.delete()
        except Exception:
            pass

    if not picks:
        # Fallback: local genre pool (also used when no query given)
        if query:
            # Try keyword matching against local DB
            q_lower = query.lower()
            songs_pool: list[str] = []
            for g, songs in _GENRES.items():
                if g in q_lower or any(
                    any(w in s.lower() for w in q_lower.split() if len(w) > 2)
                    for s in songs
                ):
                    songs_pool.extend(songs)
            if not songs_pool:
                songs_pool = _GENRES.get(genre, _DEFAULT_POOL)
        else:
            songs_pool = _GENRES.get(genre, _DEFAULT_POOL)

        picks = random.sample(songs_pool, min(count, len(songs_pool)))

    can_more = len(picks) < _RECO_MAX_PICKS
    text = _build_reco_text(picks, query, genre)
    markup = _build_reco_markup(picks, can_load_more=can_more)

    try:
        sent = await message.reply_text(
            text, reply_markup=markup, parse_mode=enums.ParseMode.HTML,
        )
    except Exception:
        try:
            sent = await message.reply_text(
                text, reply_markup=_build_plain_markup(picks),
                parse_mode=enums.ParseMode.HTML,
            )
        except Exception:
            return

    # Remember this message so the Load More button can grow it later
    _reco_session[sent.id] = {
        "chat_id": chat_id,
        "query": query,
        "genre": genre,
        "shown": set(picks),
        "all_picks": list(picks),
    }

    # Auto-delete after 120 seconds (also drops the session entry)
    async def _auto_del():
        await asyncio.sleep(120)
        try:
            await sent.delete()
        except Exception:
            pass
        _reco_session.pop(sent.id, None)

    asyncio.create_task(_auto_del())


# ── Load-More callback ────────────────────────────────────────────────────────
@app.on_callback_query(filters.regex(r"^rml:") & ~BANNED_USERS)
async def reco_more_cb(client, query):
    msg = query.message
    sess = _reco_session.get(msg.id)
    if not sess:
        return await query.answer(
            "Session expired — send /reco again", show_alert=True
        )

    if len(sess["all_picks"]) >= _RECO_MAX_PICKS:
        return await query.answer("Reached the maximum suggestions!", show_alert=True)

    await query.answer("Fetching more…")

    needed = min(4, _RECO_MAX_PICKS - len(sess["all_picks"]))
    new_picks = await _generate_more_picks(
        sess.get("query"), sess.get("genre", "bollywood"),
        sess["shown"], needed,
    )
    if not new_picks:
        return await query.answer("No more suggestions left.", show_alert=True)

    sess["all_picks"].extend(new_picks)
    sess["shown"].update(new_picks)

    can_more = len(sess["all_picks"]) < _RECO_MAX_PICKS
    new_text = _build_reco_text(
        sess["all_picks"], sess.get("query"), sess.get("genre", "bollywood"),
    )
    new_markup = _build_reco_markup(sess["all_picks"], can_load_more=can_more)
    try:
        await msg.edit_text(
            new_text, reply_markup=new_markup, parse_mode=enums.ParseMode.HTML,
        )
    except Exception:
        try:
            await msg.edit_text(
                new_text, reply_markup=_build_plain_markup(sess["all_picks"]),
                parse_mode=enums.ParseMode.HTML,
            )
        except Exception:
            pass


# ── Public helper used by core/call.py when the queue ends ────────────────────
async def auto_reco_on_queue_end(chat_id: int, last_title: str | None) -> None:
    """Send a /reco-style message in `chat_id` based on the last played song.

    Called by `KHUSHI.core.call.Call.stop_or_autoplay` when autoplay is OFF
    and the queue has just been exhausted, so the user gets fresh suggestions
    without having to type /reco manually.
    """
    try:
        cfg = await _get_rconfig(chat_id)
        genre = cfg.get("genre", "bollywood")
        count = min(cfg.get("count", 5), 6)

        picks: list[str] = []
        query_used = (last_title or "").strip() or None

        if query_used:
            try:
                picks = await _yt_related(query_used, count)
            except Exception:
                picks = []

        if not picks:
            pool = _GENRES.get(genre, _DEFAULT_POOL)
            picks = random.sample(pool, min(count, len(pool)))

        if not picks:
            return

        text_body = _build_reco_text(picks, query_used, genre)
        # Prepend a small "queue ended" header so users know why this appeared
        intro = (
            f"<blockquote>{_EM['fire']} <b>ǫᴜᴇᴜᴇ ᴇɴᴅᴇᴅ — ʜᴇʀᴇ'ꜱ ᴡʜᴀᴛ ᴛᴏ ᴘʟᴀʏ ɴᴇxᴛ</b></blockquote>\n"
        )
        full_text = intro + text_body
        markup = _build_reco_markup(picks, can_load_more=len(picks) < _RECO_MAX_PICKS)

        try:
            sent = await app.send_message(
                chat_id, full_text, reply_markup=markup,
                parse_mode=enums.ParseMode.HTML,
            )
        except Exception:
            sent = await app.send_message(
                chat_id, full_text, reply_markup=_build_plain_markup(picks),
                parse_mode=enums.ParseMode.HTML,
            )

        _reco_session[sent.id] = {
            "chat_id": chat_id,
            "query": query_used,
            "genre": genre,
            "shown": set(picks),
            "all_picks": list(picks),
        }

        async def _auto_del():
            await asyncio.sleep(180)
            try:
                await sent.delete()
            except Exception:
                pass
            _reco_session.pop(sent.id, None)

        asyncio.create_task(_auto_del())
    except Exception:
        # Never let auto-reco break stream cleanup
        pass


@app.on_message(
    filters.command(["rconfig"], prefixes=["/", ".", "!"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck
async def rconfig_cmd(client, message: Message, lang, chat_id):
    args = message.command[1:]
    cfg = await _get_rconfig(chat_id)

    if not args:
        genre = cfg.get("genre", "bollywood")
        count = cfg.get("count", 5)
        genres_list = "  ".join(f"<code>{g}</code>" for g in _GENRES)
        return await message.reply_text(
            _reply(
                f"{_EM['fire']} <b>˹ ʀᴇᴄᴏ ᴄᴏɴꜰɪɢ ˼</b>\n\n"
                f"{_EM['dot']} ɢᴇɴʀᴇ: <code>{genre}</code>\n"
                f"{_EM['dot']} ᴄᴏᴜɴᴛ: <code>{count}</code>\n\n"
                f"<b>ᴀᴠᴀɪʟᴀʙʟᴇ:</b>\n{genres_list}\n\n"
                f"{_EM['zap']} <code>/rconfig genre [name]</code>\n"
                f"{_EM['zap']} <code>/rconfig count [1-6]</code>"
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close", style="danger"),
            ]]),
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
                    InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close", style="danger"),
                ]]),
            )
        cfg["genre"] = new_genre
        await _save_rconfig(chat_id, cfg)
        return await message.reply_text(
            _reply(
                f"{_EM['fire']} ɢᴇɴʀᴇ ꜱᴇᴛ → <code>{new_genre}</code>\n"
                f"{_EM['dot']} ʙʏ: {message.from_user.mention}"
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close", style="danger"),
            ]]),
        )

    if sub == "count" and len(args) >= 2:
        try:
            new_count = max(1, min(int(args[1]), 6))
        except ValueError:
            return await message.reply_text(
                _reply(f"❌ ᴘʀᴏᴠɪᴅᴇ ᴀ ɴᴜᴍʙᴇʀ <code>1–6</code>."),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close", style="danger"),
                ]]),
            )
        cfg["count"] = new_count
        await _save_rconfig(chat_id, cfg)
        return await message.reply_text(
            _reply(
                f"{_EM['fire']} ᴄᴏᴜɴᴛ ꜱᴇᴛ → <code>{new_count}</code>\n"
                f"{_EM['dot']} ʙʏ: {message.from_user.mention}"
            ),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close", style="danger"),
            ]]),
        )

    await message.reply_text(
        _reply(
            f"{_EM['zap']} ᴜꜱᴇ:\n"
            f"{_EM['dot']} <code>/rconfig genre [name]</code>\n"
            f"{_EM['dot']} <code>/rconfig count [1-6]</code>"
        ),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("˹ᴄʟᴏꜱᴇ˼", callback_data="close"),
        ]]),
    )
