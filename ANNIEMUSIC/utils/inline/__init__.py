from . import InlineKeyboardButton as OriginalIKB

def InlineKeyboardButton(*args, **kwargs):
    icon = kwargs.get("icon_custom_emoji_id")
    if icon and isinstance(icon, str):
        try:
            kwargs["icon_custom_emoji_id"] = int(icon)
        except ValueError:
            pass
    return OriginalIKB(*args, **kwargs)

from .extras import *
from .help import *
from .play import *
from .queue import *
from .settings import *
from .start import *
from .speed import *
