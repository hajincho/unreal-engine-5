"""Collision checks for future character traversal: downward traces onto walkable surfaces and a
horizontal trace against a building wall. Prints PASS/FAIL per probe and the hit actor."""
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ck_level_common as L  # noqa: E402

PROBES = [  # name, start(m), end(m), expected z range or None for horizontal
    ("South shore (camera ground)", (2, 0, 40), (2, 0, -40), (-2, 12)),
    ("Grand stair mid-flight", (21.5, -15.0, 40), (21.5, -15.0, -40), (2, 9)),
    ("Loggia roof terrace", (44.0, -36.0, 40), (44.0, -36.0, -40), (20, 24)),
    ("Loggia lower arcade floor", (46.5, -31.0, 9.5), (46.5, -31.0, -40), (6, 8)),
    ("Bridge deck seam (x_l=37)", (178.0, 10.0, 40), (178.0, 10.0, -40), (11, 13)),
    ("Bridge deck centre", (178.0, 12.5, 40), (178.0, 12.5, -40), (11, 13)),
    ("Bridge deck east", (178.0, 40.0, 40), (178.0, 40.0, -40), (11, 13)),
    ("East plaza top", (77.0, 69.0, 40), (77.0, 69.0, -40), (8, 12)),
    ("East town terrace", (186.0, 92.0, 60), (186.0, 92.0, -40), (13, 40)),
    ("Lake bed (under water)", (120.0, 0.0, 40), (120.0, 0.0, -60), (-30, 0)),
    ("Hall wall (horizontal)", (165.0, -52.0, 16), (195.0, -52.0, 16), None),
    ("Cave wall (horizontal)", (100.0, 0.0, 40), (100.0, -300.0, 40), None),
]

ok = 0
for name, s, e, rng in PROBES:
    r = unreal.SystemLibrary.line_trace_single(L.world(), L.v(*s), L.v(*e), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
                                               unreal.DrawDebugTrace.NONE, True)  # simple collision only
    hr = r[1] if isinstance(r, tuple) else r
    t = hr.to_tuple() if hr else None
    if not t or not t[0]:
        print("FAIL  %-30s no hit (simple collision)" % name)
        continue
    p = t[5]
    actor = t[9].get_actor_label() if t[9] else "?"
    z = p.z / 100.0
    good = rng is None or (rng[0] <= z <= rng[1])
    ok += good
    print("%s  %-30s hit z=%.2f m  x=%.1f  actor=%s" % ("PASS" if good else "WARN", name, z, p.x / 100.0, actor))
print("collision probes passed: %d/%d" % (ok, len(PROBES)))
