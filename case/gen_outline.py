"""
Corne v3 Chocolate PCB outline -> SVG + DXF for designing a case.

Geometry comes straight from foostan's KiCad file (crkbd, tag v3-final,
corne-chocolate = the ProMicro / nice!nano version with 19 mm key pitch),
so the outline is exact, not traced.

Run:  python case/gen_outline.py
Out:  case/corne-v3-choc.svg  (both halves, layered, 1 unit = 1 mm)
      case/corne-v3-choc-left.dxf / -right.dxf  (outline, holes, switch cutouts)
"""
import math
import re
import urllib.request
from pathlib import Path

from shapely.geometry import Polygon

URL = ("https://raw.githubusercontent.com/foostan/crkbd/v3-final/"
       "corne-chocolate/pcb/corne-chocolate.kicad_pcb")
OUT = Path(__file__).resolve().parent

CLEARANCE = 1.0   # gap between PCB edge and the case inner wall
WALL = 3.0        # case wall thickness
SWITCH_CUT = 13.8 # choc v1 top-plate hole
CAP = (17.5, 16.5)  # choc (MBK-style) 1u keycap, 1.5u = 26.5 x 16.5
GAP = 30.0        # gap between the two halves in the drawing
MARGIN = 10.0


# --- KiCad parsing ------------------------------------------------------------
def load():
    with urllib.request.urlopen(URL) as r:
        return r.read().decode("utf-8")


def edge_segments(text):
    num = r"([-\d.]+)"
    segs = []
    for m in re.finditer(rf'\(gr_line \(start {num} {num}\) \(end {num} {num}\) \(layer "Edge.Cuts"', text):
        x1, y1, x2, y2 = map(float, m.groups())
        segs.append(("L", (x1, y1), (x2, y2), None))
    for m in re.finditer(rf'\(gr_arc \(start {num} {num}\) \(mid {num} {num}\) \(end {num} {num}\) \(layer "Edge.Cuts"', text):
        x1, y1, xm, ym, x2, y2 = map(float, m.groups())
        segs.append(("A", (x1, y1), (x2, y2), (xm, ym)))
    return segs


def chain(segs):
    """Join loose Edge.Cuts segments into closed loops (KiCad endpoints differ by ~0.003 mm)."""
    key = lambda p: (round(p[0] * 20), round(p[1] * 20))
    used, loops = [False] * len(segs), []
    for i, s in enumerate(segs):
        if used[i]:
            continue
        used[i], loop, cur = True, [s], s[2]
        while key(cur) != key(s[1]):
            for j, t in enumerate(segs):
                if used[j]:
                    continue
                if key(t[1]) == key(cur):
                    loop.append(t)
                elif key(t[2]) == key(cur):
                    loop.append((t[0], t[2], t[1], t[3]))
                else:
                    continue
                used[j], cur = True, loop[-1][2]
                break
            else:
                raise ValueError(f"open Edge.Cuts loop at {cur}")
        loops.append(loop)
    return loops


def arc_points(a, m, b, n=16):
    """Points on the circle through a, m, b (from a to b via m)."""
    ax, ay = a; mx, my = m; bx, by = b
    d = 2 * (ax * (my - by) + mx * (by - ay) + bx * (ay - my))
    ux = ((ax**2 + ay**2) * (my - by) + (mx**2 + my**2) * (by - ay) + (bx**2 + by**2) * (ay - my)) / d
    uy = ((ax**2 + ay**2) * (bx - mx) + (mx**2 + my**2) * (ax - bx) + (bx**2 + by**2) * (mx - ax)) / d
    r = math.hypot(ax - ux, ay - uy)
    t0, tm, t1 = (math.atan2(p[1] - uy, p[0] - ux) for p in (a, m, b))
    # pick the sweep direction that passes through the mid point
    sweep = (t1 - t0) % (2 * math.pi)
    if (tm - t0) % (2 * math.pi) > sweep:
        sweep -= 2 * math.pi
    return [(ux + r * math.cos(t0 + sweep * k / n), uy + r * math.sin(t0 + sweep * k / n))
            for k in range(1, n + 1)], (ux, uy, r, t0, sweep)


def loop_points(loop):
    pts = [loop[0][1]]
    for kind, a, b, m in loop:
        pts += arc_points(a, m, b)[0] if kind == "A" else [b]
    return pts


def footprints(text):
    out = []
    for part in re.split(r"\n  \(footprint ", text)[1:]:
        name = part.split('"')[1]
        at = [float(v) for v in re.search(r"\(at ([-\d. ]+)\)", part).group(1).split()]
        x, y, rot = at[0], at[1], (at[2] if len(at) > 2 else 0.0)
        drill = re.search(r"\(drill ([\d.]+)\)", part)
        out.append({"name": name, "x": x, "y": y, "rot": rot,
                    "drill": float(drill.group(1)) if drill else None})
    return out


def place(fp, lx, ly):
    """KiCad footprint-local -> board coordinates (angle is CCW on screen, y down)."""
    a = math.radians(fp["rot"])
    return (fp["x"] + lx * math.cos(a) + ly * math.sin(a),
            fp["y"] - lx * math.sin(a) + ly * math.cos(a))


def rect(fp, w, h, dx=0.0, dy=0.0):
    return [place(fp, dx + sx * w / 2, dy + sy * h / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


# --- build geometry for one half ---------------------------------------------
def build(text):
    loops = [Polygon(loop_points(l)) for l in chain(edge_segments(text))]
    loops.sort(key=lambda p: p.area, reverse=True)
    board, inner_cuts = loops[0], loops[1:]
    fps = footprints(text)
    keys = [f for f in fps if f["name"].startswith("kbd:Choc_Hotswap")]
    holes = [f for f in fps if f["name"] == "kbd:LEGO_HOLE"]
    mcu = next(f for f in fps if f["name"] == "kbd:ProMicro_v2")
    oled = next(f for f in fps if f["name"] == "kbd:OLED")
    reset = next(f for f in fps if f["name"] == "kbd:ResetSW")
    jack = next(f for f in fps if f["name"].startswith("kbd:MJ-4PP-9"))

    g = {"board": board, "inner": board.buffer(CLEARANCE, join_style="round"),
         "outer": board.buffer(CLEARANCE + WALL, join_style="round"),
         "cuts": inner_cuts, "holes": holes, "keys": [], "caps": [], "parts": []}
    for k in keys:
        wide = k["name"].endswith("1.5u")
        g["keys"].append(rect(k, SWITCH_CUT, SWITCH_CUT))
        g["caps"].append(rect(k, CAP[0] + (9.0 if wide else 0), CAP[1]))
    # ProMicro F.Fab body (nice!nano is the same 18 x 33 footprint)
    g["parts"].append(("nice!nano", [place(mcu, x, y) for x, y in
                       ((-10.16, -18.288), (8.935, -18.288), (8.935, 16.002), (-10.16, 16.002))]))
    g["parts"].append(("nice!view csatl.", [place(oled, x, y) for x, y in
                       ((-1.27, -1.27), (8.89, -1.27), (8.89, 1.27), (-1.27, 1.27))]))
    g["parts"].append(("reset", rect(reset, 6.0, 3.5)))
    g["parts"].append(("TRRS / kapcsoló", [place(jack, x, y) for x, y in
                       ((-3.0, 0.0), (3.0, 0.0), (3.0, 12.0), (-3.0, 12.0))]))
    return g


# --- output -------------------------------------------------------------------
def transform(g, fn):
    """Apply fn(x, y) to every coordinate of a built half."""
    from shapely.ops import transform as st
    t = lambda geom: st(lambda x, y, z=None: fn(x, y), geom)
    return {
        "board": t(g["board"]), "inner": t(g["inner"]), "outer": t(g["outer"]),
        "cuts": [t(c) for c in g["cuts"]],
        "holes": [dict(h, **dict(zip(("x", "y"), fn(h["x"], h["y"])))) for h in g["holes"]],
        "keys": [[fn(*p) for p in r] for r in g["keys"]],
        "caps": [[fn(*p) for p in r] for r in g["caps"]],
        "parts": [(n, [fn(*p) for p in r]) for n, r in g["parts"]],
    }


def path(points, close=True):
    d = "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in points)
    return d + (" Z" if close else "")


def poly_path(poly):
    return path(list(poly.exterior.coords)[:-1])


def svg(halves, w, h):
    layer = lambda lid, label, body, style: (
        f'  <g id="{lid}" inkscape:groupmode="layer" inkscape:label="{label}" style="{style}">\n'
        + body + "  </g>\n")
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
           f'width="{w:.2f}mm" height="{h:.2f}mm" viewBox="0 0 {w:.3f} {h:.3f}">\n',
           f'  <title>Corne v3 Chocolate – NYÁK körvonal (1 egység = 1 mm)</title>\n']
    groups = {
        "outer": ("Ház külső fal (+{:g} mm fal)".format(WALL),
                  "fill:none;stroke:#888;stroke-width:0.3"),
        "inner": ("Ház belső fal (+{:g} mm hézag)".format(CLEARANCE),
                  "fill:none;stroke:#1f77ff;stroke-width:0.3;stroke-dasharray:2,1"),
        "board": ("NYÁK körvonal", "fill:#e8f3e8;stroke:#d00;stroke-width:0.3"),
        "caps": ("Keycap helye (choc)", "fill:none;stroke:#bbb;stroke-width:0.2;stroke-dasharray:1,1"),
        "keys": ("Switch kivágás {:g} mm (top plate)".format(SWITCH_CUT),
                 "fill:none;stroke:#000;stroke-width:0.25"),
        "parts": ("Alkatrészek", "fill:#ffe9b0;fill-opacity:0.6;stroke:#c08000;stroke-width:0.2"),
        "holes": ("Furatok", "fill:none;stroke:#7a00c0;stroke-width:0.25"),
        "cuts": ("NYÁK belső kivágások (LED ablak, letörő)", "fill:none;stroke:#d00;stroke-width:0.15"),
    }
    for lid, (label, style) in groups.items():
        body = ""
        for g in halves:
            if lid in ("outer", "inner", "board"):
                body += f'    <path d="{poly_path(g[lid])}"/>\n'
            elif lid == "cuts":
                body += "".join(f'    <path d="{poly_path(c)}"/>\n' for c in g["cuts"])
            elif lid in ("keys", "caps"):
                body += "".join(f'    <path d="{path(r)}"/>\n' for r in g[lid])
            elif lid == "parts":
                for name, r in g["parts"]:
                    cx = sum(p[0] for p in r) / 4; cy = sum(p[1] for p in r) / 4
                    body += (f'    <path d="{path(r)}"/>\n'
                             f'    <text x="{cx:.2f}" y="{cy:.2f}" font-size="2.2" text-anchor="middle" '
                             f'dominant-baseline="middle" style="fill:#805000;stroke:none">{name}</text>\n')
            elif lid == "holes":
                for hl in g["holes"]:
                    body += (f'    <circle cx="{hl["x"]:.3f}" cy="{hl["y"]:.3f}" r="{hl["drill"] / 2:.3f}"/>\n'
                             f'    <text x="{hl["x"]:.2f}" y="{hl["y"] + hl["drill"] / 2 + 2.2:.2f}" '
                             f'font-size="1.8" text-anchor="middle" style="fill:#7a00c0;stroke:none">'
                             f'Ø{hl["drill"]:g}</text>\n')
        out.append(layer(lid, label, body, style))
    out.append("</svg>\n")
    return "".join(out)


def dxf(g):
    """Minimal R12 DXF: polylines on named layers, holes as circles (mm)."""
    ents = []
    def pline(points, lay):
        ents.append(f"0\nPOLYLINE\n8\n{lay}\n66\n1\n70\n1\n")
        for x, y in points:
            ents.append(f"0\nVERTEX\n8\n{lay}\n10\n{x:.4f}\n20\n{-y:.4f}\n")
        ents.append(f"0\nSEQEND\n8\n{lay}\n")
    for lay in ("board", "inner", "outer"):
        pline(list(g[lay].exterior.coords)[:-1], lay.upper())
    for r in g["keys"]:
        pline(r, "SWITCH_CUT")
    for hl in g["holes"]:
        ents.append(f"0\nCIRCLE\n8\nHOLES\n10\n{hl['x']:.4f}\n20\n{-hl['y']:.4f}\n40\n{hl['drill'] / 2:.4f}\n")
    for name, r in g["parts"]:
        pline(r, "PARTS")
    return ("0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n"
            "0\nSECTION\n2\nENTITIES\n" + "".join(ents) + "0\nENDSEC\n0\nEOF\n")


def main():
    left = build(load())
    minx, miny, maxx, maxy = left["outer"].bounds
    hw, hh = maxx - minx, maxy - miny
    w, h = 2 * hw + GAP + 2 * MARGIN, hh + 2 * MARGIN
    L = transform(left, lambda x, y: (x - minx + MARGIN, y - miny + MARGIN))
    R = transform(left, lambda x, y: (w - (x - minx + MARGIN), y - miny + MARGIN))  # mirror
    (OUT / "corne-v3-choc.svg").write_text(svg([L, R], w, h), encoding="utf-8")
    # DXFs with the PCB's own top-left corner at 0,0
    bx, by = left["board"].bounds[:2]
    (OUT / "corne-v3-choc-left.dxf").write_text(dxf(transform(left, lambda x, y: (x - bx, y - by))))
    bw = left["board"].bounds[2] - bx
    (OUT / "corne-v3-choc-right.dxf").write_text(dxf(transform(left, lambda x, y: (bw - (x - bx), y - by))))

    b = left["board"].bounds
    print(f"PCB half: {b[2] - b[0]:.2f} x {b[3] - b[1]:.2f} mm, keys {len(left['keys'])}, "
          f"holes {[h['drill'] for h in left['holes']]}")
    for i, r in enumerate(left["caps"]):
        if not left["inner"].contains(Polygon(r)):
            print(f"note: keycap {i} sticks out over the case inner wall")
    print("svg", f"{w:.1f} x {h:.1f} mm")


if __name__ == "__main__":
    main()
