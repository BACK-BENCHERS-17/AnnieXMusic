import asyncio
import importlib
import signal
import requests

from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from ANNIEMUSIC import LOGGER, app, userbot
from ANNIEMUSIC.core.call import JARVIS
from ANNIEMUSIC.misc import sudo
from ANNIEMUSIC.plugins import ALL_MODULES
from ANNIEMUSIC.utils.database import get_banned_users, get_gbanned
from ANNIEMUSIC.utils.weburl import WEB_URL
from config import BANNED_USERS

from ANNIEMUSIC.utils.health_check import start_health_server, set_bot_loop


async def _set_menu_button():
    """Set the bot menu button via Bot API (works with all pyrogram versions)."""
    if not WEB_URL:
        LOGGER("ANNIEMUSIC").info("⚙️  No WEB_URL detected — menu button not set.")
        return
    try:
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/setChatMenuButton"
        payload = {
            "menu_button": {
                "type": "web_app",
                "text": "ANNIE",
                "web_app": {"url": WEB_URL},
            }
        }
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if data.get("ok"):
            LOGGER("ANNIEMUSIC").info(f"✅ Menu button set → {WEB_URL}")
        else:
            LOGGER("ANNIEMUSIC").warning(f"⚠️  Menu button API error: {data.get('description')}")
    except Exception as e:
        LOGGER("ANNIEMUSIC").warning(f"⚠️  Could not set menu button: {e}")


async def _graceful_shutdown():
    """Gracefully stop all Pyrogram clients so Telegram closes the sessions.
    This prevents AUTH_KEY_DUPLICATED on the next bot restart."""
    LOGGER("ANNIEMUSIC").info("Received shutdown signal — gracefully stopping clients...")
    try:
        await userbot.stop()
    except Exception:
        pass
    try:
        await app.stop()
    except Exception:
        pass
    LOGGER("ANNIEMUSIC").info("All clients stopped. Exiting.")


async def init():
    # Start health check server for Railway
    start_health_server()
    # Register the running event loop so Flask control endpoints can call async bot functions
    loop = asyncio.get_event_loop()
    set_bot_loop(loop)

    # Register SIGTERM handler for graceful shutdown (prevents AUTH_KEY_DUPLICATED on restart)
    def _sigterm_handler():
        LOGGER("ANNIEMUSIC").info("SIGTERM received — scheduling graceful shutdown.")
        asyncio.ensure_future(_graceful_shutdown())

    try:
        loop.add_signal_handler(signal.SIGTERM, _sigterm_handler)
        loop.add_signal_handler(signal.SIGINT, _sigterm_handler)
    except (NotImplementedError, RuntimeError):
        pass

    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("ᴀssɪsᴛᴀɴᴛ sᴇssɪᴏɴ ɴᴏᴛ ғɪʟʟᴇᴅ, ᴘʟᴇᴀsᴇ ғɪʟʟ ᴀ ᴘʏʀᴏɢʀᴀᴍ sᴇssɪᴏɴ...")
        exit()

    LOGGER("ANNIEMUSIC").info("▶️ Using android_embed client — no PO token needed, verified 2026.")

    await sudo()

    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except:
        pass

    await app.start()

    # ── Set the menu button (Mini App) ───────────────────────────
    await _set_menu_button()

    for all_module in ALL_MODULES:
        importlib.import_module("ANNIEMUSIC.plugins" + all_module)

    LOGGER("ANNIEMUSIC.plugins").info("ᴀɴɴɪᴇ's ᴍᴏᴅᴜʟᴇs ʟᴏᴀᴅᴇᴅ...")

    JARVIS.setup_clients(userbot)
    await JARVIS.start()
    await userbot.post_start()

    try:
        await JARVIS.stream_call("http://docs.evostream.com/sample_content/assets/sintel1m720p.mp4")
    except NoActiveGroupCall:
        LOGGER("ANNIEMUSIC").error(
            "ᴘʟᴇᴀsᴇ ᴛᴜʀɴ ᴏɴ ᴛʜᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ᴏғ ʏᴏᴜʀ ʟᴏɢ ɢʀᴏᴜᴘ/ᴄʜᴀɴɴᴇʟ.\n\nᴀɴɴɪᴇ ʙᴏᴛ sᴛᴏᴘᴘᴇᴅ..."
        )
        exit()
    except:
        pass

    await JARVIS.decorators()
    LOGGER("ANNIEMUSIC").info(
        "\x41\x6e\x6e\x69\x65\x20\x4d\x75\x73\x69\x63\x20\x52\x6f\x62\x6f\x74\x20\x53\x74\x61\x72\x74\x65\x64\x20\x53\x75\x63\x63\x65\x73\x73\x66\x75\x6c\x6c\x79\x2e\x2e\x2e"
    )
    await idle()
    await app.stop()
    await userbot.stop()
    LOGGER("ANNIEMUSIC").info("sᴛᴏᴘᴘɪɴɢ ᴀɴɴɪᴇ ᴍᴜsɪᴄ ʙᴏᴛ ...")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())
