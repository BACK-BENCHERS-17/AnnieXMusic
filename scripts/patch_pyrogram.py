import os
import sys
import pyrogram.enums as enums_pkg

enums_dir = os.path.dirname(enums_pkg.__file__)
init_path  = os.path.join(enums_dir, "__init__.py")
bs_path    = os.path.join(enums_dir, "button_style.py")

# ── Step 1: create button_style.py if missing ────────────────────────────────
if not os.path.exists(bs_path):
    print("button_style.py not found — creating AutoName stub")
    with open(bs_path, "w") as f:
        f.write(
            "from enum import auto\n\n"
            "try:\n"
            "    from .auto_name import AutoName\n"
            "    class ButtonStyle(AutoName):\n"
            "        DEFAULT = auto()\n"
            "        PRIMARY = auto()\n"
            "        DANGER  = auto()\n"
            "        SUCCESS = auto()\n"
            "except ImportError:\n"
            "    from enum import IntEnum\n"
            "    class ButtonStyle(IntEnum):\n"
            "        DEFAULT = 0\n"
            "        PRIMARY = 1\n"
            "        DANGER  = 3\n"
            "        SUCCESS = 2\n"
        )
else:
    print("button_style.py already exists — skipping creation")

# ── Step 2: export ButtonStyle from enums __init__ ───────────────────────────
with open(init_path, "r") as f:
    content = f.read()

if "ButtonStyle" not in content:
    with open(init_path, "a") as f:
        f.write("\nfrom .button_style import ButtonStyle\n")
    print("Patched: ButtonStyle exported into pyrogram.enums")
else:
    print("ButtonStyle already exported — no patch needed")

# ── Step 3: ensure InlineKeyboardButton.write() sends button style ───────────
import pyrogram.types.bots_and_keyboards.inline_keyboard_button as ikb_mod
import inspect

ikb_path = inspect.getfile(ikb_mod)
with open(ikb_path, "r") as f:
    ikb_src = f.read()

if "KeyboardButtonStyle" in ikb_src:
    print("InlineKeyboardButton.write() already has KeyboardButtonStyle — OK")
else:
    print("InlineKeyboardButton.write() is missing KeyboardButtonStyle — patching…")
    # Replace the write() method signature to inject style handling
    # We inject a thin wrapper that checks for the ButtonStyle parameter
    old_write_start = "def write(self, client"
    if old_write_start not in ikb_src:
        print("WARNING: Could not find write() method — skipping write patch")
    else:
        # Find where write() starts and patch it by injecting the style block
        # We need to add the KeyboardButtonStyle construction and pass it through
        # Strategy: find callback_data section and inject style creation before it

        # Build the new write method content
        style_block = '''def write(self, client):
        # ButtonStyle patch — injected by patch_pyrogram.py
        try:
            from pyrogram import enums as _enums
            _bs = _enums.ButtonStyle
            _style = getattr(self, "style", _bs.DEFAULT)
            if _style != _bs.DEFAULT or getattr(self, "icon_custom_emoji_id", None) is not None:
                from pyrogram import raw as _raw
                _style_obj = _raw.types.KeyboardButtonStyle(
                    bg_primary=_style == _bs.PRIMARY,
                    bg_danger=_style == _bs.DANGER,
                    bg_success=_style == _bs.SUCCESS,
                    icon=getattr(self, "icon_custom_emoji_id", None),
                )
            else:
                _style_obj = None
        except Exception:
            _style_obj = None

        if self.callback_data is not None:
            data = bytes(self.callback_data, "utf-8") if isinstance(self.callback_data, str) else self.callback_data
            from pyrogram import raw as _raw2
            return _raw2.types.KeyboardButtonCallback(
                text=self.text,
                data=data,
                requires_password=getattr(self, "requires_password", None),
                style=_style_obj,
            )

        if self.url is not None:
            from pyrogram import raw as _raw2
            return _raw2.types.KeyboardButtonUrl(
                text=self.text,
                url=self.url,
                style=_style_obj,
            )

        from pyrogram import raw as _raw2
        return _raw2.types.KeyboardButtonCallback(
            text=self.text,
            data=b"noop",
            style=_style_obj,
        )
'''
        # Only patch if KeyboardButtonCallback supports style kwarg
        try:
            from pyrogram import raw
            import inspect as _ins
            cb_sig = _ins.signature(raw.types.KeyboardButtonCallback.__init__)
            if "style" in cb_sig.parameters:
                # Inject the patched write method into the class
                from pyrogram.types.bots_and_keyboards.inline_keyboard_button import InlineKeyboardButton
                exec(compile(f"class _Tmp:\n" + "\n".join("    " + l for l in style_block.splitlines()), "<patch>", "exec"), globals())
                InlineKeyboardButton.write = _Tmp.write
                print("InlineKeyboardButton.write() patched successfully in-memory")
            else:
                print("KeyboardButtonCallback does not support style kwarg — skipping write patch")
        except Exception as e:
            print(f"WARNING: Could not apply write() patch: {e}")

# ── Step 4: final verification ────────────────────────────────────────────────
try:
    from pyrogram.enums import ButtonStyle
    val = ButtonStyle.SUCCESS
    print(f"VERIFY: ButtonStyle.SUCCESS = {val!r}")
except Exception as e:
    print(f"VERIFY FAILED: {e}")
    sys.exit(1)
