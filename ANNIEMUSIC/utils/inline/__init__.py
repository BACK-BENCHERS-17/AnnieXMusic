from pyrogram.types import InlineKeyboardButton as OriginalIKB
import inspect

def InlineKeyboardButton(*args, **kwargs):
    # Get all parameters accepted by the current library's version
    sig = inspect.signature(OriginalIKB.__init__)
    valid_params = sig.parameters.keys()

    # Check for style support
    style = kwargs.pop("style", None)
    # Remove icon if passed, as requested to skip it for now
    kwargs.pop("icon_custom_emoji_id", None)

    # Prepare arguments for the original constructor
    actual_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}

    # If style is in valid_params, add it back to actual_kwargs
    if "style" in valid_params and style:
        actual_kwargs["style"] = style

    btn = OriginalIKB(*args, **actual_kwargs)

    # If style wasn't natively supported, try setting it as an attribute anyway
    if "style" not in valid_params and style:
        setattr(btn, "style", style)

    return btn
from .extras import *
from .help import *
from .play import *
from .queue import *
from .settings import *
from .start import *
from .speed import *
