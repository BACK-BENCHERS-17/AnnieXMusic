from . import InlineKeyboardButton

import config
from ANNIEMUSIC import app


def start_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"], url=f"https://t.me/{app.username}?startgroup=true", 
                style="primary",
                icon_custom_emoji_id=5041975203853239332
            ),
            InlineKeyboardButton(
                text=_["S_B_2"], url=config.SUPPORT_CHANNEL, 
                style="success",
                icon_custom_emoji_id=5454388756867986435
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
                style="primary"
            )
        ],
        [
            InlineKeyboardButton(
                text=_["S_B_7"], user_id=config.OWNER_ID, style="success"
            ),
            InlineKeyboardButton(
                text=_["S_B_4"], url=config.SUPPORT_CHAT, style="success"
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["S_B_3"], callback_data="open_help", style="success"
            ),
        ],
    ]
    return buttons
