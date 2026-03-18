import asyncio
import os
from math import ceil
from typing import Dict, List, Tuple

import edge_tts
from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ParseMode
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from ANNIEMUSIC.utils.inline import InlineKeyboardButton

from ANNIEMUSIC import app

_voice_sessions: Dict[Tuple[int, int], str] = {}
_voices: List[dict] = []
_languages: List[str] = []
_VOICES_LOCK = asyncio.Lock()

PER_ROW = 4
PER_PAGE = 16
TMP_DIR = "/tmp"


async def _init_voices() -> None:
    global _voices, _languages
    if _voices:
        return

    async with _VOICES_LOCK:
        if _voices:
            return

        raw = await edge_tts.list_voices()
        _voices = [
            {
                "short_name": v["ShortName"],
                "locale": v["Locale"],
                "gender": v["Gender"],
            }
            for v in raw
        ]
        _languages = sorted({v["locale"].split("-", 1)[0] for v in _voices})


def _paginate(items: List[str], page: int) -> Tuple[List[str], int]:
    total = len(items)
    pages = max(1, ceil(total / PER_PAGE))
    page = max(1, min(page, pages))
    start = (page - 1) * PER_PAGE
    return items[start : start + PER_PAGE], pages


def _build_keyboard(
    items: List[str],
    step: str,
    extra: Dict[str, str],
    page: int,
) -> InlineKeyboardMarkup:
    page_items, total_pages = _paginate(items, page)

    rows: List[List[InlineKeyboardButton]] = []
    for i in range(0, len(page_items), PER_ROW):
        chunk = page_items[i : i + PER_ROW]
        rows.append(
            [
                InlineKeyboardButton(
                    text=item,
                    callback_data="tts:"
                    + f"s={step}"
                    + "".join(f"|{k}={v}" for k, v in extra.items())
                    + f"|p={page}|v={item}",
                )
                for item in chunk
            ]
        )

    nav: List[InlineKeyboardButton] = []
    if page > 1:
        nav.append(
            InlineKeyboardButton(
                "◀️ Prev",
                callback_data="tts:"
                + f"s={step}"
                + "".join(f"|{k}={v}" for k, v in extra.items())
                + f"|p={page-1}",
            )
        )
    if page < total_pages:
        nav.append(
            InlineKeyboardButton(
                "Next ▶️",
                callback_data="tts:"
                + f"s={step}"
                + "".join(f"|{k}={v}" for k, v in extra.items())
                + f"|p={page+1}",
            )
        )
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(rows)


def _session_key(chat_id: int, user_id: int) -> Tuple[int, int]:
    return chat_id, user_id


def _cleanup(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)


async def _synthesize(voice: str, text: str, out_path: str) -> None:
    comm = edge_tts.Communicate(text=text, voice=voice)
    await comm.save(out_path)


@app.on_message(filters.command("voices"))
async def cmd_voices(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Text to Speech</b></blockquote>\n"
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> Please provide the text to convert.\n"
            "<b>Example:</b> <code>/voices Hello world</code></blockquote>",
            parse_mode=ParseMode.HTML,
        )

    await _init_voices()

    text = message.text.split(" ", 1)[1]
    _voice_sessions[_session_key(message.chat.id, message.from_user.id)] = text

    kb = _build_keyboard(_languages, step="lang", extra={}, page=1)
    await message.reply_text(
        "<blockquote><emoji id=\"5449449325434266744\">❄️</emoji> <b>Step 1:</b> Select a language</blockquote>",
        reply_markup=kb,
        parse_mode=ParseMode.HTML,
    )


@app.on_message(filters.command("tts"))
async def cmd_tts(client: Client, message: Message):
    if len(message.command) < 3:
        return await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>TTS Usage:</b></blockquote>\n"
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <code>/tts &lt;voice_model&gt; &lt;text&gt;</code>\n"
            "Or try <code>/voices</code> for guided selection.</blockquote>",
            parse_mode=ParseMode.HTML,
        )

    await _init_voices()

    voice = message.command[1]
    text = message.text.split(" ", 2)[2]

    if not any(v["short_name"] == voice for v in _voices):
        return await message.reply_text(
            f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Unknown voice:</b> <code>{voice}</code>\n"
            f"Use <code>/voiceall</code> or <code>/voices</code> to browse voices.</blockquote>",
            parse_mode=ParseMode.HTML,
        )

    tmp = os.path.join(TMP_DIR, f"tts_{message.from_user.id}.mp3")
    try:
        await client.send_chat_action(message.chat.id, ChatAction.RECORD_AUDIO)
        await _synthesize(voice, text, tmp)

        await client.send_chat_action(message.chat.id, ChatAction.UPLOAD_AUDIO)
        await client.send_audio(
            chat_id=message.chat.id,
            audio=tmp,
            caption=f"<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>Voice:</b> <code>{voice}</code></blockquote>",
            reply_to_message_id=message.id,
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        print(f"[TTS DIRECT ERROR] {exc}")
        await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Failed to generate speech.</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    finally:
        _cleanup(tmp)


@app.on_callback_query(filters.regex(r"^tts:"))
async def cb_tts(client: Client, callback: CallbackQuery):
    data = callback.data[4:]
    parts = dict(p.split("=", 1) for p in data.split("|") if "=" in p)
    step = parts.get("s")
    page = int(parts.get("p", "1"))

    await _init_voices()

    key = _session_key(callback.message.chat.id, callback.from_user.id)
    text = _voice_sessions.get(key)
    if not text:
        return await callback.answer(
            "Session expired. Send /voices again.", show_alert=True
        )

    if step == "lang":
        if "v" not in parts:
            kb = _build_keyboard(_languages, "lang", {}, page)
            return await callback.message.edit_text(
                "<blockquote><emoji id=\"5449449325434266744\">❄️</emoji> <b>Step 1:</b> Select a language</blockquote>",
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
            )

        lang = parts["v"]
        regions = sorted(
            {
                v["locale"].split("-", 1)[1]
                for v in _voices
                if v["locale"].startswith(f"{lang}-")
            }
        )
        kb = _build_keyboard(regions, "region", {"l": lang}, 1)
        return await callback.message.edit_text(
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>Step 2:</b> Select a region</blockquote>",
            reply_markup=kb,
            parse_mode=ParseMode.HTML,
        )

    if step == "region":
        lang = parts["l"]

        if "v" not in parts:
            regions = sorted(
                {
                    v["locale"].split("-", 1)[1]
                    for v in _voices
                    if v["locale"].startswith(f"{lang}-")
                }
            )
            kb = _build_keyboard(regions, "region", {"l": lang}, page)
            return await callback.message.edit_text(
                "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>Step 2:</b> Select a region</blockquote>",
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
            )

        region = parts["v"]
        locale = f"{lang}-{region}"
        models = sorted([v["short_name"] for v in _voices if v["locale"] == locale])
        kb = _build_keyboard(models, "model", {"l": lang, "r": region}, 1)
        return await callback.message.edit_text(
            "<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>Step 3:</b> Choose a voice model</blockquote>",
            reply_markup=kb,
            parse_mode=ParseMode.HTML,
        )

    if step == "model":
        lang = parts["l"]
        region = parts["r"]

        if "v" not in parts:
            locale = f"{lang}-{region}"
            models = sorted([v["short_name"] for v in _voices if v["locale"] == locale])
            kb = _build_keyboard(models, "model", {"l": lang, "r": region}, page)
            return await callback.message.edit_text(
                "<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>Step 3:</b> Choose a voice model</blockquote>",
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
            )

        voice = parts["v"]
        tmp = os.path.join(TMP_DIR, f"tts_{callback.from_user.id}.mp3")
        try:
            await client.send_chat_action(callback.message.chat.id, ChatAction.RECORD_AUDIO)
            await _synthesize(voice, text, tmp)

            await client.send_chat_action(callback.message.chat.id, ChatAction.UPLOAD_AUDIO)
            await client.send_audio(
                chat_id=callback.message.chat.id,
                audio=tmp,
                caption=f"<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>Voice:</b> <code>{voice}</code></blockquote>",
                reply_to_message_id=callback.message.id,
                parse_mode=ParseMode.HTML,
            )
        except Exception as exc:
            print(f"[TTS CALLBACK ERROR] {exc}")
            await callback.message.reply_text(
                f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Generation failed:</b> <code>{exc}</code></blockquote>",
                parse_mode=ParseMode.HTML
            )
        finally:
            _cleanup(tmp)
            _voice_sessions.pop(key, None)
        return await callback.answer()

    await callback.answer("Unknown action. Send /voices again.", show_alert=True)


@app.on_message(filters.command("voiceall"))
async def cmd_voiceall(client: Client, message: Message):
    await _init_voices()

    lines = [
        f"{v['short_name']} — {v['locale']} ({v['gender']})" for v in _voices
    ]
    path = os.path.join(TMP_DIR, f"voices_{message.from_user.id}.txt")
    with open(path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines))

    await message.reply_document(
        document=path,
        caption="<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>List of all available voices</b></blockquote>",
        parse_mode=ParseMode.HTML
    )
    _cleanup(path)
