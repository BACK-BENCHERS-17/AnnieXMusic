from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import httpx
from ANNIEMUSIC import app

TRUTH_API = "https://api.truthordarebot.xyz/v1/truth"
DARE_API = "https://api.truthordarebot.xyz/v1/dare"


@app.on_message(filters.command("truth"))
async def get_truth(client: Client, message: Message):
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            res = await http.get(TRUTH_API)
        if res.status_code == 200:
            question = res.json().get("question", "No question found.")
            await message.reply_text(
                f"<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>Truth!</b></blockquote>\n"
                f"<blockquote><emoji id=\"5972072533833289156\">🔹</emoji> {question}</blockquote>",
                parse_mode=ParseMode.HTML
            )
        else:
            await message.reply_text(
                "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Failed to fetch a truth question.</b></blockquote>",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        print(f"Truth error: {e}")
        await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Error occurred</b> while fetching a truth question.</blockquote>",
            parse_mode=ParseMode.HTML
        )


@app.on_message(filters.command("dare"))
async def get_dare(client: Client, message: Message):
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            res = await http.get(DARE_API)
        if res.status_code == 200:
            question = res.json().get("question", "No question found.")
            await message.reply_text(
                f"<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>Dare!</b></blockquote>\n"
                f"<blockquote><emoji id=\"5972072533833289156\">🔹</emoji> {question}</blockquote>",
                parse_mode=ParseMode.HTML
            )
        else:
            await message.reply_text(
                "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Failed to fetch a dare question.</b></blockquote>",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        print(f"Dare error: {e}")
        await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Error occurred</b> while fetching a dare question.</blockquote>",
            parse_mode=ParseMode.HTML
        )
