from pyrogram.types import WebAppInfo

from . import InlineKeyboardButton
import config
from ANNIEMUSIC import app
from ANNIEMUSIC.utils.weburl import WEB_URL

_ICONS = {
    "add":     "5042334757040423886",
    "channel": "5825434651717127160",
    "support": "6122692084806716730",
    "help":    "5188093600538057635",
    "web":     "5449449325434266744",
}


def start_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"],
                url=f"https://t.me/{app.username}?startgroup=true",
                style="primary",
                icon_custom_emoji_id=_ICONS["add"],
            ),
            InlineKeyboardButton(
                text=_["S_B_2"],
                url=config.SUPPORT_CHANNEL,
                style="success",
                icon_custom_emoji_id=_ICONS["channel"],
            ),
        ],
    ]
    return buttons


def private_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"],
                url=f"https://t.me/{app.username}?startgroup=true",
                style="primary",
                icon_custom_emoji_id=_ICONS["add"],
            )
        ],
        [
            InlineKeyboardButton(
                text=_["S_B_4"],
                url=config.SUPPORT_CHAT,
                style="success",
                icon_custom_emoji_id=_ICONS["support"],
            ),
            InlineKeyboardButton(
                text=_["S_B_2"],
                url=config.SUPPORT_CHANNEL,
                style="success",
                icon_custom_emoji_id=_ICONS["channel"],
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["S_B_3"],
                callback_data="open_help",
                style="primary",
                icon_custom_emoji_id=_ICONS["help"],
            ),
        ],
    ]

    if WEB_URL:
        buttons.append([
            InlineKeyboardButton(
                text="🎵 ᴡᴇʙ ᴘʟᴀʏᴇʀ",
                web_app=WebAppInfo(url=WEB_URL),
                style="success",
                icon_custom_emoji_id=_ICONS["web"],
            )
        ])

    return buttons
