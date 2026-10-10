"""
Kailh Choc v1 keycap generator for FDM printing (Corne, 18x17 mm choc spacing).

Output STLs are already oriented for printing: top face on the bed, legs up.
Run:  python gen_choc_keycaps.py
"""
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold

OUT = Path(__file__).parent / "stl"

# --- cap body -------------------------------------------------------------
PITCH_X, PITCH_Y = 18.0, 17.0   # choc spacing
GAP = 0.7                       # space between neighbouring caps
CORNER_R = 1.5                  # plan-view corner radius
THICK = 2.6                     # solid body thickness (no skirt -> never hits the housing)
CHAMFER = 0.6                   # 45 deg chamfer on the top edge

# --- choc v1 legs ---------------------------------------------------------
LEG_PITCH = 5.7                 # centre-to-centre distance of the two legs (X)
LEG_W = 1.20                    # leg width  (X)
LEG_L = 3.00                    # leg length (Y)
LEG_H = 3.0                     # how far the legs stick out under the cap
LEG_TIP = 0.25                  # lead-in chamfer at the leg tip

# --- homing mark (F / J) ----------------------------------------------------
HOMING_W, HOMING_L, HOMING_D = 1.0, 6.0, 0.4   # tactile groove on the top face


def rounded_rect(w, h, r):
    r = min(r, w / 2 - 0.01, h / 2 - 0.01)
    sq = CrossSection.square((w - 2 * r, h - 2 * r), center=True)
    return sq.offset(r, JoinType.Round, circular_segments=48)


def slab(w, h, r, z0, z1):
    return Manifold.extrude(rounded_rect(w, h, r), z1 - z0).translate((0, 0, z0))


def body(units_x=1.0):
    w = PITCH_X * units_x - GAP
    h = PITCH_Y - GAP
    # z = 0 is the top face (it will sit on the bed), body grows towards +z
    top = slab(w - 2 * CHAMFER, h - 2 * CHAMFER, CORNER_R - CHAMFER, 0, 0.01)
    rest = slab(w, h, CORNER_R, CHAMFER, THICK)
    return Manifold.batch_hull([top, rest])


def leg(x, offset):
    lw, ll = LEG_W + offset, LEG_L + offset
    base = Manifold.cube((lw, ll, LEG_H - LEG_TIP), center=False).translate(
        (x - lw / 2, -ll / 2, THICK))
    tip = Manifold.cube((lw - 2 * LEG_TIP, ll - 2 * LEG_TIP, 0.01)).translate(
        (x - lw / 2 + LEG_TIP, -ll / 2 + LEG_TIP, THICK + LEG_H - 0.01))
    return Manifold.batch_hull([base, tip])


def keycap(units_x=1.0, homing=False, leg_offset=0.0):
    cap = body(units_x)
    cap += leg(-LEG_PITCH / 2, leg_offset) + leg(LEG_PITCH / 2, leg_offset)
    if homing:
        groove = Manifold.cube((HOMING_L, HOMING_W, HOMING_D * 2), center=True)
        cap -= groove.translate((0, -3.5, 0))
    return cap


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=True)


def save(m, name):
    t = to_trimesh(m)
    assert t.is_watertight, name
    t.export(OUT / name)
    ext = t.bounds[1] - t.bounds[0]
    print(f"{name:28s} {ext[0]:5.1f} x {ext[1]:5.1f} x {ext[2]:4.1f} mm")


def main():
    OUT.mkdir(exist_ok=True)
    save(keycap(1.0), "choc_1u.stl")
    save(keycap(1.0, homing=True), "choc_1u_homing.stl")
    save(keycap(1.5), "choc_1_5u.stl")

    # Fit test: leg size offsets left -> right; one extra notch per cap on the
    # body edge marks its position (1 notch = first, 5 notches = last).
    offsets = [-0.10, -0.05, 0.0, 0.05, 0.10]
    strip = Manifold()
    for i, off in enumerate(offsets):
        cap = keycap(1.0, leg_offset=off)
        for n in range(i + 1):
            notch = Manifold.cube((0.8, 1.2, THICK * 3), center=True)
            cap -= notch.translate((-6 + n * 1.6, -(PITCH_Y - GAP) / 2, 0))
        strip += cap.translate((i * PITCH_X, 0, 0))
    save(strip, "choc_fit_test_5x.stl")


if __name__ == "__main__":
    main()
