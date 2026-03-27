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
            parse_mode=enums.ParseMode.HTML,
        ) if config.STRING1 else None
        self.two = Client(
            "AnnieAssis2",
            config.API_ID,
            config.API_HASH,
            session_string=config.STRING2,
            parse_mode=enums.ParseMode.HTML,
        ) if config.STRING2 else None
        self.three = Client(
            "AnnieAssis3",
            config.API_ID,
            config.API_HASH,
            session_string=config.STRING3,
            parse_mode=enums.ParseMode.HTML,
        ) if config.STRING3 else None
        self.four = Client(
            "AnnieAssis4",
            config.API_ID,
            config.API_HASH,
            session_string=config.STRING4,
            parse_mode=enums.ParseMode.HTML,
        ) if config.STRING4 else None
        self.five = Client(
            "AnnieAssis5",
            config.API_ID,
            config.API_HASH,
            session_string=config.STRING5,
            parse_mode=enums.ParseMode.HTML,
        ) if config.STRING5 else None

    async def _setup_assistant(self, client, index: int):
        """Do post-start assistant setup: join groups, send log message, fetch identity.
        The client is already started by PyTgCalls — do NOT call client.start() here."""
        if client is None:
            return

        try:
            # Verify client is actually connected before registering it
            me = await client.get_me()
            client.id, client.name, client.username = me.id, me.first_name, me.username
            assistantids.append(me.id)

            # Only register as active AFTER confirming the connection works
            assistants.append(index)

            for group in GROUPS_TO_JOIN:
                try:
                    await client.join_chat(group)
                except Exception:
                    pass

            try:
                await client.send_message(
                    config.LOGGER_ID, f"Annie's Assistant {index} Started"
                )
            except Exception:
                LOGGER(__name__).error(
                    f"Assistant {index} can't access the log group. Check permissions!"
                )

            LOGGER(__name__).info(f"Assistant {index} Started as {client.name}")

        except errors.AuthKeyDuplicated:
            LOGGER(__name__).error(
                f"Assistant {index}: AUTH_KEY_DUPLICATED — this session is already open elsewhere. "
                f"Generate a fresh session string for STRING{index}."
            )
        except errors.AuthKeyUnregistered:
            LOGGER(__name__).error(
                f"Assistant {index}: AuthKeyUnregistered — session expired. Generate a new STRING{index}."
            )
        except errors.UserDeactivated:
            LOGGER(__name__).error(
                f"Assistant {index}: Account deactivated. Remove STRING{index}."
            )
        except Exception as e:
            LOGGER(__name__).error(f"Assistant {index} setup failed: {e}")

    async def start(self):
        """Legacy: called when Userbot manages its own clients independently.
        In shared-client mode, use post_start() after PyTgCalls.start() instead."""
        LOGGER(__name__).info("Starting Annie's Assistants...")
        await self._setup_assistant(self.one, 1)
        await self._setup_assistant(self.two, 2)
        await self._setup_assistant(self.three, 3)
        await self._setup_assistant(self.four, 4)
        await self._setup_assistant(self.five, 5)

    async def post_start(self):
        """Run assistant setup after PyTgCalls has already started the shared Pyrogram clients."""
        LOGGER(__name__).info("Setting up Annie's Assistants (post PyTgCalls start)...")
        await self._setup_assistant(self.one, 1)
        await self._setup_assistant(self.two, 2)
        await self._setup_assistant(self.three, 3)
        await self._setup_assistant(self.four, 4)
        await self._setup_assistant(self.five, 5)

    async def stop(self):
        LOGGER(__name__).info("Stopping Assistants...")
        try:
            if config.STRING1 and self.one and self.one.is_connected:
                await self.one.stop()
            if config.STRING2 and self.two and self.two.is_connected:
                await self.two.stop()
            if config.STRING3 and self.three and self.three.is_connected:
                await self.three.stop()
            if config.STRING4 and self.four and self.four.is_connected:
                await self.four.stop()
            if config.STRING5 and self.five and self.five.is_connected:
                await self.five.stop()
        except Exception as e:
            LOGGER(__name__).error(f"Error while stopping assistants: {e}")