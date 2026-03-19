import sys
import asyncio
import os
from pyrogram import Client, errors, enums
from pyrogram.enums import ChatMemberStatus

import config
from ..logging import LOGGER

BOT_PFP_PATH = "ANNIEMUSIC/assets/bot_pfp.png"


async def _update_bot_pfp(client: "JARVIS"):
    try:
        photo = None
        async for p in client.get_chat_photos(client.id, limit=1):
            photo = p
            break
        if photo:
            await client.download_media(photo.file_id, file_name=BOT_PFP_PATH)
            LOGGER(__name__).info("✅ Bot profile picture saved as bot_pfp.png.")
        else:
            LOGGER(__name__).info("ℹ️ Bot has no profile picture — thumbnail will use upic.png.")
    except Exception as e:
        LOGGER(__name__).warning(f"⚠️ Could not fetch bot PFP: {e}")


class JARVIS(Client):
    def __init__(self):
        super().__init__(
            name="AnnieXMusic",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            in_memory=True,
            parse_mode=enums.ParseMode.HTML,
            workers=48,
            max_concurrent_transmissions=7,
        )
        LOGGER(__name__).info("Bot client initialized.")

    async def start(self):
        try:
            await super().start()
        except errors.FloodWait as e:
            LOGGER(__name__).warning(f"FloodWait detected. Waiting for {e.value} seconds...")
            await asyncio.sleep(e.value)
            await super().start()

        me = await self.get_me()
        self.username, self.id = me.username, me.id
        self.name = f"{me.first_name} {me.last_name or ''}".strip()
        self.mention = me.mention

        try:
            await self.send_message(
                config.LOGGER_ID,
                (
                    f"<u><b>» {self.mention} ʙᴏᴛ sᴛᴀʀᴛᴇᴅ :</b></u>\n\n"
                    f"ɪᴅ : <code>{self.id}</code>\n"
                    f"ɴᴀᴍᴇ : {self.name}\n"
                    f"ᴜsᴇʀɴᴀᴍᴇ : @{self.username}"
                ),
            )
        except (errors.ChannelInvalid, errors.PeerIdInvalid):
            LOGGER(__name__).error("❌ Bot cannot access the log group/channel – add & promote it first!")
            sys.exit()
        except Exception as exc:
            LOGGER(__name__).error(f"❌ Bot has failed to access the log group.\nReason: {type(exc).__name__}")
            sys.exit()

        try:
            member = await self.get_chat_member(config.LOGGER_ID, self.id)
            if member.status != ChatMemberStatus.ADMINISTRATOR:
                LOGGER(__name__).error("❌ Promote the bot as admin in the log group/channel.")
                sys.exit()
        except Exception as e:
            LOGGER(__name__).error(f"❌ Could not check admin status: {e}")
            sys.exit()

        LOGGER(__name__).info(f"✅ Music Bot started as {self.name} (@{self.username})")
        await _update_bot_pfp(self)