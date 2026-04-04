"""
KHUSHI Bot — Entry Point
Run with:  python -m KHUSHI
"""

import asyncio
import importlib
import os
import signal

import requests
from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from KHUSHI import LOGGER, app, userbot
from KHUSHI.core.call import JARVIS
from KHUSHI.misc import sudo
from KHUSHI.utils.database import get_banned_users, get_gbanned
from KHUSHI.utils.weburl import WEB_URL
from config import BANNED_USERS

_PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "plugins")


def _load_plugins():
    import glob
    paths = glob.glob(_PLUGIN_DIR + "/*.py")
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
    LOGGER("KHUSHI").info(f"KHUSHI: {count}/{len(paths)-1} plugins loaded.")


async def _set_commands():
    try:
        cmds = [
            {"command": "play",      "description": "ꜱᴛʀᴇᴀᴍ ᴀᴜᴅɪᴏ ɪɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ"},
            {"command": "vplay",     "description": "ꜱᴛʀᴇᴀᴍ ᴠɪᴅᴇᴏ ɪɴ ᴠɪᴅᴇᴏ ᴄʜᴀᴛ"},
            {"command": "pause",     "description": "ᴘᴀᴜꜱᴇ ᴘʟᴀʏʙᴀᴄᴋ"},
            {"command": "resume",    "description": "ʀᴇꜱᴜᴍᴇ ᴘʟᴀʏʙᴀᴄᴋ"},
            {"command": "skip",      "description": "ꜱᴋɪᴘ ᴄᴜʀʀᴇɴᴛ ᴛʀᴀᴄᴋ"},
            {"command": "stop",      "description": "ꜱᴛᴏᴘ & ᴄʟᴇᴀʀ ǫᴜᴇᴜᴇ"},
            {"command": "queue",     "description": "ꜱʜᴏᴡ ᴄᴜʀʀᴇɴᴛ ǫᴜᴇᴜᴇ"},
            {"command": "volume",    "description": "ꜱᴇᴛ ᴠᴏʟᴜᴍᴇ [0-200]"},
            {"command": "loop",      "description": "ʟᴏᴏᴘ ᴛʀᴀᴄᴋ [1-10]"},
            {"command": "shuffle",   "description": "ꜱʜᴜꜰꜰʟᴇ ᴛʜᴇ ǫᴜᴇᴜᴇ"},
            {"command": "ping",      "description": "ʙᴏᴛ ꜱᴛᴀᴛᴜꜱ & ꜱʏꜱᴛᴇᴍ ꜱᴛᴀᴛꜱ"},
            {"command": "start",     "description": "ꜱᴛᴀʀᴛ ᴀɴɴɪᴇ"},
            {"command": "help",      "description": "ᴀɴɴɪᴇ ʜᴇʟᴘ ᴍᴇɴᴜ"},
            {"command": "language",  "description": "ᴄʜᴀɴɢᴇ ʙᴏᴛ ʟᴀɴɢᴜᴀɢᴇ"},
            {"command": "stats",     "description": "ʙᴏᴛ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ"},
            {"command": "bc",        "description": "ʙʀᴏᴀᴅᴄᴀꜱᴛ (ꜱᴜᴅᴏ ᴏɴʟʏ)"},
        ]
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/setMyCommands"
        r = requests.post(url, json={"commands": cmds}, timeout=10)
        if r.json().get("ok"):
            LOGGER("KHUSHI").info("✅ Bot commands registered.")
    except Exception as e:
        LOGGER("KHUSHI").warning(f"setMyCommands failed: {e}")


async def _set_menu_button():
    try:
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/setChatMenuButton"
        if WEB_URL:
            payload = {
                "menu_button": {
                    "type": "web_app",
                    "text": "ANNIE",
                    "web_app": {"url": WEB_URL},
                }
            }
        else:
            payload = {"menu_button": {"type": "commands"}}
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass


async def _graceful_shutdown():
    try:
        from KHUSHI.utils.database import get_active_chats
        for cid in await get_active_chats():
            try:
                await JARVIS.stop_stream(cid)
            except (NoActiveGroupCall, Exception):
                pass
    except Exception:
        pass
    try:
        await userbot.stop()
    except Exception:
        pass
    try:
        await app.stop()
    except Exception:
        pass


def _sigterm(sig, frame):
    LOGGER("KHUSHI").info("SIGTERM — shutting down...")
    asyncio.get_event_loop().create_task(_graceful_shutdown())


async def _start_web():
    try:
        from web_config import WEB_ENABLED, WEB_HOST, WEB_PORT
        if not WEB_ENABLED:
            return
        from KHUSHI.utils.webserver import start_webserver
        await start_webserver(WEB_HOST, WEB_PORT)
    except ImportError:
        pass
    except Exception as e:
        LOGGER("KHUSHI").warning(f"Web server failed to start: {e}")


async def main():
    signal.signal(signal.SIGTERM, _sigterm)

    LOGGER("KHUSHI").info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    LOGGER("KHUSHI").info("       A N N I E  |  Music Bot     ")
    LOGGER("KHUSHI").info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Populate banned sets
    try:
        for uid in await get_banned_users():
            BANNED_USERS.add(uid)
        for uid in await get_gbanned():
            BANNED_USERS.add(uid)
    except Exception as e:
        LOGGER("KHUSHI").warning(f"Could not load banned users from DB (bot will still start): {e}")

    # Start KHUSHI's bot client
    await app.start()

    # Wire assistants into JARVIS before starting PyTgCalls
    JARVIS.setup_clients(userbot)

    # Start PyTgCalls (starts the Pyrogram assistant clients internally)
    await JARVIS.start()

    # Setup assistant metadata now that clients are running
    await userbot.post_start()

    # Load sudo users
    try:
        await sudo()
    except Exception as e:
        LOGGER("KHUSHI").warning(f"Could not load sudo users from DB (bot will still start): {e}")

    # Load all KHUSHI plugins
    _load_plugins()

    # Start background admin list refresh
    try:
        from KHUSHI.plugins.broadcast import _refresh_adminlist
        asyncio.get_event_loop().create_task(_refresh_adminlist())
    except Exception:
        pass

    await _set_commands()
    await _set_menu_button()
    await _start_web()

    LOGGER("KHUSHI").info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    LOGGER("KHUSHI").info("       A N N I E  is  L I V E !   ")
    LOGGER("KHUSHI").info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    await idle()
    await _graceful_shutdown()


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        LOGGER("KHUSHI").info("Stopped by user.")
