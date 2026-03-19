from . import InlineKeyboardButton
from ANNIEMUSIC.utils.formatters import time_to_seconds
from config import BOT_USERNAME


def generate_progress_bar(played_sec, duration_sec):
    if duration_sec == 0:
        percentage = 0
    else:
        percentage = min((played_sec / duration_sec) * 100, 100)
    bar_length = 11
    filled = max(0, min(int(round(bar_length * percentage / 100)), bar_length))
    return "▰" * filled + "▱" * (bar_length - filled)


def track_markup(_, videoid, user_id, channel, fplay):
    return [
        [
            InlineKeyboardButton(
                text=_["P_B_1"],
                callback_data=f"MusicStream {videoid}|{user_id}|a|{channel}|{fplay}",
                style="success"
            ),
            InlineKeyboardButton(
                text=_["P_B_2"],
                callback_data=f"MusicStream {videoid}|{user_id}|v|{channel}|{fplay}",
                style="success"
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data=f"forceclose {videoid}|{user_id}",
                style="danger"
            )
        ],
    ]


def control_buttons(_, chat_id, autoplay_on=None):
    if autoplay_on is True:
        ap_text  = "✅ ᴀᴜᴛᴏᴘʟᴀʏ : ᴏɴ"
        ap_style = "success"
    else:
        ap_text  = "❌ ᴀᴜᴛᴏᴘʟᴀʏ : ᴏꜰꜰ"
        ap_style = "danger"

    return [
        [
            InlineKeyboardButton(
                text="▷",
                callback_data=f"ADMIN Resume|{chat_id}",
                style="success"
            ),
            InlineKeyboardButton(
                text="II",
                callback_data=f"ADMIN Pause|{chat_id}",
                style="primary"
            ),
            InlineKeyboardButton(
                text="↻",
                callback_data=f"ADMIN Replay|{chat_id}",
                style="primary"
            ),
            InlineKeyboardButton(
                text="‣‣I",
                callback_data=f"ADMIN Skip|{chat_id}",
                style="primary"
            ),
            InlineKeyboardButton(
                text="▢",
                callback_data=f"ADMIN Stop|{chat_id}",
                style="danger"
            ),
        ],
        [
            InlineKeyboardButton(
                text=ap_text,
                callback_data=f"ADMIN Autoplay|{chat_id}",
                style=ap_style,
            ),
        ],
    ]


def stream_markup_timer(_, chat_id, played, dur, autoplay_on=None):
    played_sec   = time_to_seconds(played)
    duration_sec = time_to_seconds(dur)
    bar          = generate_progress_bar(played_sec, duration_sec)

    bot_url = f"https://t.me/{BOT_USERNAME}" if BOT_USERNAME else "https://t.me/ANNIEXMUSICxBOT"
    progress_row = [
        InlineKeyboardButton(
            text=f"⏱ {played}  {bar}  {dur}",
            url=bot_url,
            style="primary"
        )
    ]

    return (
        [progress_row]
        + control_buttons(_, chat_id, autoplay_on=autoplay_on)
        + [[InlineKeyboardButton(text=_["CLOSE_BUTTON"], callback_data="close", style="danger")]]
    )


def stream_markup(_, chat_id, autoplay_on=None):
    return (
        control_buttons(_, chat_id, autoplay_on=autoplay_on)
        + [[InlineKeyboardButton(text=_["CLOSE_BUTTON"], callback_data="close", style="danger")]]
    )


def playlist_markup(_, videoid, user_id, ptype, channel, fplay):
    return [
        [
            InlineKeyboardButton(
                text=_["P_B_1"],
                callback_data=f"AnniePlaylists {videoid}|{user_id}|{ptype}|a|{channel}|{fplay}",
                style="success"
            ),
            InlineKeyboardButton(
                text=_["P_B_2"],
                callback_data=f"AnniePlaylists {videoid}|{user_id}|{ptype}|v|{channel}|{fplay}",
                style="success"
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data=f"forceclose {videoid}|{user_id}",
                style="danger"
            ),
        ],
    ]


def livestream_markup(_, videoid, user_id, mode, channel, fplay):
    return [
        [
            InlineKeyboardButton(
                text=_["P_B_3"],
                callback_data=f"LiveStream {videoid}|{user_id}|{mode}|{channel}|{fplay}",
                style="success"
            )
        ],
        [
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data=f"forceclose {videoid}|{user_id}",
                style="danger"
            )
        ],
    ]


def slider_markup(_, videoid, user_id, query, query_type, channel, fplay):
    short_query = query[:20]
    return [
        [
            InlineKeyboardButton(
                text=_["P_B_1"],
                callback_data=f"MusicStream {videoid}|{user_id}|a|{channel}|{fplay}",
                style="success"
            ),
            InlineKeyboardButton(
                text=_["P_B_2"],
                callback_data=f"MusicStream {videoid}|{user_id}|v|{channel}|{fplay}",
                style="success"
            ),
        ],
        [
            InlineKeyboardButton(
                text="◁",
                callback_data=f"slider B|{query_type}|{short_query}|{user_id}|{channel}|{fplay}",
                style="primary"
            ),
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data=f"forceclose {short_query}|{user_id}",
                style="danger"
            ),
            InlineKeyboardButton(
                text="▷",
                callback_data=f"slider F|{query_type}|{short_query}|{user_id}|{channel}|{fplay}",
                style="primary"
            ),
        ],
    ]
