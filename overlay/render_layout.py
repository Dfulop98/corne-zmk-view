"""
Render config/corne.keymap into overlay/layout.png (all layers on one image).

Labels show what the Hungarian Windows layout actually types.
Run after every keymap change:  python overlay/render_layout.py
"""
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
KEYMAP = ROOT / "config" / "corne.keymap"
OUT = Path(__file__).resolve().parent / "layout.png"

# --- labels -----------------------------------------------------------------
KP = {
    "TAB": "Tab", "LSHFT": "Shift", "LCTRL": "Ctrl", "LALT": "Alt", "LGUI": "Win",
    "BSPC": "Bksp", "SPACE": "Space", "RET": "Enter", "ESC": "Esc", "DEL": "Del",
    "INS": "Ins", "CAPS": "Caps", "PSCRN": "PrtSc", "PG_UP": "PgUp", "PG_DN": "PgDn",
    "HOME": "Home", "END": "End", "LEFT": "←", "RIGHT": "→", "UP": "↑", "DOWN": "↓",
    "COMMA": ",", "DOT": ".", "Y": "Z", "Z": "Y",
    "C_PP": "Play", "C_STOP": "Stop", "C_MUTE": "Mute", "C_VOL_UP": "Vol+",
    "C_VOL_DN": "Vol−", "C_PREV": "Prev", "C_NEXT": "Next", "F24": "Info",
    "LA(F4)": "Alt+F4", "LG(UP)": "Max", "LG(DOWN)": "Min",
    "LG(LEFT)": "Snap←", "LG(RIGHT)": "Snap→",
    "LG(LS(LEFT))": "←Mon", "LG(LS(RIGHT))": "Mon→",
    "LG(LC(LEFT))": "←Dsk", "LG(LC(RIGHT))": "Dsk→", "LG(TAB)": "Task",
    "LG(L)": "Lock", "LG(D)": "Desk", "LG(V)": "Clip", "LG(LS(S))": "Snip",
}
for i in range(10):
    KP[f"N{i}"] = str(i)
for i in range(1, 25):
    KP.setdefault(f"F{i}", f"F{i}")

HU = {
    "HU_Z": "Z", "HU_Y": "Y", "HU_OE": "Ö", "HU_UE": "Ü", "HU_OA": "Ó", "HU_OEE": "Ő",
    "HU_UA": "Ú", "HU_EA": "É", "HU_AA": "Á", "HU_UEE": "Ű", "HU_IA": "Í", "HU_0": "0",
    "HU_SQT": "'", "HU_DQT": '"', "HU_PLUS": "+", "HU_EXCL": "!", "HU_PRCT": "%",
    "HU_SLSH": "/", "HU_EQL": "=", "HU_LPAR": "(", "HU_RPAR": ")", "HU_MINUS": "-",
    "HU_UNDER": "_", "HU_QUES": "?", "HU_COLON": ":", "HU_BSLH": "\\", "HU_PIPE": "|",
    "HU_AT": "@", "HU_HASH": "#", "HU_DLR": "$", "HU_AMPS": "&", "HU_STAR": "*",
    "HU_SEMI": ";", "HU_LT": "<", "HU_GT": ">", "HU_LBKT": "[", "HU_RBKT": "]",
    "HU_LBRC": "{", "HU_RBRC": "}", "HU_TILDE": "~", "HU_GRAVE": "`", "HU_UNDO": "Undo", "HU_REDO": "Redo",
    "HU_CUT": "Cut", "HU_COPY": "Copy", "HU_PASTE": "Paste",
}
BEHAVIOR = {
    "&hu_caret": "^", "&app_switch": "Apps",
    "&bootloader": "Boot", "&trans": "", "&none": "",
}

TITLES = {
    "base_layer": "BASE",
    "num_layer": "NUM  (bal középső hüvelyk)",
    "sym_layer": "SYM  (jobb középső hüvelyk)",
    "acc_layer": "ACC  (bal külső hüvelyk)",
    "dacc_layer": "ACC + SYM",
    "edit_layer": "EDIT  (jobb külső hüvelyk)",
    "sys_layer": "SYS  (NUM + SYM)",
}


def label(tokens):
    head = tokens[0]
    if head.startswith("HU_"):
        return HU.get(head, head[3:])
    if head == "&kp":
        return KP.get(tokens[1], tokens[1])
    if head == "&mo":
        return tokens[1]
    if head == "&tab_gui":
        return "Tab/Win"
    if head == "&bt":
        return "BT clr" if tokens[1] == "BT_CLR" else f"BT {tokens[2]}"
    if head == "&out":
        return "USB/BT"
    return BEHAVIOR.get(head, head.lstrip("&"))


def parse():
    text = KEYMAP.read_text(encoding="utf-8")
    text = "\n".join(re.sub(r"//.*", "", line) for line in text.splitlines())
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    keymap = text[text.index("keymap {"):]
    layers = []
    for name, body in re.findall(r"(\w+_layer) \{.*?bindings = <(.*?)>;", keymap, re.S):
        keys, cur = [], None
        for tok in body.split():
            if tok.startswith("&") or tok.startswith("HU_"):
                if cur:
                    keys.append(cur)
                cur = [tok]
            else:
                cur.append(tok)
        keys.append(cur)
        assert len(keys) == 42, (name, len(keys))
        layers.append((name, [(label(k), k[0]) for k in keys]))
    return layers


# --- drawing ----------------------------------------------------------------
K, G, SPLIT = 44, 4, 26           # key size, gap, gap between halves
STAGGER = [10, 10, 4, 0, 3, 6]    # corne column stagger, outer -> inner
BG, PANEL, KEY, KEY_DIM, INK, MUTED, ACCENT = (
    "#14171e", "#1c2029", "#2c3240", "#20242e", "#e8eaf0", "#7d8597", "#e0a83a")
FONT_DIR = Path("C:/Windows/Fonts")


def font(size, bold=False):
    for name in (["segoeuib.ttf"] if bold else []) + ["segoeui.ttf", "arial.ttf"]:
        try:
            return ImageFont.truetype(str(FONT_DIR / name), size)
        except OSError:
            continue
    return ImageFont.load_default()


F_KEY, F_SMALL, F_TITLE = font(15), font(11), font(16, bold=True)
HALF_W = 6 * (K + G)
BOARD_W = 2 * HALF_W + SPLIT
BOARD_H = 30 + 3 * (K + G) + 12 + 10 + K + 14


def draw_key(d, x, y, text, kind):
    held = kind == "&mo"
    fill = ACCENT if kind == "held" else (KEY if text else KEY_DIM)
    d.rounded_rectangle([x, y, x + K, y + K], radius=6, fill=fill)
    if not text:
        return
    f = F_KEY if len(text) <= 4 else F_SMALL
    color = BG if kind == "held" else (ACCENT if held else INK)
    d.text((x + K / 2, y + K / 2), text, font=f, fill=color, anchor="mm")


def draw_board(d, ox, oy, title, keys, held_idx):
    d.rounded_rectangle([ox - 14, oy - 10, ox + BOARD_W + 14, oy + BOARD_H], radius=10, fill=PANEL)
    d.text((ox, oy), title, font=F_TITLE, fill=INK)
    top = oy + 30
    for side in (0, 1):
        hx = ox + side * (HALF_W + SPLIT)
        for c in range(6):
            sy = STAGGER[5 - c if side else c]
            for r in range(3):
                i = r * 12 + side * 6 + c
                text, kind = keys[i]
                draw_key(d, hx + c * (K + G), top + sy + r * (K + G), text,
                         "held" if i in held_idx else kind)
        tx = hx + (3 * (K + G) if side == 0 else 0)
        ty = top + 3 * (K + G) + 22
        for j in range(3):
            i = 36 + side * 3 + j
            text, kind = keys[i]
            draw_key(d, tx + j * (K + G), ty, text, "held" if i in held_idx else kind)


# thumb positions that are held to reach each layer
HELD = {"num_layer": {37}, "sym_layer": {40}, "acc_layer": {36}, "dacc_layer": {36, 40},
        "edit_layer": {41}, "sys_layer": {37, 40}}


def main():
    layers = parse()
    cols, margin, gap = 3, 34, 40
    rows = (len(layers) + cols - 1) // cols
    w = margin * 2 + cols * BOARD_W + (cols - 1) * gap
    h = margin * 2 + rows * BOARD_H + (rows - 1) * gap + 24
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    for n, (name, keys) in enumerate(layers):
        r, c = divmod(n, cols)
        draw_board(d, margin + c * (BOARD_W + gap), margin + r * (BOARD_H + gap),
                   TITLES.get(name, name), keys, HELD.get(name, set()))
    d.text((w - margin, h - margin + 6), "EDIT + N: ablak be/ki  ·  sárga = nyomva tartott hüvelyk",
           font=F_SMALL, fill=MUTED, anchor="rs")
    img.save(OUT)
    print(f"{OUT}  {w}x{h}")


if __name__ == "__main__":
    main()
