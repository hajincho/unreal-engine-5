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
    for k, (name, fn) in enumerate(specs):
        rng = random.Random(900 + k)
        mb = C.MeshBuilder(name, [TR] if "Mote" not in name else [MOTE])
        fn(mb, rng)
        ob, ucx = mb.finish(coll, uv_scale=0.5, recalc="Mote" not in name)
        C.export_asset(ob, ucx, "Props")
        print("BUILT", name, len(ob.data.polygons))
    C.save_blend("CK_Props")


if __name__ == "__main__":
    main()
