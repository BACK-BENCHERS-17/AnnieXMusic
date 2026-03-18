from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from ANNIEMUSIC import app
from gpytranslate import Translator

translator = Translator()


@app.on_message(filters.command("tr"))
async def translate(_, message: Message):
    reply = message.reply_to_message

    if not reply or not (reply.text or reply.caption):
        return await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Translator</b></blockquote>\n"
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> Please reply to a text or caption to translate.</blockquote>",
            parse_mode=ParseMode.HTML
        )

    content = reply.text or reply.caption

    try:
        arg = message.text.split(maxsplit=1)[1].lower()
        if "//" in arg:
            source_lang, target_lang = arg.split("//")
        else:
            source_lang = await translator.detect(content)
            target_lang = arg
    except IndexError:
        source_lang = await translator.detect(content)
        target_lang = "en"

    try:
        result = await translator(content, sourcelang=source_lang, targetlang=target_lang)
        await message.reply_text(
            f"<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>Translated:</b> <code>{source_lang}</code> ➜ <code>{target_lang}</code></blockquote>\n"
            f"<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> {result.text}</blockquote>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.reply_text(
            f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Translation failed:</b> <code>{str(e)}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
