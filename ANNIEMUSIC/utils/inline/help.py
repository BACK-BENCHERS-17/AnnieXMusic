from . import InlineKeyboardButton
from pyrogram.types import InlineKeyboardMarkup
from ANNIEMUSIC import app

TOTAL_SECTIONS = 10
SKIP_SECTIONS = set()


def first_page(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["H_B_1"],
                callback_data="help_callback hb1_p1",
                style="primary",
            ),
            InlineKeyboardButton(
                text=_["H_B_2"],
                callback_data="help_callback hb2_p1",
                style="primary",
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["H_B_3"],
                callback_data="help_callback hb3_p1",
                style="primary",
            ),
            InlineKeyboardButton(
                text=_["H_B_4"],
                callback_data="help_callback hb4_p1",
                style="primary",
            ),
            InlineKeyboardButton(
                text=_["H_B_5"],
                callback_data="help_callback hb5_p1",
                style="primary",
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["H_B_6"],
                callback_data="help_callback hb6_p1",
                style="primary",
            ),
            InlineKeyboardButton(
                text=_["H_B_7"],
                callback_data="help_callback hb7_p1",
                style="primary",
            ),
            InlineKeyboardButton(
                text=_["H_B_8"],
                callback_data="help_callback hb8_p1",
                style="primary",
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["H_B_9"],
                callback_data="help_callback hb9_p1",
                style="primary",
            ),
            InlineKeyboardButton(
                text=_["H_B_10"],
                callback_data="help_callback hb10_p1",
                style="primary",
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["BACK_BUTTON"],
                callback_data="back_to_main",
                style="success",
            ),
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data="close",
                style="danger",
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
                ),
                InlineKeyboardButton(
                    text=_["CLOSE_BUTTON"],
                    callback_data="close",
                    style="danger",
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
            ),
        ],
    ]
