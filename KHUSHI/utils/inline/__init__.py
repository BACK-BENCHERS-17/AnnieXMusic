from pyrogram.types import InlineKeyboardButton as OriginalIKB
import inspect

_IKB_PARAMS = set(inspect.signature(OriginalIKB.__init__).parameters.keys())
_HAS_ICON = "icon_custom_emoji_id" in _IKB_PARAMS

def InlineKeyboardButton(*args, **kwargs):
    kwargs.pop("style", None)

    if not _HAS_ICON:
        kwargs.pop("icon_custom_emoji_id", None)
    else:
        icon = kwargs.get("icon_custom_emoji_id")
        if icon and isinstance(icon, str):
            try:
                kwargs["icon_custom_emoji_id"] = int(icon)
            except ValueError:
                kwargs.pop("icon_custom_emoji_id", None)

    return OriginalIKB(*args, **kwargs)

from .extras import *
from .help import *
from .play import *
from .queue import *
from .settings import *
from .start import *
from .speed import *
