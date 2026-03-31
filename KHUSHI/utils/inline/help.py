from . import InlineKeyboardButton
from pyrogram.types import InlineKeyboardMarkup

TOTAL_SECTIONS = 15
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
            InlineKeyboardButton(
                text=_["H_B_11"],
                callback_data="help_callback hb11_p1",
                style="primary",
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["H_B_12"],
                callback_data="help_callback hb12_p1",
                style="primary",
            ),
            InlineKeyboardButton(
                text=_["H_B_13"],
                callback_data="help_callback hb13_p1",
                style="primary",
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["H_B_14"],
                callback_data="help_callback hb14_p1",
                style="primary",
            ),
            InlineKeyboardButton(
                text=_["H_B_15"],
                callback_data="help_callback hb15_p1",
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
    return help_nav_markup(_, current_page)


def help_nav_markup(_, section: int):
    """Navigation markup shown inside a help section — Back to menu + Next (loops)."""
    next_s = (section % TOTAL_SECTIONS) + 1
    prev_s = ((section - 2) % TOTAL_SECTIONS) + 1
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text="˹ᴍᴇɴᴜ˼",
                callback_data="help_back_1",
                style="primary",
            ),
            InlineKeyboardButton(
                text=f"◀ {prev_s}",
                callback_data=f"help_nav_{prev_s}",
                style="default",
            ),
            InlineKeyboardButton(
                text=f"{next_s} ▶",
                callback_data=f"help_nav_{next_s}",
                style="success",
            ),
        ]
    ])


def help_back_markup(_, current_page: int):
    return help_nav_markup(_, current_page)


def private_help_panel(_):
    from KHUSHI import app
    return [
        [
            InlineKeyboardButton(
                text=_["S_B_3"],
                url=f"https://t.me/{app.username}?start=help",
                style="success",
            ),
        ],
    ]
