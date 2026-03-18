from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ChatAction, ParseMode
from ANNIEMUSIC import app
import pyshorteners
import httpx


shortener = pyshorteners.Shortener()


@app.on_message(filters.command("short"))
async def short_urls(bot: Client, message: Message):
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    if len(message.command) < 2:
        return await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>URL Shortener</b></blockquote>\n"
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> Please provide a link to shorten.\n"
            "<b>Example:</b> <code>/short https://example.com</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

    link = message.command[1]

    try:
        tiny = shortener.tinyurl.short(link)
        dagd = shortener.dagd.short(link)
        clck = shortener.clckru.short(link)

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 TinyURL", url=tiny)],
            [InlineKeyboardButton("🔗 Dagd", url=dagd), InlineKeyboardButton("🔗 Clck.ru", url=clck)],
        ])

        await message.reply_text(
            "<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>Here are your shortened URLs:</b></blockquote>",
            reply_markup=markup,
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        print(f"Shortener error: {e}")
        await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Failed to shorten the link.</b>\n"
            "It might already be shortened or invalid.</blockquote>",
            parse_mode=ParseMode.HTML
        )


@app.on_message(filters.command("unshort"))
async def unshort_url(bot: Client, message: Message):
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    if len(message.command) < 2:
        return await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>URL Unshortener</b></blockquote>\n"
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> Please provide a shortened link.\n"
            "<b>Example:</b> <code>/unshort https://bit.ly/example</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

    short_link = message.command[1]

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(short_link)
            final_url = str(response.url)

        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 View Final URL", url=final_url)]])
        await message.reply_text(
            f"<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>Unshortened URL:</b>\n<code>{final_url}</code></blockquote>",
            reply_markup=markup,
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        print(f"Unshortener error: {e}")
        await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Failed to unshorten the link.</b>\n"
            "It may be broken or invalid.</blockquote>",
            parse_mode=ParseMode.HTML
        )
