from pyrogram.types import InlineKeyboardButton as OriginalIKB
import inspect

def InlineKeyboardButton(*args, **kwargs):
    # Get all parameters accepted by the current library's version
    sig = inspect.signature(OriginalIKB.__init__)
    valid_params = sig.parameters.keys()

    # Check for style and icon support
    style = kwargs.pop("style", None)
    icon = kwargs.pop("icon_custom_emoji_id", None)

    # Prepare arguments for the original constructor
    actual_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}

    # If style/icon are in valid_params, add them back to actual_kwargs
    if "style" in valid_params and style:
        actual_kwargs["style"] = style
    if "icon_custom_emoji_id" in valid_params and icon:
        actual_kwargs["icon_custom_emoji_id"] = icon

    btn = OriginalIKB(*args, **actual_kwargs)

    # If they weren't natively supported, try setting them as attributes anyway
    if "style" not in valid_params and style:
        setattr(btn, "style", style)
    if "icon_custom_emoji_id" not in valid_params and icon:
        setattr(btn, "icon_custom_emoji_id", icon)

    return btn
from .extras import *
from .help import *
from .play import *
from .queue import *
from .settings import *
from .start import *
from .speed import *
