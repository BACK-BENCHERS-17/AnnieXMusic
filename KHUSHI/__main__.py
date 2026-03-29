"""
KHUSHI Bot — Entry Point
Run with:  python -m KHUSHI

Reuses ANNIEMUSIC's Pyrogram client, PyTgCalls, platforms, and database.
Loads KHUSHI's own plugins (new UI, new modules) instead of ANNIEMUSIC's.
"""

import asyncio
import importlib
import os
import signal
import sys

import requests
from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from ANNIEMUSIC import LOGGER, app, userbot
from ANNIEMUSIC.core.call import JARVIS
from ANNIEMUSIC.misc import sudo
from ANNIEMUSIC.utils.database import get_banned_users, get_gbanned
from ANNIEMUSIC.utils.weburl import WEB_URL
from config import BANNED_USERS

# Load KHUSHI plugins
_KHUSHI_PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "plugins")


def _load_khushi_plugins():
    import glob
    paths = glob.glob(_KHUSHI_PLUGIN_DIR + "/*.py")
    count = 0
    for path in sorted(paths):
        name = os.path.basename(path).replace(".py", "")
        if name == "__init__":
            continue
        try:
            importlib.import_module(f"KHUSHI.plugins.{name}")
            LOGGER("KHUSHI").info(f"  ✅ KHUSHI.plugins.{name}")
            count += 1
        except Exception as e:
            LOGGER("KHUSHI").error(f"  ❌ KHUSHI.plugins.{name}: {e}")
    LOGGER("KHUSHI").info(f"KHUSHI: {count} plugins loaded.")


async def _set_bot_commands():
    try:
        cmds = [
            {"command": "play",        "description": "Stream audio in voice chat"},
            {"command": "vplay",       "description": "Stream video in video chat"},
            {"command": "pause",       "description": "Pause playback"},
            {"command": "resume",      "description": "Resume playback"},
            {"command": "skip",        "description": "Skip current track"},
            {"command": "stop",        "description": "Stop & clear queue"},
            {"command": "queue",       "description": "Show current queue"},
            {"command": "volume",      "description": "Set volume [0-200]"},
            {"command": "loop",        "description": "Loop track [1-10]"},
            {"command": "shuffle",     "description": "Shuffle the queue"},
            {"command": "247",         "description": "Toggle 24/7 mode"},
            {"command": "ping",        "description": "Bot status & stats"},
            {"command": "kstart",      "description": "Start KHUSHI bot"},
            {"command": "khelp",       "description": "KHUSHI help menu"},
        ]
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/setMyCommands"
        r = requests.post(url, json={"commands": cmds}, timeout=10)
        if r.json().get("ok"):
            LOGGER("KHUSHI").info("✅ KHUSHI bot commands registered.")
    except Exception as e:
        LOGGER("KHUSHI").warning(f"setMyCommands error: {e}")


async def _set_menu_button():
    try:
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/setChatMenuButton"
        if WEB_URL:
            payload = {"menu_button": {"type": "web_app", "text": "KHUSHI", "web_app": {"url": WEB_URL}}}
        else:
            payload = {"menu_button": {"type": "commands"}}
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass


async def _graceful_shutdown():
    try:
        all_chats = []
        from ANNIEMUSIC.utils.database import get_active_chats
        all_chats = await get_active_chats()
    except Exception:
        all_chats = []

    for chat_id in all_chats:
        try:
            await JARVIS.stop_stream(chat_id)
        except (NoActiveGroupCall, Exception):
            pass

    try:
        await userbot.stop()
    except Exception:
        pass
    try:
        await app.stop()
    except Exception:
        pass


def _handle_sigterm(sig, frame):
    LOGGER("KHUSHI").info("SIGTERM received — shutting down gracefully...")
    loop = asyncio.get_event_loop()
    loop.create_task(_graceful_shutdown())


async def main():
    signal.signal(signal.SIGTERM, _handle_sigterm)

    LOGGER("KHUSHI").info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    LOGGER("KHUSHI").info("  KHUSHI Bot  |  Super Fast UI  ")
    LOGGER("KHUSHI").info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Populate banned lists
    for uid in await get_banned_users():
        BANNED_USERS.add(uid)
    for uid in await get_gbanned():
        BANNED_USERS.add(uid)

    # Start clients
    await app.start()
    await userbot.start()

    # Load sudoers
    await sudo()

    # Register assistants with PyTgCalls
    await JARVIS.start()

    # Load KHUSHI plugins
    _load_khushi_plugins()

    await _set_bot_commands()
    await _set_menu_button()

    LOGGER("KHUSHI").info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    LOGGER("KHUSHI").info("  KHUSHI is LIVE !")
    LOGGER("KHUSHI").info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    await idle()
    await _graceful_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOGGER("KHUSHI").info("Stopped by user.")
