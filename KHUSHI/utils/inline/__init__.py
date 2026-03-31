from pyrogram.types import InlineKeyboardButton as OriginalIKB
import inspect

try:
    from pyrogram.enums import ButtonStyle
    _HAS_BUTTON_STYLE = True
except ImportError:
    ButtonStyle = None
    _HAS_BUTTON_STYLE = False

_IKB_PARAMS = set(inspect.signature(OriginalIKB.__init__).parameters.keys())
_HAS_ICON  = "icon_custom_emoji_id" in _IKB_PARAMS
_HAS_STYLE = "style" in _IKB_PARAMS and _HAS_BUTTON_STYLE

if _HAS_BUTTON_STYLE:
    _STYLE_MAP = {
        "primary": ButtonStyle.PRIMARY,
        "success": ButtonStyle.SUCCESS,
        "danger":  ButtonStyle.DANGER,
        "default": ButtonStyle.DEFAULT,
    }
else:
    _STYLE_MAP = {}


def InlineKeyboardButton(*args, **kwargs):
    raw_style = kwargs.pop("style", None)

    if _HAS_STYLE and raw_style is not None:
        if isinstance(raw_style, str):
            kwargs["style"] = _STYLE_MAP.get(raw_style.lower(), ButtonStyle.DEFAULT)
        else:
            kwargs["style"] = raw_style

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


from pyrogram.types import InlineKeyboardMarkup


def close_markup(_):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            text=_["CLOSE_BUTTON"],
            callback_data="close",
            style="danger",
        )
    ]])


from .extras import *
from .help import *
from .play import *
from .queue import *
from .settings import *
from .start import *
from .speed import *
