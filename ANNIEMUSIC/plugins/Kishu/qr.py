from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from ANNIEMUSIC import app
import qrcode
import io


def generate_qr_code(text):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="white", back_color="black")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes


@app.on_message(filters.command("qr"))
async def qr_handler(client, message: Message):
    if len(message.command) > 1:
        input_text = " ".join(message.command[1:])
        qr_image = generate_qr_code(input_text)
        await message.reply_photo(
            qr_image,
            caption="<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>Here's your QR Code!</b></blockquote>",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>QR Generator</b></blockquote>\n"
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> Please provide text for the QR code.\n"
            "<b>Example:</b> <code>/qr https://github.com/</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
