from pyrogram.types import InlineKeyboardButton as OriginalIKB
import inspect

def InlineKeyboardButton(*args, **kwargs):
    if "style" in kwargs:
        # Check if the current InlineKeyboardButton supports 'style'
        sig = inspect.signature(OriginalIKB.__init__)
        if "style" not in sig.parameters:
            kwargs.pop("style")
    return OriginalIKB(*args, **kwargs)

from .extras import *
from .help import *
from .play import *
from .queue import *
from .settings import *
from .start import *
from .speed import *
