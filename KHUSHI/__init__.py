"""
KHUSHI — Super Fast Music Bot
Reuses ANNIEMUSIC core (same bot client, same PyTgCalls, same platforms).
KHUSHI brings brand-new UI, new modules, and a cleaner plugin structure.
"""

from ANNIEMUSIC import (
    app,
    userbot,
    Apple,
    Carbon,
    SoundCloud,
    Spotify,
    Resso,
    Telegram,
    YouTube,
)
from ANNIEMUSIC.core.call import JARVIS
from ANNIEMUSIC.misc import db, SUDOERS

__all__ = [
    "app",
    "userbot",
    "JARVIS",
    "db",
    "SUDOERS",
    "Apple",
    "Carbon",
    "SoundCloud",
    "Spotify",
    "Resso",
    "Telegram",
    "YouTube",
]
