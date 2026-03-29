import asyncio
import logging
import random
import time
from pyrogram import filters, enums

LOGGER = logging.getLogger(__name__)
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.raw import functions as raw_func, types as raw_types
from pyrogram.parser import Parser
from youtubesearchpython.__future__ import VideosSearch

import config
from ANNIEMUSIC import app
from ANNIEMUSIC.misc import _boot_
from ANNIEMUSIC.plugins.sudo.sudoers import sudoers_list
from ANNIEMUSIC.utils import bot_sys_stats
from ANNIEMUSIC.utils.database import (
    add_served_chat,
    add_served_user,
    get_served_chats,
    get_served_users,
    is_on_off,
)
from ANNIEMUSIC.utils.decorators.language import LanguageStart
from ANNIEMUSIC.utils.formatters import get_readable_time
from ANNIEMUSIC.utils.inline.start import private_panel, start_panel
from ANNIEMUSIC.utils.inline.help import first_page
from ANNIEMUSIC.utils.reactions import react_to_command
from ANNIEMUSIC.utils.font_styles import Fonts
from config import BANNED_USERS, AYUV, HELP_IMG_URL, START_IMGS, STICKERS, PING_IMG_URL

# ── Effect ID ─────────────────────────────────────────────────────────────────
MESSAGE_EFFECT_ID = 5159385139981059251


async def send_photo_with_effect(client, message: Message, photo_url: str,
                                  caption: str, markup: InlineKeyboardMarkup,
                                  effect_id: int = MESSAGE_EFFECT_ID) -> bool:
    """Send a photo with message_effect_id using Pyrogram's raw API."""
    try:
        peer = await client.resolve_peer(message.chat.id)

        # Parse HTML caption → plain text + raw entities
        parser = Parser(client)
        parsed = await parser.parse(caption, mode=enums.ParseMode.HTML)
        text     = parsed.get("message", "")
        entities = parsed.get("entities") or []

        # Convert high-level InlineKeyboardMarkup → raw ReplyMarkup
        raw_markup = await markup.write(client) if markup else None

        # Photo media with spoiler
        media = raw_types.InputMediaPhotoExternal(url=photo_url, spoiler=True)

        await client.invoke(
            raw_func.messages.SendMedia(
                peer=peer,
                media=media,
                message=text,
                random_id=random.randint(-(2**63), 2**63 - 1),
                reply_markup=raw_markup,
                entities=entities,
                effect=effect_id,
            )
        )
        return True
    except Exception as e:
        print(f"[EFFECT SEND] Raw API failed: {e}")
        return False


async def delete_sticker_after_delay(message: Message, delay: int) -> None:
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


_OWNER_LINK = "<a href='https://t.me/PGL_B4CHI'>ㅤ⎯꯭̽ 𝚱 𝚮 𝐔 𝛅 𝚮 𝚰⥱</a>"


@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    asyncio.create_task(react_to_command(message))
    try:
        await add_served_user(message.from_user.id)
    except Exception:
        pass

    if len(message.text.split()) > 1:
        name = message.text.split(None, 1)[1]

        if name.startswith("help"):
            keyboard = first_page(_)
            return await message.reply_photo(
                photo=HELP_IMG_URL,
                caption=_["help_1"].format(config.SUPPORT_CHAT),
                reply_markup=keyboard,
            )

        if name.startswith("sud"):
            await sudoers_list(client=client, message=message, _=_)
            if await is_on_off(2):
                username = f"@{message.from_user.username}" if message.from_user.username else "(none)"
                await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=(
                        f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>sᴜᴅᴏʟɪsᴛ</b>.\n\n"
                        f"<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n"
                        f"<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {username}"
                    ),
                )
            return

        if name.startswith("inf"):
            m = await message.reply_text("🔎")
            try:
                vid_id = str(name).replace("info_", "", 1)
                query = f"https://www.youtube.com/watch?v={vid_id}"
                results = VideosSearch(query, limit=1)
                data = await results.next()
                result = (data.get("result") or [None])[0]
                if not result:
                    await m.edit_text("No results found.")
                    return

                title = result.get("title") or "ᴜɴᴋɴᴏᴡɴ"
                duration = result.get("duration") or "ᴜɴᴋɴᴏᴡɴ"
                views = (result.get("viewCount") or {}).get("short") or "ᴜɴᴋɴᴏᴡɴ"
                thumbnail = ((result.get("thumbnails") or [{}])[0].get("url") or "").split("?")[0]
                channellink = (result.get("channel") or {}).get("link") or "https://youtube.com"
                channel = (result.get("channel") or {}).get("name") or "ᴜɴᴋɴᴏᴡɴ"
                link = result.get("link") or query
                published = result.get("publishedTime") or "ᴜɴᴋɴᴏᴡɴ"

                searched_text = _["start_6"].format(title, duration, views, published, channellink, channel, config.OWNER_USERNAME)
                key = InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text=_["S_B_6"], url=link),
                      InlineKeyboardButton(text=_["S_B_4"], url=config.SUPPORT_CHAT)]]
                )

                await m.delete()

                await app.send_photo(
                    chat_id=message.chat.id,
                    photo=thumbnail or HELP_IMG_URL,
                    caption=searched_text,
                    reply_markup=key,
                )

                if await is_on_off(2):
                    username = f"@{message.from_user.username}" if message.from_user.username else "(none)"
                    await app.send_message(
                        chat_id=config.LOGGER_ID,
                        text=(
                            f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>ᴛʀᴀᴄᴋ ɪɴғᴏʀᴍᴀᴛɪᴏɴ</b>.\n\n"
                            f"<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n"
                            f"<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {username}"
                        ),
                    )
            except Exception as e:
                await m.edit_text(f"Error: {e}")
            return

    out = private_panel(_)
    sticker_message = await message.reply_sticker(sticker=random.choice(STICKERS))
    asyncio.create_task(delete_sticker_after_delay(sticker_message, 2))

    served_chats_coro = get_served_chats()
    served_users_coro = get_served_users()
    stats_coro = bot_sys_stats()
    try:
        served_chats, served_users, (UP, CPU, RAM, DISK) = await asyncio.gather(
            served_chats_coro, served_users_coro, stats_coro
        )
    except Exception:
        try:
            UP, CPU, RAM, DISK = await bot_sys_stats()
        except Exception:
            UP = CPU = RAM = DISK = "N/A"
        served_chats = []
        served_users = []

    _start_caption = _["start_1"].format(
        message.from_user.mention,
        f"<a href='https://t.me/{app.username}'>{app.name}</a>",
        UP, DISK, CPU, RAM,
        _OWNER_LINK
    )
    _markup = InlineKeyboardMarkup(out)
    _img = random.choice(START_IMGS)

    # Try raw API with message effect (spoiler + effect both supported)
    sent = await send_photo_with_effect(
        client, message, _img, _start_caption, _markup
    )

    # Fallback 1: normal reply_photo without effect
    if not sent:
        try:
            await message.reply_photo(
                photo=_img,
                caption=_start_caption,
                reply_markup=_markup,
                has_spoiler=True,
            )
            sent = True
        except Exception:
            pass

    # Fallback 2: text message when photo fails (e.g. URL blocked/invalid)
    if not sent:
        try:
            await message.reply_text(
                _start_caption,
                reply_markup=_markup,
                disable_web_page_preview=True,
            )
        except Exception:
            pass

    if await is_on_off(2):
        username = f"@{message.from_user.username}" if message.from_user.username else "(none)"
        await app.send_message(
            chat_id=config.LOGGER_ID,
            text=(
                f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n"
                f"<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n"
                f"<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {username}"
            ),
        )


@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    try:
        out = start_panel(_)
        UP, CPU, RAM, DISK = await bot_sys_stats()
        user = message.from_user
        mention = user.mention if user else (message.sender_chat.title if message.sender_chat else "User")
        caption = _["start_1"].format(
            mention,
            f"<a href='https://t.me/{app.username}'>{app.name}</a>",
            UP, DISK, CPU, RAM,
            _OWNER_LINK
        )
        markup = InlineKeyboardMarkup(out)
        sent = False
        try:
            await message.reply_photo(
                photo=random.choice(START_IMGS),
                caption=caption,
                reply_markup=markup,
                has_spoiler=True,
            )
            sent = True
        except Exception as e1:
            LOGGER.warning("[start_gp] reply_photo (spoiler) failed: %s", e1)
        if not sent:
            try:
                await message.reply_photo(
                    photo=random.choice(START_IMGS),
                    caption=caption,
                    reply_markup=markup,
                )
                sent = True
            except Exception as e2:
                LOGGER.warning("[start_gp] reply_photo failed: %s", e2)
        if not sent:
            try:
                await message.reply_text(
                    text=caption,
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )
                sent = True
            except Exception as e3:
                LOGGER.error("[start_gp] reply_text failed: %s", e3)
        if not sent:
            LOGGER.error("[start_gp] All send attempts failed for chat %s", message.chat.id)
    except Exception as ex:
        LOGGER.error("[start_gp] Unhandled exception: %s", ex, exc_info=True)
    return await add_served_chat(message.chat.id)
