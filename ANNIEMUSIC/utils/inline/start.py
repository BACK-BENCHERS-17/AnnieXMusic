from pyrogram.types import WebAppInfo

from . import InlineKeyboardButton
import config
from ANNIEMUSIC import app
from ANNIEMUSIC.utils.weburl import WEB_URL


def start_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"],
                url=f"https://t.me/{app.username}?startgroup=true",
                style="primary",
                icon_custom_emoji_id=5041975203853239332,
            ),
            InlineKeyboardButton(
                text=_["S_B_2"],
                url=config.SUPPORT_CHANNEL,
                style="success",
                icon_custom_emoji_id=5454388756867986435,
            ),
        ],
    ]

    if WEB_URL:
        buttons.append([
            InlineKeyboardButton(
                text="🎵 ᴀɴɴɪᴇ",
                web_app=WebAppInfo(url=WEB_URL),
                style="primary",
            )
        ])

    return buttons


def private_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"],
                url=f"https://t.me/{app.username}?startgroup=true",
                style="primary",
            )
        ],
        [
            InlineKeyboardButton(
                text=_["S_B_7"],
                url="https://t.me/PGL_B4CHI",
                style="success",
            ),
            InlineKeyboardButton(
                text=_["S_B_4"],
                url=config.SUPPORT_CHAT,
                style="success",
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["S_B_3"],
                callback_data="open_help",
                style="success",
            ),
        ],
    ]

    if WEB_URL:
        buttons.append([
            InlineKeyboardButton(
                text="🎵 ᴀɴɴɪᴇ",
                web_app=WebAppInfo(url=WEB_URL),
                style="primary",
            )
        ])

    return buttons
