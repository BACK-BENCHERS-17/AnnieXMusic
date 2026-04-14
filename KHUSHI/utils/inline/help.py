from . import InlineKeyboardButton
from pyrogram.types import InlineKeyboardMarkup

TOTAL_SECTIONS = 8
SKIP_SECTIONS = set()
_PAGE1_LAST = 8


def first_page(_):
    """Help menu — all 8 categories in one page."""
    buttons = [
        [
            InlineKeyboardButton(text=_["H_B_1"], callback_data="help_callback hb1_p1", style="primary"),
            InlineKeyboardButton(text=_["H_B_2"], callback_data="help_callback hb2_p1", style="primary"),
        ],
        [
            InlineKeyboardButton(text=_["H_B_3"], callback_data="help_callback hb3_p1", style="primary"),
            InlineKeyboardButton(text=_["H_B_4"], callback_data="help_callback hb4_p1", style="primary"),
            InlineKeyboardButton(text=_["H_B_5"], callback_data="help_callback hb5_p1", style="primary"),
        ],
        [
            InlineKeyboardButton(text=_["H_B_6"], callback_data="help_callback hb6_p1", style="primary"),
            InlineKeyboardButton(text=_["H_B_7"], callback_data="help_callback hb7_p1", style="primary"),
            InlineKeyboardButton(text=_["H_B_8"], callback_data="help_callback hb8_p1", style="primary"),
        ],
        [
            InlineKeyboardButton(
                text=_["BACK_BUTTON"],
                callback_data="khushi_back",
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
    """Alias — no second page anymore, returns first_page."""
    return first_page(_)


def action_sub_menu(_, current_page: int):
    return help_nav_markup(_, current_page)


def help_nav_markup(_, section: int):
    """Navigation markup inside a help section — back to menu + Prev + Next (loop)."""
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
                text="◁  ᴩʀᴇᴠ",
                callback_data=f"help_nav_{prev_s}",
                style="default",
            ),
            InlineKeyboardButton(
                text="ɴᴇxᴛ  ▷",
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
