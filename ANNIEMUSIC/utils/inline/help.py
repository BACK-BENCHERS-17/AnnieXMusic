from . import InlineKeyboardButton
from pyrogram.types import InlineKeyboardMarkup
from ANNIEMUSIC import app

TOTAL_SECTIONS = 10
SKIP_SECTIONS = set()

_ICONS = {
    "play":     "5188093600538057635",
    "controls": "5373123633415854520",
    "queue":    "5235731086212088293",
    "loop":     "5236698095568298517",
    "seek":     "5289584807741733596",
    "speed":    "5042334757040423886",
    "auth":     "5431895003821513760",
    "live":     "5825434651717127160",
    "stats":    "5231200819986047254",
    "settings": "5823103619665777239",
    "back":     "5972072533833289156",
    "close":    "5039598514980520994",
}


def first_page(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["H_B_1"],
                callback_data="help_callback hb1_p1",
                style="primary",
                icon_custom_emoji_id=_ICONS["play"],
            ),
            InlineKeyboardButton(
                text=_["H_B_2"],
                callback_data="help_callback hb2_p1",
                style="primary",
                icon_custom_emoji_id=_ICONS["controls"],
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["H_B_3"],
                callback_data="help_callback hb3_p1",
                style="primary",
                icon_custom_emoji_id=_ICONS["queue"],
            ),
            InlineKeyboardButton(
                text=_["H_B_4"],
                callback_data="help_callback hb4_p1",
                style="primary",
                icon_custom_emoji_id=_ICONS["loop"],
            ),
            InlineKeyboardButton(
                text=_["H_B_5"],
                callback_data="help_callback hb5_p1",
                style="primary",
                icon_custom_emoji_id=_ICONS["seek"],
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["H_B_6"],
                callback_data="help_callback hb6_p1",
                style="primary",
                icon_custom_emoji_id=_ICONS["speed"],
            ),
            InlineKeyboardButton(
                text=_["H_B_7"],
                callback_data="help_callback hb7_p1",
                style="primary",
                icon_custom_emoji_id=_ICONS["auth"],
            ),
            InlineKeyboardButton(
                text=_["H_B_8"],
                callback_data="help_callback hb8_p1",
                style="primary",
                icon_custom_emoji_id=_ICONS["live"],
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["H_B_9"],
                callback_data="help_callback hb9_p1",
                style="primary",
                icon_custom_emoji_id=_ICONS["stats"],
            ),
            InlineKeyboardButton(
                text=_["H_B_10"],
                callback_data="help_callback hb10_p1",
                style="primary",
                icon_custom_emoji_id=_ICONS["settings"],
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["BACK_BUTTON"],
                callback_data="back_to_main",
                style="success",
                icon_custom_emoji_id=_ICONS["back"],
            ),
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data="close",
                style="danger",
                icon_custom_emoji_id=_ICONS["close"],
            ),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def second_page(_):
    return first_page(_)


def action_sub_menu(_, current_page: int):
    return help_back_markup(_, current_page)


def help_back_markup(_, current_page: int):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=_["BACK_BUTTON"],
                    callback_data=f"help_back_{current_page}",
                    style="primary",
                    icon_custom_emoji_id=_ICONS["back"],
                ),
                InlineKeyboardButton(
                    text=_["CLOSE_BUTTON"],
                    callback_data="close",
                    style="danger",
                    icon_custom_emoji_id=_ICONS["close"],
                ),
            ]
        ]
    )


def private_help_panel(_):
    return [
        [
            InlineKeyboardButton(
                text=_["S_B_3"],
                url=f"https://t.me/{app.username}?start=help",
                style="success",
                icon_custom_emoji_id=_ICONS["play"],
            ),
        ],
    ]
