from pyrogram.types import InlineKeyboardButton as OriginalIKB
from pyrogram import enums
import inspect

_HAS_BUTTON_STYLE = hasattr(enums, "ButtonStyle")
_IKB_PARAMS = set(inspect.signature(OriginalIKB.__init__).parameters.keys())
_HAS_ICON = "icon_custom_emoji_id" in _IKB_PARAMS

def InlineKeyboardButton(*args, **kwargs):
    if not _HAS_BUTTON_STYLE:
        kwargs.pop("style", None)
    else:
        style = kwargs.get("style")
        if style and isinstance(style, str):
            style = style.lower()
            if style == "primary":
                kwargs["style"] = enums.ButtonStyle.PRIMARY
            elif style == "success":
                kwargs["style"] = enums.ButtonStyle.SUCCESS
            elif style == "danger":
                kwargs["style"] = enums.ButtonStyle.DANGER
            else:
                kwargs["style"] = enums.ButtonStyle.DEFAULT

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
