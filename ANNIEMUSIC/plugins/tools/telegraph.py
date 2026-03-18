import os
import aiohttp

from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, Message
from ANNIEMUSIC.utils.inline import InlineKeyboardButton

from ANNIEMUSIC import app


async def upload_file(path: str):
    url = "https://catbox.moe/user/api.php"
    data = {"reqtype": "fileupload", "json": "true"}

    async with aiohttp.ClientSession() as session:
        with open(path, "rb") as f:
            form = aiohttp.FormData()
            form.add_field("fileToUpload", f, filename=os.path.basename(path))
            for k, v in data.items():
                form.add_field(k, v)

            async with session.post(url, data=form) as resp:
                if resp.status == 200:
                    result = await resp.text()
                    return True, result.strip()
                return False, f"Error: {resp.status} - {await resp.text()}"


@app.on_message(filters.command(["tgm", "tgt", "telegraph"]))
async def telegraph_handler(_, message: Message):
    if not message.reply_to_message or not (
        message.reply_to_message.photo
        or message.reply_to_message.video
        or message.reply_to_message.document
    ):
        return await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Media Uploader</b></blockquote>\n"
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> Please reply to an image/video/document to upload.</blockquote>",
            parse_mode=ParseMode.HTML
        )

    media = message.reply_to_message
    file = media.photo or media.video or media.document

    if file.file_size > 200 * 1024 * 1024:
        return await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>File too large.</b> Max size is 200MB.</blockquote>",
            parse_mode=ParseMode.HTML
        )

    status = await message.reply(
        "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>Downloading your media...</b></blockquote>",
        parse_mode=ParseMode.HTML
    )

    try:
        local_path = await media.download()
        await status.edit(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Uploading to Catbox...</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
        success, result = await upload_file(local_path)

        if success:
            await status.edit(
                "<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>Uploaded successfully!</b></blockquote>\n"
                f"<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>Link:</b> <code>{result}</code></blockquote>",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("📎 Open File", url=result)]]
                ),
                parse_mode=ParseMode.HTML
            )
        else:
            await status.edit(
                f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Upload failed:</b> <code>{result}</code></blockquote>",
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        await status.edit(
            f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Failed to process media:</b> <code>{e}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

    finally:
        if os.path.exists(local_path):
            os.remove(local_path)
