import os
import aiohttp
import aiofiles

from config import DEEP_API
from ANNIEMUSIC import app
from pyrogram import filters
from pyrogram.types import Message


async def download_from_url(path: str, url: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                async with aiofiles.open(path, mode="wb") as f:
                    await f.write(await resp.read())
                return path
    return None


async def post_file(url: str, file_path: str, headers: dict):
    async with aiohttp.ClientSession() as session:
        with open(file_path, 'rb') as f:
            form = aiohttp.FormData()
            form.add_field('image', f, filename=os.path.basename(file_path), content_type='application/octet-stream')

            async with session.post(url, data=form, headers=headers) as resp:
                return await resp.json()


async def post_data(url: str, data: dict, headers: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, headers=headers) as resp:
            return await resp.json()


@app.on_message(filters.command("upscale"))
async def upscale_image(_, message: Message):
    from pyrogram.enums import ParseMode
    if not DEEP_API:
        return await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Missing DeepAI API key.</b></blockquote>",
            parse_mode=ParseMode.HTML
        )

    reply = message.reply_to_message
    if not reply or not reply.photo:
        return await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Image Upscaler</b></blockquote>\n"
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> Please reply to an image.</blockquote>",
            parse_mode=ParseMode.HTML
        )

    status = await message.reply_text(
        "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>Upscaling image...</b></blockquote>",
        parse_mode=ParseMode.HTML
    )

    try:
        local_path = await reply.download()
        resp = await post_file(
            "https://api.deepai.org/api/torch-srgan",
            local_path,
            headers={'api-key': DEEP_API}
        )

        image_url = resp.get("output_url")
        if not image_url:
            return await status.edit(
                "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Upscale request failed.</b></blockquote>",
                parse_mode=ParseMode.HTML
            )

        final_path = await download_from_url(local_path, image_url)
        if not final_path:
            return await status.edit(
                "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Could not download result.</b></blockquote>",
                parse_mode=ParseMode.HTML
            )

        await status.delete()
        await message.reply_document(final_path)

    except Exception as e:
        await status.edit(
            f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Error:</b> <code>{str(e)}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )


@app.on_message(filters.command("getdraw"))
async def draw_image(_, message: Message):
    from pyrogram.enums import ParseMode
    if not DEEP_API:
        return await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>DeepAI API key is missing.</b></blockquote>",
            parse_mode=ParseMode.HTML
        )

    reply = message.reply_to_message
    query = None

    if reply and reply.text:
        query = reply.text
    elif len(message.command) > 1:
        query = message.text.split(None, 1)[1]

    if not query:
        return await message.reply_text(
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> Please reply to a message or provide text.</blockquote>",
            parse_mode=ParseMode.HTML
        )

    status = await message.reply_text(
        "<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>Generating image...</b></blockquote>",
        parse_mode=ParseMode.HTML
    )

    user_id = message.from_user.id
    chat_id = message.chat.id
    temp_path = f"cache/{user_id}_{chat_id}_{message.id}.png"

    try:
        resp = await post_data(
            "https://api.deepai.org/api/text2img",
            data={'text': query, 'grid_size': '1', 'image_generator_version': 'hd'},
            headers={'api-key': DEEP_API}
        )

        image_url = resp.get("output_url")
        if not image_url:
            return await status.edit(
                "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Failed to generate image.</b></blockquote>",
                parse_mode=ParseMode.HTML
            )

        final_path = await download_from_url(temp_path, image_url)
        if not final_path:
            return await status.edit(
                "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Error downloading image.</b></blockquote>",
                parse_mode=ParseMode.HTML
            )

        await status.delete()
        await message.reply_photo(
            final_path,
            caption=f"<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <code>{query}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        await status.edit(
            f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Error:</b> <code>{str(e)}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
