"""
patch_pyrogram.py — Ensures pyrofork/kurigram/pyrogram has full TL Layer 222
                    with ButtonStyle (coloured buttons) support.

Designed to be a SAFE NO-OP when kurigram==2.2.19 is installed (which already
has everything correct).  Only writes/patches when the installed library has
old Layer 220 IDs or is missing ButtonStyle entirely.

Applied steps:
  1. Ensure button_style.py enum exists   (pyrogram.enums.ButtonStyle)
  2. Export ButtonStyle from pyrogram.enums
  3. Write KeyboardButtonStyle raw TL type — only if missing or wrong ID
  4. Upgrade KeyboardButtonCallback        — only if ID ≠ 0xe62bc960
  5. Upgrade KeyboardButtonUrl             — only if ID ≠ 0xd80c25ec
  6. Upgrade KeyboardButtonSwitchInline    — only if ID ≠ 0x991399fc
  7. Update raw/all.py                     — layer const + type-ID mappings
  8. Export KeyboardButtonStyle from raw.types
  9. Patch InlineKeyboardButton.write()    — only if not already async+KBS
 10. Reload all pyrogram modules and verify
"""

import os
import re
import sys

import pyrogram.enums as _enums_pkg

_pyro_root    = os.path.dirname(os.path.dirname(_enums_pkg.__file__))
_enums_dir    = os.path.dirname(_enums_pkg.__file__)
_raw_types_dir = os.path.join(_pyro_root, "raw", "types")
_raw_dir       = os.path.join(_pyro_root, "raw")
_bk_dir        = os.path.join(_pyro_root, "types", "bots_and_keyboards")

# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

def _file_has_id(path: str, hex_id: str) -> bool:
    """Return True when the file already contains the given hex ID string."""
    if not os.path.exists(path):
        return False
    with open(path) as f:
        return hex_id.lower() in f.read().lower()


def _write_file(path: str, content: str, label: str) -> None:
    with open(path, "w") as f:
        f.write(content)
    print(f"[patch] {label} written")


def _reload_pyrogram() -> None:
    for key in list(sys.modules.keys()):
        if key == "pyrogram" or key.startswith("pyrogram."):
            del sys.modules[key]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — button_style.py
# ─────────────────────────────────────────────────────────────────────────────
_bs_path = os.path.join(_enums_dir, "button_style.py")
if not os.path.exists(_bs_path):
    _write_file(_bs_path, '''\
from enum import auto

try:
    from .auto_name import AutoName

    class ButtonStyle(AutoName):
        DEFAULT = auto()
        PRIMARY = auto()
        DANGER  = auto()
        SUCCESS = auto()
except ImportError:
    from enum import IntEnum

    class ButtonStyle(IntEnum):
        DEFAULT = 0
        PRIMARY = 1
        DANGER  = 3
        SUCCESS = 2
''', "pyrogram/enums/button_style.py")
else:
    print("[patch] pyrogram/enums/button_style.py exists — skipping")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — export ButtonStyle from pyrogram.enums.__init__
# ─────────────────────────────────────────────────────────────────────────────
_enums_init = os.path.join(_enums_dir, "__init__.py")
with open(_enums_init) as f:
    _enums_content = f.read()
if "ButtonStyle" not in _enums_content:
    with open(_enums_init, "a") as f:
        f.write("\nfrom .button_style import ButtonStyle\n")
    print("[patch] ButtonStyle exported from pyrogram.enums")
else:
    print("[patch] ButtonStyle already in pyrogram.enums.__init__ — skipping")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — KeyboardButtonStyle raw TL type  (Layer 222, ID 0x4fdd3430)
# ─────────────────────────────────────────────────────────────────────────────
_kbs_path = os.path.join(_raw_types_dir, "keyboard_button_style.py")
if not _file_has_id(_kbs_path, "0x4fdd3430"):
    _write_file(_kbs_path, '''\
from io import BytesIO
from typing import List, Optional, Any

from pyrogram.raw.core.primitives import Int, Long, Int128, Int256, Bool, Bytes, String, Double, Vector
from pyrogram.raw.core import TLObject


class KeyboardButtonStyle(TLObject):
    """Layer 222 — ID 4FDD3430"""

    __slots__: List[str] = ["bg_primary", "bg_danger", "bg_success", "icon"]

    ID = 0x4fdd3430
    QUALNAME = "types.KeyboardButtonStyle"

    def __init__(self, *, bg_primary: Optional[bool] = None,
                 bg_danger: Optional[bool] = None,
                 bg_success: Optional[bool] = None,
                 icon: Optional[int] = None) -> None:
        self.bg_primary = bg_primary
        self.bg_danger  = bg_danger
        self.bg_success = bg_success
        self.icon       = icon

    @staticmethod
    def read(b: BytesIO, *args: Any) -> "KeyboardButtonStyle":
        flags      = Int.read(b)
        bg_primary = bool(flags & (1 << 0))
        bg_danger  = bool(flags & (1 << 1))
        bg_success = bool(flags & (1 << 2))
        icon       = Long.read(b) if flags & (1 << 3) else None
        return KeyboardButtonStyle(bg_primary=bg_primary, bg_danger=bg_danger,
                                   bg_success=bg_success, icon=icon)

    def write(self, *args) -> bytes:
        b = BytesIO()
        b.write(Int(self.ID, False))
        flags  = 0
        flags |= (1 << 0) if self.bg_primary else 0
        flags |= (1 << 1) if self.bg_danger  else 0
        flags |= (1 << 2) if self.bg_success else 0
        flags |= (1 << 3) if self.icon is not None else 0
        b.write(Int(flags))
        if self.icon is not None:
            b.write(Long(self.icon))
        return b.getvalue()
''', "pyrogram/raw/types/keyboard_button_style.py")
else:
    print("[patch] KeyboardButtonStyle already has correct ID 0x4fdd3430 — skipping")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — KeyboardButtonCallback  (Layer 222, ID 0xe62bc960)
# ─────────────────────────────────────────────────────────────────────────────
_kbc_path = os.path.join(_raw_types_dir, "keyboard_button_callback.py")
if not _file_has_id(_kbc_path, "0xe62bc960"):
    _write_file(_kbc_path, '''\
from io import BytesIO
from typing import TYPE_CHECKING, List, Optional, Any

from pyrogram.raw.core.primitives import Int, Long, Int128, Int256, Bool, Bytes, String, Double, Vector
from pyrogram.raw.core import TLObject

if TYPE_CHECKING:
    from pyrogram import raw


class KeyboardButtonCallback(TLObject):
    """Layer 222 — ID E62BC960"""

    __slots__: List[str] = ["text", "data", "requires_password", "style"]

    ID = 0xe62bc960
    QUALNAME = "types.KeyboardButtonCallback"

    def __init__(self, *, text: str, data: bytes,
                 requires_password: Optional[bool] = None,
                 style: "raw.base.KeyboardButtonStyle" = None) -> None:
        self.text               = text
        self.data               = data
        self.requires_password  = requires_password
        self.style              = style

    @staticmethod
    def read(b: BytesIO, *args: Any) -> "KeyboardButtonCallback":
        flags              = Int.read(b)
        requires_password  = bool(flags & (1 << 0))
        style              = TLObject.read(b) if flags & (1 << 10) else None
        text               = String.read(b)
        data               = Bytes.read(b)
        return KeyboardButtonCallback(text=text, data=data,
                                      requires_password=requires_password, style=style)

    def write(self, *args) -> bytes:
        b = BytesIO()
        b.write(Int(self.ID, False))
        flags  = 0
        flags |= (1 << 0)  if self.requires_password else 0
        flags |= (1 << 10) if self.style is not None  else 0
        b.write(Int(flags))
        if self.style is not None:
            b.write(self.style.write())
        b.write(String(self.text))
        b.write(Bytes(self.data))
        return b.getvalue()
''', "pyrogram/raw/types/keyboard_button_callback.py")
else:
    print("[patch] KeyboardButtonCallback already has correct ID 0xe62bc960 — skipping")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — KeyboardButtonUrl  (Layer 222, ID 0xd80c25ec)
# ─────────────────────────────────────────────────────────────────────────────
_kbu_path = os.path.join(_raw_types_dir, "keyboard_button_url.py")
if not _file_has_id(_kbu_path, "0xd80c25ec"):
    _write_file(_kbu_path, '''\
from io import BytesIO
from typing import TYPE_CHECKING, List, Optional, Any

from pyrogram.raw.core.primitives import Int, Long, Int128, Int256, Bool, Bytes, String, Double, Vector
from pyrogram.raw.core import TLObject

if TYPE_CHECKING:
    from pyrogram import raw


class KeyboardButtonUrl(TLObject):
    """Layer 222 — ID D80C25EC"""

    __slots__: List[str] = ["text", "url", "style"]

    ID = 0xd80c25ec
    QUALNAME = "types.KeyboardButtonUrl"

    def __init__(self, *, text: str, url: str,
                 style: "raw.base.KeyboardButtonStyle" = None) -> None:
        self.text  = text
        self.url   = url
        self.style = style

    @staticmethod
    def read(b: BytesIO, *args: Any) -> "KeyboardButtonUrl":
        flags  = Int.read(b)
        style  = TLObject.read(b) if flags & (1 << 10) else None
        text   = String.read(b)
        url    = String.read(b)
        return KeyboardButtonUrl(text=text, url=url, style=style)

    def write(self, *args) -> bytes:
        b = BytesIO()
        b.write(Int(self.ID, False))
        flags  = 0
        flags |= (1 << 10) if self.style is not None else 0
        b.write(Int(flags))
        if self.style is not None:
            b.write(self.style.write())
        b.write(String(self.text))
        b.write(String(self.url))
        return b.getvalue()
''', "pyrogram/raw/types/keyboard_button_url.py")
else:
    print("[patch] KeyboardButtonUrl already has correct ID 0xd80c25ec — skipping")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — KeyboardButtonSwitchInline  (Layer 222, ID 0x991399fc)
# ─────────────────────────────────────────────────────────────────────────────
_kbsi_path = os.path.join(_raw_types_dir, "keyboard_button_switch_inline.py")
if not _file_has_id(_kbsi_path, "0x991399fc"):
    _write_file(_kbsi_path, '''\
from io import BytesIO
from typing import TYPE_CHECKING, List, Optional, Any

from pyrogram.raw.core.primitives import Int, Long, Int128, Int256, Bool, Bytes, String, Double, Vector
from pyrogram.raw.core import TLObject

if TYPE_CHECKING:
    from pyrogram import raw


class KeyboardButtonSwitchInline(TLObject):
    """Layer 222 — ID 991399FC"""

    __slots__: List[str] = ["text", "query", "same_peer", "style", "peer_types"]

    ID = 0x991399fc
    QUALNAME = "types.KeyboardButtonSwitchInline"

    def __init__(self, *, text: str, query: str,
                 same_peer: Optional[bool] = None,
                 style: "raw.base.KeyboardButtonStyle" = None,
                 peer_types: Optional[List["raw.base.InlineQueryPeerType"]] = None) -> None:
        self.text       = text
        self.query      = query
        self.same_peer  = same_peer
        self.style      = style
        self.peer_types = peer_types

    @staticmethod
    def read(b: BytesIO, *args: Any) -> "KeyboardButtonSwitchInline":
        flags      = Int.read(b)
        same_peer  = bool(flags & (1 << 0))
        style      = TLObject.read(b) if flags & (1 << 10) else None
        text       = String.read(b)
        query      = String.read(b)
        peer_types = TLObject.read(b) if flags & (1 << 1) else []
        return KeyboardButtonSwitchInline(text=text, query=query, same_peer=same_peer,
                                          style=style, peer_types=peer_types)

    def write(self, *args) -> bytes:
        b = BytesIO()
        b.write(Int(self.ID, False))
        flags  = 0
        flags |= (1 << 0)  if self.same_peer  else 0
        flags |= (1 << 10) if self.style is not None else 0
        flags |= (1 << 1)  if self.peer_types else 0
        b.write(Int(flags))
        if self.style is not None:
            b.write(self.style.write())
        b.write(String(self.text))
        b.write(String(self.query))
        if self.peer_types:
            b.write(Vector(self.peer_types))
        return b.getvalue()
''', "pyrogram/raw/types/keyboard_button_switch_inline.py")
else:
    print("[patch] KeyboardButtonSwitchInline already has correct ID 0x991399fc — skipping")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — raw/all.py: update layer constant + type-ID mappings
# ─────────────────────────────────────────────────────────────────────────────
_all_py = os.path.join(_raw_dir, "all.py")
if os.path.exists(_all_py):
    with open(_all_py) as f:
        _all_content = f.read()

    _changed = False

    if re.search(r"layer\s*=\s*2[01]\d", _all_content):
        _all_content = re.sub(r"(layer\s*=\s*)2[01]\d", r"\g<1>222", _all_content)
        _changed = True

    _id_replacements = {
        "0x35bbdb6b": "0xe62bc960",
        "0x258aff05": "0xd80c25ec",
        "0x93b9fbb5": "0x991399fc",
    }
    for old_id, new_id in _id_replacements.items():
        if old_id in _all_content and new_id not in _all_content:
            _all_content = _all_content.replace(old_id, new_id)
            _changed = True

    _kbs_mapping = '    0x4fdd3430: "pyrogram.raw.types.KeyboardButtonStyle",\n'
    if "0x4fdd3430" not in _all_content:
        _all_content = _all_content.replace(
            "objects = {\n",
            "objects = {\n" + _kbs_mapping,
            1
        )
        _changed = True

    if _changed:
        with open(_all_py, "w") as f:
            f.write(_all_content)
        print("[patch] raw/all.py updated (layer + IDs)")
    else:
        print("[patch] raw/all.py already correct — skipping")
else:
    print("[patch] raw/all.py not found — skipping")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — export KeyboardButtonStyle from raw.types.__init__
# ─────────────────────────────────────────────────────────────────────────────
_rt_init = os.path.join(_raw_types_dir, "__init__.py")
if os.path.exists(_rt_init):
    with open(_rt_init) as f:
        _rt_content = f.read()
    if "KeyboardButtonStyle" not in _rt_content:
        with open(_rt_init, "a") as f:
            f.write("\nfrom .keyboard_button_style import KeyboardButtonStyle\n")
        print("[patch] KeyboardButtonStyle exported from pyrogram.raw.types")
    else:
        print("[patch] KeyboardButtonStyle already in raw.types.__init__ — skipping")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 9 — patch InlineKeyboardButton.write() if not already async + KBS
#
# CRITICAL: InlineKeyboardMarkup.write() calls `await b.write(client)`.
# write() MUST be an async coroutine.  A sync def raises:
#   "TypeError: object KeyboardButtonXxx can't be used in 'await' expression"
# ─────────────────────────────────────────────────────────────────────────────
_ikb_path = os.path.join(_bk_dir, "inline_keyboard_button.py")
if os.path.exists(_ikb_path):
    with open(_ikb_path) as f:
        _ikb_src = f.read()

    _already_ok = ("KeyboardButtonStyle" in _ikb_src) and ("async def write" in _ikb_src)

    if not _already_ok:
        print("[patch] Patching InlineKeyboardButton.write() (async) …")

        _NEW_WRITE = '''
    async def write(self, client):
        # ButtonStyle patch — injected by patch_pyrogram.py
        try:
            from pyrogram.enums import ButtonStyle as _BS
            from pyrogram.raw.types import KeyboardButtonStyle as _KBS
            _s    = getattr(self, "style", _BS.DEFAULT)
            _icon = getattr(self, "icon_custom_emoji_id", None)
            _style_obj = _KBS(
                bg_primary=(_s == _BS.PRIMARY),
                bg_danger =(_s == _BS.DANGER),
                bg_success=(_s == _BS.SUCCESS),
                icon=_icon,
            ) if (_s != _BS.DEFAULT or _icon is not None) else None
        except Exception:
            _style_obj = None

        if self.callback_data is not None:
            data = bytes(self.callback_data, "utf-8") if isinstance(self.callback_data, str) else self.callback_data
            return raw.types.KeyboardButtonCallback(
                text=self.text, data=data,
                requires_password=self.requires_password, style=_style_obj)

        if self.url is not None:
            return raw.types.KeyboardButtonUrl(text=self.text, url=self.url, style=_style_obj)

        if getattr(self, "login_url", None) is not None:
            return self.login_url.write(
                text=self.text,
                bot=await client.resolve_peer(self.login_url.bot_username or "self"),
                style=_style_obj,
            )

        if getattr(self, "user_id", None) is not None:
            return raw.types.InputKeyboardButtonUserProfile(
                text=self.text,
                user_id=await client.resolve_peer(self.user_id),
                style=_style_obj,
            )

        if self.switch_inline_query is not None:
            return raw.types.KeyboardButtonSwitchInline(
                text=self.text, query=self.switch_inline_query, style=_style_obj)

        if self.switch_inline_query_current_chat is not None:
            return raw.types.KeyboardButtonSwitchInline(
                text=self.text, query=self.switch_inline_query_current_chat,
                same_peer=True, style=_style_obj)

        if self.callback_game is not None:
            return raw.types.KeyboardButtonGame(text=self.text)

        if self.web_app is not None:
            return raw.types.KeyboardButtonWebView(text=self.text, url=self.web_app.url)

        if self.pay is not None:
            return raw.types.KeyboardButtonBuy(text=self.text)

        if getattr(self, "copy_text", None) is not None:
            try:
                return raw.types.KeyboardButtonCopy(text=self.text, copy_text=self.copy_text)
            except Exception:
                pass

        return raw.types.KeyboardButton(text=self.text)

'''
        _m = re.search(r'\n    (?:async )?def write\(self.*?\n    (?=def |\Z)', _ikb_src, re.DOTALL)
        if _m:
            _ikb_src = _ikb_src[:_m.start()] + "\n" + _NEW_WRITE + "    " + _ikb_src[_m.end():]
        else:
            _ikb_src += "\n" + _NEW_WRITE

        with open(_ikb_path, "w") as f:
            f.write(_ikb_src)
        print("[patch] InlineKeyboardButton.write() patched (async)")
    else:
        print("[patch] InlineKeyboardButton.write() already async+KeyboardButtonStyle — skipping")

    # Ensure __init__ has style + icon params (kurigram already has them)
    with open(_ikb_path) as f:
        _ikb_src2 = f.read()
    if "self.style" not in _ikb_src2:
        _m2 = re.search(r'(def __init__\(self.*?super\(\).__init__\(\))', _ikb_src2, re.DOTALL)
        if _m2:
            _orig = _m2.group(1)
            if "style" not in _orig:
                _patched = _orig.rstrip(")") + ",\n        style=None\n    )\n        self.style = style"
                _ikb_src2 = _ikb_src2.replace(_orig, _patched, 1)
                with open(_ikb_path, "w") as f:
                    f.write(_ikb_src2)
                print("[patch] style param added to IKB.__init__")
else:
    print("[patch] WARNING: inline_keyboard_button.py not found — skipping")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 10 — reload & verify
# ─────────────────────────────────────────────────────────────────────────────
_reload_pyrogram()

try:
    from pyrogram.enums import ButtonStyle
    print(f"[patch] ButtonStyle.SUCCESS = {ButtonStyle.SUCCESS!r}")
except Exception as e:
    print(f"[patch] VERIFY FAILED (ButtonStyle): {e}")
    sys.exit(1)

try:
    from pyrogram.raw.types import KeyboardButtonStyle, KeyboardButtonCallback
    assert KeyboardButtonCallback.ID == 0xe62bc960, f"Wrong KBC ID: {hex(KeyboardButtonCallback.ID)}"
    assert KeyboardButtonStyle.ID  == 0x4fdd3430, f"Wrong KBS ID: {hex(KeyboardButtonStyle.ID)}"
    print(f"[patch] KeyboardButtonCallback ID = {hex(KeyboardButtonCallback.ID)} ✓")
    print(f"[patch] KeyboardButtonStyle    ID = {hex(KeyboardButtonStyle.ID)} ✓")
except Exception as e:
    print(f"[patch] VERIFY FAILED (raw types): {e}")
    sys.exit(1)

import inspect as _inspect
try:
    from pyrogram.types import InlineKeyboardButton as _IKB
    _ikb_src_check = _inspect.getsource(_IKB.write)
    assert "async def write" in _ikb_src_check, "write() is not async!"
    assert "KeyboardButtonStyle" in _ikb_src_check or "KeyboardButtonCallback" in _ikb_src_check, \
        "write() doesn't build KeyboardButton objects!"
    print("[patch] InlineKeyboardButton.write() is async ✓")
except Exception as e:
    print(f"[patch] VERIFY FAILED (IKB write): {e}")
    sys.exit(1)

print("[patch] All patches applied — button colours will work on Railway.")
