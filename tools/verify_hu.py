"""
Check every key of config/corne.keymap against the real Windows Hungarian layout.

For each binding it works out the HID key + modifiers the keyboard sends, asks
Windows (ToUnicodeEx with the 0000040E layout) what that types, and compares it
with the intended label (overlay/render_layout.py).  Windows only.

Run:  python tools/verify_hu.py
"""
import ctypes
import re
import sys
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "overlay"))
import render_layout as rl  # noqa: E402  (intended labels + keymap parser)

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.LoadKeyboardLayoutW.restype = wintypes.HKL
user32.MapVirtualKeyExW.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.HKL]
user32.ToUnicodeEx.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_char_p,
                               ctypes.c_wchar_p, ctypes.c_int, wintypes.UINT, wintypes.HKL]
HKL = user32.LoadKeyboardLayoutW("0000040E", 0x80)   # KLF_NOTELLSHELL, does not activate

# HID usage name -> PS/2 set-1 scan code (what Windows sees)
SC = {c: s for c, s in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
      [0x1E, 0x30, 0x2E, 0x20, 0x12, 0x21, 0x22, 0x23, 0x17, 0x24, 0x25, 0x26, 0x32,
       0x31, 0x18, 0x19, 0x10, 0x13, 0x1F, 0x14, 0x16, 0x2F, 0x11, 0x2D, 0x15, 0x2C])}
SC.update({f"N{(i + 1) % 10}": 0x02 + i for i in range(10)})
SC.update({"MINUS": 0x0C, "EQUAL": 0x0D, "LBKT": 0x1A, "RBKT": 0x1B, "BSLH": 0x2B,
           "NON_US_HASH": 0x2B, "SEMI": 0x27, "SQT": 0x28, "GRAVE": 0x29, "COMMA": 0x33,
           "DOT": 0x34, "FSLH": 0x35, "NON_US_BSLH": 0x56, "SPACE": 0x39})

VK_NAMES = {0x08: "Bksp", 0x09: "Tab", 0x0D: "Enter", 0x1B: "Esc", 0x20: "Space"}
for i in range(26):
    VK_NAMES[0x41 + i] = chr(0x41 + i)
for i in range(10):
    VK_NAMES[0x30 + i] = str(i)
VK_NAMES.update({0xBE: ".", 0xBC: ","})


def split_mods(code):
    """'LG(LS(S))' -> ({'LG','LS'}, 'S')"""
    mods = set()
    while True:
        m = re.fullmatch(r"(L[SCAG]|R[SCAG])\((.*)\)", code)
        if not m:
            return mods, code
        mods.add(m.group(1))
        code = m.group(2)


def type_char(key, shift=False, altgr=False):
    """What one key press types on the HU layout. Returns (text, dead)."""
    sc = SC[key]
    vk = user32.MapVirtualKeyExW(sc, 1, HKL)          # MAPVK_VSC_TO_VK
    state = bytearray(256)
    if shift:
        state[0x10] = state[0xA0] = 0x80
    if altgr:
        state[0x11] = state[0x12] = state[0xA2] = state[0xA5] = 0x80
    buf = ctypes.create_unicode_buffer(8)
    n = user32.ToUnicodeEx(vk, sc, bytes(state), buf, 8, 0, HKL)
    if n < 0:                                          # dead key: flush with space
        sp = ctypes.create_unicode_buffer(8)
        m = user32.ToUnicodeEx(0x20, 0x39, bytes(256), sp, 8, 0, HKL)
        return sp.value[:max(m, 0)], True
    return buf.value[:n], False


def _press(key, shift=False, altgr=False):
    sc = SC[key]
    vk = user32.MapVirtualKeyExW(sc, 1, HKL)
    state = bytearray(256)
    if shift:
        state[0x10] = state[0xA0] = 0x80
    if altgr:
        state[0x11] = state[0x12] = state[0xA2] = state[0xA5] = 0x80
    buf = ctypes.create_unicode_buffer(8)
    n = user32.ToUnicodeEx(vk, sc, bytes(state), buf, 8, 0, HKL)
    return buf.value[:n] if n > 0 else ""


def type_sequence(codes):
    """Type a macro key by key, keeping Windows' dead-key state between presses,
    exactly like the keyboard sends it. Returns the text that appears."""
    _press("SPACE"), _press("SPACE")                   # clear any pending dead key
    out = ""
    for c in codes:
        mods, key = split_mods(c)
        out += _press(key, shift=bool(mods & {"LS", "RS"}), altgr="RA" in mods)
    _press("SPACE"), _press("SPACE")
    return out


def vk_of(key):
    return user32.MapVirtualKeyExW(SC[key], 1, HKL)


def actual_kp(code):
    """What '&kp CODE' does on HU Windows, as a comparable label."""
    mods, key = split_mods(code)
    if key in SC and not (mods & {"LC", "RC", "LA", "LG", "RG"}):
        text, dead = type_char(key, shift=bool(mods & {"LS", "RS"}), altgr="RA" in mods)
        return text + (" (dead)" if dead else "")
    if key in SC:                                      # shortcut: apps see the VK, not the char
        parts = [n for m, n in (("LC", "Ctrl"), ("LA", "Alt"), ("LG", "Win"), ("LS", "Shift"))
                 if m in mods]
        return "+".join(parts + [VK_NAMES.get(vk_of(key), hex(vk_of(key)))])
    parts = [n for m, n in (("LC", "Ctrl"), ("LA", "Alt"), ("LG", "Win"), ("LS", "Shift"))
             if m in mods]
    return "+".join(parts + [key])


def hu_defines():
    text = (ROOT / "config" / "hu_keys.h").read_text(encoding="utf-8")
    return dict(re.findall(r"#define\s+(HU_\w+)\s+&kp\s+(\S+)", text))


def macros():
    text = (ROOT / "config" / "corne.keymap").read_text(encoding="utf-8")
    out = {}
    for name, body in re.findall(r"(\w+): \1 \{[^}]*?compatible = \"zmk,behavior-macro\";.*?bindings = (.*?);",
                                 text, re.S):
        out["&" + name] = re.findall(r"&kp (\S+?)[>\s]", body + " ")
    return out


# What each non-character binding is supposed to do on Windows
SHORTCUT_INTENT = {
    "Undo": "Ctrl+Z", "Redo": "Ctrl+Y", "Cut": "Ctrl+X", "Copy": "Ctrl+C", "Paste": "Ctrl+V",
    "Alt+F4": "Alt+F4", "Max": "Win+UP", "Min": "Win+DOWN", "Snap←": "Win+LEFT",
    "Snap→": "Win+RIGHT", "←Mon": "Win+Shift+LEFT", "Mon→": "Win+Shift+RIGHT",
    "←Dsk": "Ctrl+Win+LEFT", "Dsk→": "Ctrl+Win+RIGHT", "Task": "Win+TAB", "Space": " ",
    "Lock": "Win+L", "Desk": "Win+D", "Clip": "Win+V", "Snip": "Win+Shift+S",
}


def main():
    hu = hu_defines()
    mac = macros()
    problems, checked = [], 0
    for name, keys in rl.parse():
        for idx, (intended, head) in enumerate(keys):
            if not intended:
                continue
            raw = keys_raw[name][idx]
            if raw[0].startswith("HU_"):
                code = hu[raw[0]]
            elif raw[0] == "&kp":
                code = raw[1]
            elif raw[0] in mac:
                seq = mac[raw[0]]
                if raw[0] == "&app_switch":
                    continue
                text = type_sequence(seq)
                checked += 1
                if text != intended:
                    problems.append((name, idx, intended, text))
                continue
            else:
                continue                               # &mo, &bt, &out, &bootloader, &tab_gui
            checked += 1
            mods, key = split_mods(code)
            if key not in SC and not mods:
                # named non-character key (F-keys, arrows, media, Esc...): label must match the code
                if rl.KP.get(code) != intended:
                    problems.append((name, idx, intended, code))
                continue
            got = actual_kp(code)
            want = SHORTCUT_INTENT.get(intended, intended)
            if len(want) == 1:
                want = want.lower()                    # labels are capitals, the key types lowercase
            if got != want:
                problems.append((name, idx, intended, got))
    print(f"checked {checked} keys against the Windows Hungarian layout (0000040E)")
    for p in problems:
        print("MISMATCH  %-11s key %2d: intended %-8r -> HU Windows gives %r" % p)
    if not problems:
        print("all match")


keys_raw = {}


def _collect_raw():
    text = rl.KEYMAP.read_text(encoding="utf-8")
    text = "\n".join(re.sub(r"//.*", "", line) for line in text.splitlines())
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    km = text[text.index("keymap {"):]
    for name, body in re.findall(r"(\w+_layer) \{.*?bindings = <(.*?)>;", km, re.S):
        keys, cur = [], None
        for tok in body.split():
            if tok.startswith("&") or tok.startswith("HU_"):
                if cur:
                    keys.append(cur)
                cur = [tok]
            else:
                cur.append(tok)
        keys.append(cur)
        keys_raw[name] = keys


if __name__ == "__main__":
    _collect_raw()
    main()
