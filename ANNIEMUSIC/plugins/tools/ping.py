from datetime import datetime

from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from config import *
from ANNIEMUSIC import app
from ANNIEMUSIC.core.call import JARVIS
from ANNIEMUSIC.utils import bot_sys_stats
from ANNIEMUSIC.utils.decorators.language import language
from ANNIEMUSIC.utils.inline import supp_markup
from config import BANNED_USERS, PING_IMG_URL


@app.on_message(filters.command("ping", prefixes=["/", "."]) & ~BANNED_USERS)
@language
async def ping_com(client, message: Message, _):
    start = datetime.now()

    try:
        pytgping = await JARVIS.ping()
    except Exception:
        pytgping = "N/A"

    UP, CPU, RAM, DISK = await bot_sys_stats()
    resp = (datetime.now() - start).microseconds / 1000

    caption = _["ping_2"].format(resp, app.mention, UP, RAM, CPU, DISK, pytgping)
    markup = supp_markup(_)

    sent = False

    if PING_IMG_URL:
        try:
            await message.reply_photo(
                photo=PING_IMG_URL,
                caption=caption,
                reply_markup=markup,
            )
            sent = True
        except Exception:
            pass

    if not sent:
        try:
            await message.reply_text(
                text=caption,
                reply_markup=markup,
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
