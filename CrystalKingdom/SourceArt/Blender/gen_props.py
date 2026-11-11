"""Detail props: broken column drums, cut-stone debris, broken ornaments, floating glow motes.
run: blender --background --factory-startup --python gen_props.py
"""
import math
import os
import random
import sys

from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ck_common as C  # noqa: E402
import gen_architecture as A  # noqa: E402

TR, MOTE = "M_StoneTrim", "M_GlowMote"
PL, FL, SL, MT, GL, CR = "M_Plant", "M_Flower", "M_Soil", "M_Metal", "M_WindowGlow", "M_Crystal"
STREET_MATS = [TR, PL, FL, SL, MT, GL, CR]


def shrub(mb, rng, x, y, z, r):
    """Low-poly leafy clump: a few squashed, jittered lathe blobs."""
    for _ in range(rng.randint(2, 4)):
        rr = r * rng.uniform(0.55, 1.0)
        ox, oy = rng.uniform(-r, r) * 0.6, rng.uniform(-r, r) * 0.6
        prof = [(rr * 0.35, 0.0), (rr * rng.uniform(0.85, 1.05), rr * 0.45), (rr * rng.uniform(0.7, 0.95), rr * 0.95),
                (rr * 0.35, rr * 1.3), (0.0, rr * rng.uniform(1.35, 1.6))]
        mb.lathe(PL, (x + ox, y + oy, z), prof, sides=7, smooth=True)


def flowers(mb, rng, x, y, z, n, spread):
    for _ in range(n):
        fx, fy = x + rng.uniform(-spread, spread), y + rng.uniform(-spread * 0.4, spread * 0.4)
        h = rng.uniform(0.25, 0.6)
        mb.cyl(PL, (fx, fy, z), 0.015, h, sides=4)
        mb.lathe(FL, (fx, fy, z + h), [(0.0, -0.03), (0.07, 0.0), (0.05, 0.05), (0.0, 0.07)], sides=5)


def planter_long(mb, rng, L=6.0, W=1.1, H=0.75):
    """Long stone street planter: moulded trough, soil, shrubs, flowers and a few crystal shoots."""
    mb.box(TR, (0, 0, 0.08), (L + 0.2, W + 0.2, 0.16), collide=True)              # plinth
    for sy in (-1, 1):
        mb.box(TR, (0, sy * (W / 2 - 0.09), H / 2), (L, 0.18, H), collide=True)    # long walls
        mb.box(TR, (0, sy * (W / 2 - 0.05), H + 0.05), (L + 0.12, 0.3, 0.1))       # rim
    for sx in (-1, 1):
        mb.box(TR, (sx * (L / 2 - 0.09), 0, H / 2), (0.18, W, H), collide=True)
        mb.box(TR, (sx * (L / 2), 0, H / 2 + 0.05), (0.32, W + 0.22, H + 0.1))   # end posts
        A.finial(mb, sx * (L / 2), 0, H + 0.1, 0.35, mat=TR)
    for k in range(int(L / 1.5)):                                                # carved panels
        x = -L / 2 + 0.75 + k * 1.5
        for sy in (-1, 1):
            mb.box(TR, (x, sy * (W / 2 + 0.01), H * 0.5), (1.1, 0.04, H * 0.55))
    mb.box(SL, (0, 0, H - 0.08), (L - 0.36, W - 0.36, 0.06))                      # soil
    n = int(L / 0.9)
    for k in range(n):
        x = -L / 2 + 0.5 + k * (L - 1.0) / max(n - 1, 1)
        shrub(mb, rng, x, rng.uniform(-0.1, 0.1), H - 0.06, rng.uniform(0.28, 0.42))
    flowers(mb, rng, 0, 0, H - 0.06, int(L * 4), L / 2 - 0.35)
    for _ in range(3):                                                           # tiny crystal shoots
        x = rng.uniform(-L / 2 + 0.6, L / 2 - 0.6)
        mb.cyl(CR, (x, rng.uniform(-0.15, 0.15), H - 0.06), 0.06, rng.uniform(0.35, 0.7), sides=6, r_top=0.0, smooth=False)


def planter_round(mb, rng, R=1.0, H=0.8):
    mb.lathe(TR, (0, 0, 0), [(R * 0.8, 0.0), (R * 0.85, 0.15), (R * 0.75, 0.3), (R * 0.95, H * 0.85), (R * 1.05, H), (R * 0.9, H + 0.06)], sides=16)
    mb.cyl(SL, (0, 0, H - 0.12), R * 0.88, 0.06, sides=16)
    shrub(mb, rng, 0, 0, H - 0.08, R * 0.7)
    flowers(mb, rng, 0, 0, H - 0.08, 18, R * 0.7)
    mb.add_ucx([(x, y, z) for x in (-R, R) for y in (-R, R) for z in (0, H)])


def street_lamp(mb, rng, H=4.6):
    """Wrought-iron street lamp with a glowing lantern (emissive only: no light cost)."""
    mb.lathe(TR, (0, 0, 0), [(0.32, 0.0), (0.32, 0.2), (0.22, 0.3), (0.2, 0.55), (0.12, 0.7)], sides=8)
    mb.cyl(MT, (0, 0, 0.7), 0.07, H - 0.7, sides=8)
    for z in (1.4, H - 0.6):
        mb.cyl(MT, (0, 0, z), 0.11, 0.08, sides=8)
    mb.box(MT, (0.35, 0, H - 0.05), (0.75, 0.06, 0.06))                         # arm
    mb.cyl(MT, (0.72, 0, H - 0.35), 0.015, 0.3, sides=4)
    mb.box(GL, (0.72, 0, H - 0.62), (0.26, 0.26, 0.38))                          # lantern glass
    mb.cyl(MT, (0.72, 0, H - 0.43), 0.2, 0.16, sides=4, r_top=0.03, smooth=False)  # cap
    mb.box(MT, (0.72, 0, H - 0.83), (0.3, 0.3, 0.05))
    mb.add_ucx([(x, y, z) for x in (-0.3, 0.3) for y in (-0.3, 0.3) for z in (0, H)])


def bench(mb, rng, L=2.2):
    for sx in (-1, 1):
        mb.box(TR, (sx * (L / 2 - 0.2), 0, 0.22), (0.28, 0.5, 0.44))
        A.finial(mb, sx * (L / 2 - 0.2), 0.15, 0.44, 0.15, mat=TR)
    mb.box(TR, (0, 0, 0.47), (L, 0.55, 0.1), collide=True)
    mb.box(TR, (0, 0.25, 0.8), (L, 0.1, 0.55))


def broken_column(mb, rng):
    r = rng.uniform(0.32, 0.45)
    n_drums = rng.randint(2, 4)
    x = 0.0
    for i in range(n_drums):
        L = rng.uniform(0.7, 1.6)
        mb.push(Matrix.Translation((x, rng.uniform(-0.6, 0.6), r)) @ Matrix.Rotation(math.radians(rng.uniform(80, 100)), 4, "Y")
                @ Matrix.Rotation(rng.uniform(0, 6.28), 4, "Z"))
        sides = 16
        jag = [rng.uniform(-0.12, 0.12) for _ in range(sides)]
        for k in range(sides):
            a0, a1 = 2 * math.pi * k / sides, 2 * math.pi * (k + 1) / sides
            fl = 0.93 if k % 2 else 1.0  # fluting
            p = [(r * fl * math.cos(a0), r * fl * math.sin(a0), 0.0), (r * fl * math.cos(a1), r * fl * math.sin(a1), 0.0),
                 (r * fl * math.cos(a1), r * fl * math.sin(a1), L + jag[(k + 1) % sides]), (r * fl * math.cos(a0), r * fl * math.sin(a0), L + jag[k])]
            mb.face(p, TR)
        mb.face([(r * math.cos(2 * math.pi * k / sides), r * math.sin(2 * math.pi * k / sides), 0.0) for k in reversed(range(sides))], TR)
        mb.face([(r * math.cos(2 * math.pi * k / sides), r * math.sin(2 * math.pi * k / sides), L + jag[k]) for k in range(sides)], TR)
        mb.pop()
        x += L + rng.uniform(0.2, 0.9)
    if rng.random() < 0.6:
        mb.push(Matrix.Translation((x + 0.6, 0.4, 0.0)) @ Matrix.Rotation(math.radians(rng.uniform(-25, 25)), 4, "X"))
        A.capital(mb, 0, 0, 0.0, r)
        mb.pop()


def debris(mb, rng, n=14, area=3.0):
    for _ in range(n):
        s = (rng.uniform(0.25, 0.9), rng.uniform(0.2, 0.5), rng.uniform(0.15, 0.45))
        a = rng.uniform(0, 6.28)
        d = area * math.sqrt(rng.random())
        mb.push(Matrix.Translation((d * math.cos(a), d * math.sin(a), s[2] * 0.4)) @ Matrix.Rotation(rng.uniform(0, 6.28), 4, "Z")
                @ Matrix.Rotation(math.radians(rng.uniform(-25, 25)), 4, "X"))
        mb.box(TR, (0, 0, 0), s)
        mb.pop()


def ornament(mb, rng):
    mb.push(Matrix.Rotation(math.radians(rng.uniform(60, 100)), 4, "Y"))
    A.pinnacle(mb, 0, 0, 0, rng.uniform(0.6, 0.9))
    mb.pop()
    debris(mb, rng, 6, 1.5)


def motes(mb, rng, n=420, size=(40.0, 40.0, 25.0)):
    for _ in range(n):
        c = Vector((rng.uniform(-size[0] / 2, size[0] / 2), rng.uniform(-size[1] / 2, size[1] / 2), rng.uniform(0, size[2])))
        s = rng.uniform(0.03, 0.09)
        mb.piece_rand = rng.random()
        pts = [c + Vector(v) * s for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1.4), (0, 0, -1.4))]
        tris = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
        g = rng.random()
        for t in tris:
            mb.face([tuple(pts[i]) for i in t], MOTE, g=[g, g, g])


def main():
    C.reset_scene()
    coll = C.collection("Props")
    specs = [("SM_Props_ColumnBroken_%02d" % (i + 1), broken_column) for i in range(3)]
    specs += [("SM_Props_StoneDebris_%02d" % (i + 1), debris) for i in range(3)]
    specs += [("SM_Props_OrnamentBroken_%02d" % (i + 1), ornament) for i in range(2)]
    specs += [("SM_Props_GlowMotes_%02d" % (i + 1), motes) for i in range(2)]
    specs += [("SM_Prop_PlanterLong_%02d" % (i + 1), planter_long) for i in range(3)]
    specs += [("SM_Prop_PlanterRound_%02d" % (i + 1), planter_round) for i in range(2)]
    specs += [("SM_Prop_StreetLamp_01", street_lamp), ("SM_Prop_Bench_01", bench)]
    only = os.environ.get("CK_ONLY")
    for k, (name, fn) in enumerate(specs):
        if only and only not in name:
            continue
        rng = random.Random(900 + k)
        mats = [MOTE] if "Mote" in name else (STREET_MATS if "SM_Prop_" in name else [TR])
        mb = C.MeshBuilder(name, mats)
        fn(mb, rng)
        ob, ucx = mb.finish(coll, uv_scale=0.5, recalc="Mote" not in name)
        C.export_asset(ob, ucx, "Props")
        print("BUILT", name, len(ob.data.polygons))
    C.save_blend("CK_Props" if not only else "CK_Props_" + only)


if __name__ == "__main__":
    main()
