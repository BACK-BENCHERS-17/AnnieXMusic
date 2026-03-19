import asyncio
from pyrogram import Client, enums, errors

import config

from ..logging import LOGGER

assistants = []
assistantids = []

GROUPS_TO_JOIN = [
    "AnnieSupportGroup",
]


# Initialize userbots
class Userbot:
    def __init__(self):
        self.one = Client(
            "AnnieAssis1",
            config.API_ID,
            config.API_HASH,
            session_string=config.STRING1,
            no_updates=True,
            parse_mode=enums.ParseMode.HTML,
        ) if config.STRING1 else None
        self.two = Client(
            "AnnieAssis2",
            config.API_ID,
            config.API_HASH,
            session_string=config.STRING2,
            no_updates=True,
            parse_mode=enums.ParseMode.HTML,
        ) if config.STRING2 else None
        self.three = Client(
            "AnnieAssis3",
            config.API_ID,
            config.API_HASH,
            session_string=config.STRING3,
            no_updates=True,
            parse_mode=enums.ParseMode.HTML,
        ) if config.STRING3 else None
        self.four = Client(
            "AnnieAssis4",
            config.API_ID,
            config.API_HASH,
            session_string=config.STRING4,
            no_updates=True,
            parse_mode=enums.ParseMode.HTML,
        ) if config.STRING4 else None
        self.five = Client(
            "AnnieAssis5",
            config.API_ID,
            config.API_HASH,
            session_string=config.STRING5,
            no_updates=True,
            parse_mode=enums.ParseMode.HTML,
        ) if config.STRING5 else None

    async def start_assistant(self, client, index: int):
        if client is None:
            return

        try:
            try:
                await client.start()
            except errors.FloodWait as e:
                LOGGER(__name__).warning(f"Assistant {index} hit FloodWait. Waiting for {e.value} seconds...")
                await asyncio.sleep(e.value)
                await client.start()

            for group in GROUPS_TO_JOIN:
                try:
                    await client.join_chat(group)
                except Exception:
                    pass

            assistants.append(index)

            try:
                await client.send_message(
                    config.LOGGER_ID, f"Annie's Assistant {index} Started"
                )
            except Exception:
                LOGGER(__name__).error(
                    f"Assistant {index} can't access the log group. Check permissions!"
                )

            me = await client.get_me()
            client.id, client.name, client.username = me.id, me.first_name, me.username
            assistantids.append(me.id)

            LOGGER(__name__).info(f"Assistant {index} Started as {client.name}")

        except Exception as e:
            LOGGER(__name__).error(f"Failed to start Assistant {index}: {e}")

    async def start(self):
        LOGGER(__name__).info("Starting Annie's Assistants...")
        await self.start_assistant(self.one, 1)
        await self.start_assistant(self.two, 2)
        await self.start_assistant(self.three, 3)
        await self.start_assistant(self.four, 4)
        await self.start_assistant(self.five, 5)

    async def stop(self):
        LOGGER(__name__).info("Stopping Assistants...")
        try:
            if config.STRING1:
                await self.one.stop()
            if config.STRING2:
                await self.two.stop()
            if config.STRING3:
                await self.three.stop()
            if config.STRING4:
                await self.four.stop()
            if config.STRING5:
                await self.five.stop()
        except Exception as e:
            LOGGER(__name__).error(f"Error while stopping assistants: {e}")