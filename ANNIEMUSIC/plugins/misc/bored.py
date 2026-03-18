from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from ANNIEMUSIC import app
import httpx

BORED_API_URL = "https://apis.scrimba.com/bored/api/activity"

@app.on_message(filters.command("bored"))
async def bored_command(client: Client, message: Message):
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            response = await http.get(BORED_API_URL)

        if response.status_code != 200:
            return await message.reply_text(
                "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Failed to fetch a fun activity.</b> Try again later.</blockquote>",
                parse_mode=ParseMode.HTML
            )

        data = response.json()
        activity = data.get("activity")

        if activity:
            await message.reply_text(
                f"<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>Feeling bored?</b></blockquote>\n"
                f"<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>Try this:</b> {activity}</blockquote>",
                parse_mode=ParseMode.HTML
            )
        else:
            await message.reply_text(
                "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>No activity found.</b></blockquote>",
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        print(f"Bored API error: {e}")
        await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Something went wrong</b> while fetching boredom busters.</blockquote>",
            parse_mode=ParseMode.HTML
        )
