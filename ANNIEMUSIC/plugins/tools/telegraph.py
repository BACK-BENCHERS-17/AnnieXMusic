import os
import aiohttp

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

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
        return await message.reply_text("📎 <b>Please reply to an image/video/document to upload.</b>")

    media = message.reply_to_message
    file = media.photo or media.video or media.document

    if file.file_size > 200 * 1024 * 1024:
        return await message.reply_text("⚠️ <b>File too large. Max size is 200MB.</b>")

    status = await message.reply("🔄 <b>Downloading your media...</b>")

    try:
        local_path = await media.download()
        await status.edit("⬆️ <b>Uploading to Telegraph...</b>")
        success, result = await upload_file(local_path)

        if success:
            await status.edit(
                f"✅ <b>Uploaded successfully!</b>\n🔗 [Click to View]({result})",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("📎 Open Telegraph", url=result)]]
                ),
            )
        else:
            await status.edit(f"❌ <b>Upload failed:</b>\n`{result}`")

    except Exception as e:
        await status.edit(f"❌ <b>Failed to process media:</b>\n`{e}`")

    finally:
        if os.path.exists(local_path):
            os.remove(local_path)
