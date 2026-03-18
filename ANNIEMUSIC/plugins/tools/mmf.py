import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from ANNIEMUSIC import app

@app.on_message(filters.command("mmf"))
async def mmf(_, message: Message):
    chat_id = message.chat.id
    reply_message = message.reply_to_message

    if len(message.text.split()) < 2:
        await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Meme Maker</b></blockquote>\n"
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> Give me text after <code>/mmf</code> to memify.\n"
            "Reply to an image with: <code>/mmf top text ; bottom text</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    msg = await message.reply_text(
        "<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>Creating meme...</b></blockquote>",
        parse_mode=ParseMode.HTML
    )
    text = message.text.split(None, 1)[1]
    try:
        file = await app.download_media(reply_message)
    except Exception as e:
        await msg.edit(
            f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Failed to download media.</b>\n<code>{e}</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    meme = await drawText(file, text)
    await app.send_document(chat_id, document=meme)

    await msg.delete()
    os.remove(meme)


async def drawText(image_path, text):
    img = Image.open(image_path)
    os.remove(image_path)

    i_width, i_height = img.size

    if os.name == "nt":
        fnt = "arial.ttf"
    else:
        fnt = "./ANNIEMUSIC/assets/default.ttf"

    m_font = ImageFont.truetype(fnt, int((70 / 640) * i_width))

    if ";" in text:
        upper_text, lower_text = text.split(";")
    else:
        upper_text = text
        lower_text = ""

    draw = ImageDraw.Draw(img)
    current_h, pad = 10, 5

    if upper_text:
        for u_text in textwrap.wrap(upper_text, width=15):
            uwl, uht, uwr, uhb = m_font.getbbox(u_text)
            u_width, u_height = uwr - uwl, uhb - uht
            for dx, dy in [(-2,0),(2,0),(0,-2),(0,2)]:
                draw.text(
                    xy=(((i_width - u_width) / 2) + dx, int((current_h / 640) * i_width) + dy),
                    text=u_text, font=m_font, fill=(0, 0, 0),
                )
            draw.text(
                xy=((i_width - u_width) / 2, int((current_h / 640) * i_width)),
                text=u_text, font=m_font, fill=(255, 255, 255),
            )
            current_h += u_height + pad

    if lower_text:
        for l_text in textwrap.wrap(lower_text, width=15):
            uwl, uht, uwr, uhb = m_font.getbbox(l_text)
            u_width, u_height = uwr - uwl, uhb - uht
            for dx, dy in [(-2,0),(2,0),(0,-2),(0,2)]:
                draw.text(
                    xy=(((i_width - u_width) / 2) + dx, i_height - u_height - int((20 / 640) * i_width) + dy),
                    text=l_text, font=m_font, fill=(0, 0, 0),
                )
            draw.text(
                xy=((i_width - u_width) / 2, i_height - u_height - int((20 / 640) * i_width)),
                text=l_text, font=m_font, fill=(255, 255, 255),
            )
            current_h += u_height + pad

    image_name = "memify.webp"
    img.save(image_name, "webp")
    return image_name
