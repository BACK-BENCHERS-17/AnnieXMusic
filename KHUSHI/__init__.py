"""
KHUSHI — Independent core initialization.
Own Pyrogram client, own PyTgCalls, own Userbot.
Platforms re-instantiated from ANNIEMUSIC's platform classes (stateless API wrappers).
"""

from KHUSHI.logging import LOGGER
from KHUSHI.core.bot import KhushiBot
from KHUSHI.core.userbot import Userbot
from KHUSHI.misc import dbb

from ANNIEMUSIC.platforms import (
    AppleAPI,
    CarbonAPI,
    RessoAPI,
    SoundAPI,
    SpotifyAPI,
    TeleAPI,
    YouTubeAPI,
)

# ── KHUSHI's OWN instances ────────────────────────────────────────────────────
app = KhushiBot()
userbot = Userbot()

# ── Platform API instances (stateless, safe to share) ────────────────────────
Apple      = AppleAPI()
Carbon     = CarbonAPI()
SoundCloud = SoundAPI()
Spotify    = SpotifyAPI()
Resso      = RessoAPI()
Telegram   = TeleAPI()
YouTube    = YouTubeAPI()

dbb()

__all__ = [
    "LOGGER",
    "app",
    "userbot",
    "Apple",
    "Carbon",
    "SoundCloud",
    "Spotify",
    "Resso",
    "Telegram",
    "YouTube",
]
