from pyrogram.types import InlineKeyboardButton as OriginalIKB
import inspect

def InlineKeyboardButton(*args, **kwargs):
    # Get all parameters accepted by the current library's version
    sig = inspect.signature(OriginalIKB.__init__)
    valid_params = sig.parameters.keys()

    # Separate valid parameters and extra attributes
    actual_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}
    extra_attrs = {k: v for k, v in kwargs.items() if k not in valid_params}

    btn = OriginalIKB(*args, **actual_kwargs)
    for k, v in extra_attrs.items():
        setattr(btn, k, v)
    return btn

from .extras import *
from .help import *
from .play import *
from .queue import *
from .settings import *
from .start import *
from .speed import *
