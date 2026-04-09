import os
import pyrogram.enums as enums_pkg

enums_dir = os.path.dirname(enums_pkg.__file__)
init_path  = os.path.join(enums_dir, "__init__.py")
bs_path    = os.path.join(enums_dir, "button_style.py")

if not os.path.exists(bs_path):
    print("button_style.py not found — creating stub")
    with open(bs_path, "w") as f:
        f.write(
            "from enum import IntEnum\n\n"
            "class ButtonStyle(IntEnum):\n"
            "    DEFAULT = 0\n"
            "    PRIMARY = 1\n"
            "    SUCCESS = 2\n"
            "    DANGER  = 3\n"
        )

with open(init_path, "r") as f:
    content = f.read()

if "ButtonStyle" not in content:
    with open(init_path, "a") as f:
        f.write("\nfrom .button_style import ButtonStyle\n")
    print("Patched: ButtonStyle exported into pyrogram.enums")
else:
    print("ButtonStyle already exported — no patch needed")
