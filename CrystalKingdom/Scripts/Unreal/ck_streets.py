"""Straight streets for the row town (ck_layout.py): one paved street on every street line that has houses, cross
streets (along Y) through gaps in the house rows, and links from the grand bridge ends to the nearest street.
Physics first: the paving follows the ground with a grade limit (raised only, never buried); any fill over 0.25 m
stands on a dressed-stone embankment; a road never crosses water, a cliff (fill > MAX_FILL) or a building.
CK_ARGS: width=7 grade=0.12 max_fill=2.5 cross_gap=60
Writes Saved/road_plan.json (kinds street / cross / link) for the map and the landscaping stage.
"""
import json
import math
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib  # noqa: E402

import ck_level_common as L  # noqa: E402

importlib.reload(L)
from ck_level_common import M, rot, v  # noqa: E402

ARGS = globals().get("CK_ARGS", {})
E = L.EAS
W = float(ARGS.get("width", "8"))          # kerb to kerb = facade line to facade line: every door opens onto the paving
GRADE = float(ARGS.get("grade", "0.05"))            # ~3 degrees: streets read as level, with gentle ramps
FLAT_R = int(ARGS.get("flat_window", "6"))           # half window in samples (x STEP m) for the levelling
CLEAR = float(ARGS.get("clear", "0.10"))             # paving always this far above the highest rock under it
REQ = {}                                             # (x, y) of a road sample -> lowest allowed top height
MAX_FILL = float(ARGS.get("max_fill", "2.5"))
CROSS_GAP = float(ARGS.get("cross_gap", "60"))
STEP = 2.0
PAVE = "/Game/CrystalKingdom/Materials/Instances/MI_StoneTrim"
CRYSTALS = ("CK/Crystals/Floor", "CK/Crystals/Dense", "CK/Crystals/Landmarks", "CK/Rocks/Shore", "CK/Crystals/Foreground")

print("old roads removed", L.clear_ck("CK/Roads"), "old front steps", L.clear_ck("CK/Architecture/Town/Steps"), "old bridge steps", L.clear_ck("CK/Bridge"))
with open(os.path.join(unreal.Paths.project_saved_dir(), "town_rows.json"), encoding="utf-8") as fh:
    TOWN = json.load(fh)
L.reset_terrain_cache()
FLOOR = [t for t in L._terrain() if "Shell" not in t[0].static_mesh.get_name()]
_g = {}


def G(x, y):
    k = (round(x * 2) / 2, round(y * 2) / 2)
    if k in _g:
        return _g[k]
    best = None
    X, Y = k[0] * M, k[1] * M
    for comp, x0, x1, y0, y1 in FLOOR:
        if x0 <= X <= x1 and y0 <= Y <= y1:
            r = comp.line_trace_component(unreal.Vector(X, Y, 11500), unreal.Vector(X, Y, -4000), True, False, False)
            if isinstance(r, tuple) and r[1].length() > 0.5 and r[1].z > 0.5:
                z = r[0].z / M
                if z < 60 and (best is None or z > best):
                    best = z
    _g[k] = best
    return best


# obstacles: every building / plinth / footing / quay wall footprint (AABB, metres)
blocks = []
for a in E.get_all_level_actors():
    f = str(a.get_folder_path())
    if f.startswith("CK/Architecture") and isinstance(a, unreal.StaticMeshActor):
        nm = a.static_mesh_component.static_mesh.get_name() if a.static_mesh_component.static_mesh else ""
        if "Bridge" in nm:
            continue
        o, e = a.get_actor_bounds(False)
        blocks.append([o.x / M - e.x / M, o.x / M + e.x / M, o.y / M - e.y / M, o.y / M + e.y / M, f, a])

IGNORE_TOWN = [False]
IGNORE_WALLS = [False]


def blocked(x, y, half):
    for b in blocks:
        b0, b1, c0, c1, f = b[:5]
        if IGNORE_TOWN[0] and f == "CK/Architecture/Town":
            continue
        if IGNORE_WALLS[0] and f.startswith(("CK/Architecture/TerraceWalls", "CK/Architecture/Footings")):
            continue
        if b0 - half < x < b1 + half and c0 - half < y < c1 + half:
            return True
    return False


def profile(p0, p1, half=None, min_pts=4, cliffs_ok=False):
    """Sample a straight line every STEP m. Returns runs [(pts, zs, ground)] that are buildable."""
    half = W / 2 if half is None else half
    L_ = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    n = max(2, int(round(L_ / STEP)))
    pts = [(p0[0] + (p1[0] - p0[0]) * k / n, p0[1] + (p1[1] - p0[1]) * k / n) for k in range(n + 1)]
    ux, uy = (p1[0] - p0[0]) / (L_ or 1), (p1[1] - p0[1]) / (L_ or 1)
    nx, ny = -uy, ux
    g = []
    across = [i / 8.0 for i in range(-8, 9)]            # every 0.5 m across an 8 m carriageway
    along = [-1.0, -0.5, 0.0, 0.5, 1.0]                  # and every 0.5 m along, covering both half-segments
    for x, y in pts:      # ground under the whole carriageway: the lowest decides the fill, the highest the level
        zs = [G(x + nx * s * half + ux * t, y + ny * s * half + uy * t) for s in across for t in along]
        bad = any(z is None or z < 0.15 for z in zs) or blocked(x, y, half - 0.6) or (not cliffs_ok and max(zs) - min(zs) > MAX_FILL)   # a cliff across the carriageway
        g.append(None if bad else (max(zs), min(zs)))
    for k in range(1 if not cliffs_ok else len(g), len(g)):   # a cliff along the road breaks it (connectors climb it with steps)
        if g[k] is not None and g[k - 1] is not None and abs(g[k][0] - g[k - 1][0]) > MAX_FILL:   # smaller steps are ramped by the levelling
            g[k] = None
    runs, cur = [], []
    for k, gi in enumerate(g):
        if gi is None:
            if len(cur) >= min_pts:
                runs.append(cur)
            cur = []
        else:
            cur.append(k)
    if len(cur) >= min_pts:
        runs.append(cur)
    out = []
    for run in runs:
        z0 = [g[k][0] + CLEAR for k in run]                    # minimum: clear of every rock under the paving
        for i, k in enumerate(run):
            REQ[(round(pts[k][0], 2), round(pts[k][1], 2))] = z0[i]
        # buildability only (water, cliffs, buildings were cut above); the final heights come from terrace() later
        out.append([(pts[k], z0[i], g[k][1]) for i, k in enumerate(run)])
    return out


roads = []
n_slab = n_emb = 0


def pave(piece, kind, width=None):
    """Record one straight road body: centre points, top height and lowest ground per point."""
    roads.append({"kind": kind, "width": width or W, "pts": [list(p) for p, _, _ in piece], "z": [z for _, z, _ in piece],
                  "low": [lo for _, _, lo in piece]})


# ---------------------------------------------------------------- 1. streets along the street lines that have houses
houses = TOWN["houses"]
lines = {}
for h in houses:
    mname, side, px0, px1, py0, py1, floor, low = h
    ys = (py0 - TOWN["street_half"]) if side > 0 else (py1 + TOWN["street_half"])
    lines.setdefault(round(ys, 1), []).append((px0, px1))
live = [(b[0], b[1], b[2], b[3]) for b in blocks if b[4] == "CK/Architecture/Town"]
for ys, spans in sorted(lines.items()):
    # only houses still standing, grouped into clusters: a street runs where houses line it, not along empty cave wall
    spans = sorted(sp for sp in spans if any(abs(l0 - sp[0]) < 0.6 and abs(l1 - sp[1]) < 0.6 and (c0 - 6 < ys < c1 + 6) for l0, l1, c0, c1 in live))
    clusters = []
    for sp in spans:
        if clusters and sp[0] - clusters[-1][1] < float(ARGS.get("merge_gap", "60")):
            clusters[-1][1] = max(clusters[-1][1], sp[1])
        else:
            clusters.append([sp[0], sp[1]])
    for x0, x1 in clusters:
        for piece in profile((x0 - 8, ys), (x1 + 8, ys)):
            pave(piece, "street")
street_ys = sorted(lines)
print("street lines", street_ys, "pieces", len(roads))

# ---------------------------------------------------------------- 2. cross streets: open the rows where it costs fewest houses
def on_street(px, py):
    return any(r["kind"] == "street" and abs(r["pts"][0][1] - py) < 0.5 and r["pts"][0][0] + 2 <= px <= r["pts"][-1][0] - 2 for r in roads)


def town_blockers(x, ya, yb):
    hw = W / 2 + 0.6
    return [b for b in blocks if b[4] == "CK/Architecture/Town" and b[0] < x + hw and b[1] > x - hw and b[2] < yb and b[3] > ya]


ncross = opened = 0
for ya, yb in zip(street_ys, street_ys[1:]):
    if yb - ya > 50:
        continue
    cands = []
    for xi in range(-40, 450, 2):
        x = float(xi)
        if not (on_street(x, ya) and on_street(x, yb)):
            continue
        bl = town_blockers(x, ya, yb)
        houses_ = [b for b in bl if b[5].static_mesh_component.static_mesh.get_name() != "Cube"]
        if len(houses_) > 2:
            continue
        IGNORE_TOWN[0] = True
        pieces = profile((x, ya), (x, yb))
        IGNORE_TOWN[0] = False
        if len(pieces) == 1 and abs(pieces[0][0][0][1] - ya) < 3 and abs(pieces[0][-1][0][1] - yb) < 3:
            cands.append((len(houses_), x, pieces[0], bl))
    want = max(1, int(sum(1 for _ in cands) and (max(c[1] for c in cands) - min(c[1] for c in cands)) / 90) + 1) if cands else 0
    chosen = []
    for c in sorted(cands, key=lambda c: c[0]):
        if len(chosen) >= want:
            break
        if all(abs(c[1] - d[1]) >= CROSS_GAP for d in chosen):
            chosen.append(c)
    for cost, x, piece, bl in chosen:
        for b in bl:                      # open the row: the house (and its plinth) standing in the way makes room
            if b in blocks:
                E.destroy_actor(b[5])
                blocks.remove(b)
                opened += 1
        pave(piece, "cross")
        ncross += 1
print("cross streets", ncross, "row pieces removed to open them", opened)

# ---------------------------------------------------------------- 3. grand bridge ends -> nearest street, straight or with right-angle turns
LINK_W = float(ARGS.get("link_width", "6"))
RAMP_MAX = float(ARGS.get("ramp_max", "0.12"))     # steeper than this over a short gap -> stone steps instead of a ramp


def full(p0, p1):
    pcs = profile(p0, p1, half=LINK_W / 2, min_pts=2)
    if len(pcs) != 1:
        return None
    pc = pcs[0]
    if math.hypot(pc[0][0][0] - p0[0], pc[0][0][1] - p0[1]) > 2.5 or math.hypot(pc[-1][0][0] - p1[0], pc[-1][0][1] - p1[1]) > 2.5:
        return None
    return pc


def on_any_street(px, py):
    for r in roads:
        if r["kind"] != "street":
            continue
        (ax, ay), (bx_, by_) = r["pts"][0], r["pts"][-1]
        if abs(ay - py) < 0.5 and min(ax, bx_) + 1 <= px <= max(ax, bx_) - 1:
            return True
    return False


def open_walls(piece):
    n = 0
    for (p0, _, _), (p1, _, _) in zip(piece, piece[1:]):
        x0, x1 = min(p0[0], p1[0]) - W / 2 - 0.5, max(p0[0], p1[0]) + W / 2 + 0.5
        y0, y1 = min(p0[1], p1[1]) - W / 2 - 0.5, max(p0[1], p1[1]) + W / 2 + 0.5
        for b in list(blocks):
            if b[4].startswith(("CK/Architecture/TerraceWalls", "CK/Architecture/Footings")) and b[0] < x1 and b[1] > x0 and b[2] < y1 and b[3] > y0:
                E.destroy_actor(b[5])
                blocks.remove(b)
                n += 1
    return n


nlink = walls_opened = 0
LANDINGS = {}
for a in E.get_all_level_actors():
    if not (isinstance(a, unreal.StaticMeshActor) and a.static_mesh_component.static_mesh and "Bridge_Grand" in a.static_mesh_component.static_mesh.get_name()):
        continue
    o, e = a.get_actor_bounds(False)
    bx = o.x / M
    for yend, sgn in (((o.y - e.y) / M, -1), ((o.y + e.y) / M, 1)):
        comp = a.static_mesh_component
        r = comp.line_trace_component(v(bx, yend - sgn * 8.0, 80), v(bx, yend - sgn * 8.0, -40), True, False, False)
        deck = r[0].z / M if isinstance(r, tuple) and r[1].length() > 0.5 else None      # deck level inside the end gate
        level = max(0.15, (deck if deck is not None else 0.15) - 3.0)
        yl = yend + sgn * 0.5          # the deck must reach the terrace: walk out to the first dry, unobstructed ground
        while abs(yl - yend) < 15 and (G(bx, yl) is None or G(bx, yl) < level or G(bx + W / 2, yl) is None or G(bx - W / 2, yl) is None
                                       or min(G(bx + W / 2, yl), G(bx - W / 2, yl)) < level):
            yl += sgn * 0.5
        if deck is not None and abs(yl - yend) > 0.6 and G(bx, yl) is not None and G(bx, yl) >= level:
            # stone abutment + paving across the open water between the deck end and the quay
            zl = G(bx, yl)
            n_ = max(2, int(abs(yl - yend) / STEP) + 1)
            gap = []
            for k in range(n_ + 1):
                t = k / n_
                yy = yend + (yl - yend) * t
                gz = [G(bx + d, yy) for d in (-W / 2, 0, W / 2)]
                gz = [g for g in gz if g is not None] or [-6.0]
                gap.append(((bx, yy), deck + (zl - deck) * t, min(gz)))
            IGNORE_WALLS[0] = True
            walls_opened += open_walls(gap)
            IGNORE_WALLS[0] = False
            span = abs(yl - yend)
            land = [G(bx + d * 0.5, yl + sgn * t) for d in range(-int(LINK_W), int(LINK_W) + 1) for t in (0.0, 0.5, 1.0, 1.5, 2.0)]
            land = [g_ for g_ in land if g_ is not None]
            zl = max(land) if land else zl            # the quay lip and the terrace just behind it, not one centre sample
            rise = zl + CLEAR - deck
            if abs(rise) / max(span, 0.1) > RAMP_MAX:
                # too steep for a ramp: a stone abutment from the lake bed to deck level, then straight stone steps to the quay
                bed = min(p_[2] for p_ in gap) - 0.5
                lo_z = min(deck, zl + CLEAR)
                L.spawn_mesh("/Engine/BasicShapes/Cube", v(bx, (yend + yl) / 2, (bed + lo_z) / 2), rot(),
                             (LINK_W + 0.6, span + 0.4, lo_z - bed), folder="CK/Bridge/Steps", material=PAVE, label="Bridge_Abutment_%d" % sgn)
                n_st = max(1, int(math.ceil(abs(rise) / 0.17)))
                tread = span / n_st
                for i in range(n_st):           # step i: from the lower end, each one a tread further and a riser higher
                    h_top = lo_z + abs(rise) * (i + 1) / n_st
                    if rise > 0:      # climbing from the deck: higher steps lie nearer the quay
                        y0, y1 = yend + sgn * i * tread, yl
                    else:             # descending from the deck: higher steps lie nearer the deck
                        y0, y1 = yend, yend + sgn * (n_st - i) * tread
                    yc_, ln_ = (y0 + y1) / 2, abs(y1 - y0)
                    L.spawn_mesh("/Engine/BasicShapes/Cube", v(bx, yc_, (lo_z + h_top) / 2), rot(), (LINK_W, ln_, h_top - lo_z),
                                 folder="CK/Bridge/Steps", material=PAVE, label="Bridge_Step_%d_%02d" % (sgn, i))
                print("bridge stairs", "west" if sgn < 0 else "east", n_st, "steps, rise", round(rise, 2), "m over", round(span, 1), "m")
            else:
                pave(gap, "link", LINK_W)
                roads[-1]["deck"] = deck          # the abutment starts exactly at deck level
            LANDINGS[sgn] = (bx, yl, zl + CLEAR)
            print("bridge abutment", "west" if sgn < 0 else "east", "deck", round(deck, 1), "-> quay", round(zl, 1), "over", round(abs(yl - yend), 1), "m")
        start = (bx, yl + sgn * 0.5)
        yend = yl
        best = None
        IGNORE_WALLS[0] = True
        for ys in sorted(street_ys, key=lambda q: abs(q - yend)):
            if (ys - yend) * sgn <= 0:
                continue
            if ARGS.get("debug"):
                pcs_ = profile(start, (bx, ys), min_pts=2)
                print("DBG bridge end", round(yend, 1), "start", [round(q, 1) for q in start], "street", ys, "on_street", on_any_street(bx, ys),
                      "pieces", [(round(pc[0][0][1], 1), round(pc[-1][0][1], 1), len(pc)) for pc in pcs_])
            if on_any_street(bx, ys):                                 # straight on
                pc = full(start, (bx, ys))
                if pc:
                    best = (abs(ys - yend), [pc])
                    break
            for out in (4.0, 8.0, 12.0):                              # out along the bridge, across, then on to the street
                p1 = (bx, yend + sgn * out)
                if (ys - p1[1]) * sgn < 4:
                    continue
                for dx in sorted(range(-80, 81, 4), key=abs):
                    if dx == 0 or not on_any_street(bx + dx, ys):
                        continue
                    p2 = (bx + dx, p1[1])
                    total = out + abs(dx) + abs(ys - p1[1])
                    if best and total >= best[0]:
                        continue
                    a1, a2, a3 = full(start, p1), full(p1, p2), full(p2, (bx + dx, ys))
                    if a1 and a2 and a3:
                        best = (total, [a1, a2, a3])
            if best:
                break
        IGNORE_WALLS[0] = False
        if best:
            for pc in best[1]:
                walls_opened += open_walls(pc)
                pave(pc, "link", LINK_W)
            nlink += 1
print("bridge links", nlink, "quay wall pieces opened", walls_opened)

# ---------------------------------------------------------------- 4. junctions: side roads stop on the street's kerb line
def street_at(px, py):
    """(road, z) of a street whose carriageway contains (px, py)."""
    for r in roads:
        if r["kind"] != "street":
            continue
        (ax, ay), (bx_, by_) = r["pts"][0], r["pts"][-1]
        if abs(ay - py) <= r["width"] / 2 + 0.01 and min(ax, bx_) - 0.01 <= px <= max(ax, bx_) + 0.01:
            xs = [p[0] for p in r["pts"]]
            k = min(range(len(xs)), key=lambda i: abs(xs[i] - px))
            return r, r["z"][k]
    return None, None


njoin = 0
for r in roads:
    if r["kind"] == "street":
        continue
    r.setdefault("join", {})
    for end in (0, -1):
        x, y = r["pts"][end]
        ox, oy = r["pts"][1 if end == 0 else -2]
        dl = math.hypot(x - ox, y - oy) or 1
        st = None
        for reach in (0.0, 1.0, 2.0, 3.0):      # a road ending just short of a street is carried on to its kerb
            st, zs = street_at(x + (x - ox) / dl * reach, y + (y - oy) / dl * reach)
            if st is not None:
                break
        if st is None:
            continue
        ys = st["pts"][0][1]
        r["pts"][end] = [x, ys + (st["width"] / 2 if y > ys else -st["width"] / 2)]
        r["join"][end] = st                     # its end height is fixed to that street once the street is final
        njoin += 1
print("junctions", njoin)

# ---------------------------------------------------------------- 5. every front door gets a road (extend / forecourt / drop)
town = [b for b in blocks if b[4] == "CK/Architecture/Town" and b[5].static_mesh_component.static_mesh.get_name() != "Cube"]
plinths = [b for b in blocks if b[4] == "CK/Architecture/Town" and b[5].static_mesh_component.static_mesh.get_name() == "Cube"]
extended = forecourts = 0
unserved = []
doors = []
for b in town:
    a = b[5]
    yaw = a.get_actor_rotation().yaw
    faces_down = abs(((yaw + 360) % 360) - 180) < 1           # yaw 180: facade toward -Y, its street lies at lower Y
    cx = (b[0] + b[1]) / 2
    bb = a.static_mesh_component.static_mesh.get_bounding_box()
    front = a.get_actor_location().y / M + (-bb.max.y / M if faces_down else bb.max.y / M)
    ys = front - W / 2 if faces_down else front + W / 2
    st, _ = street_at(cx, ys)
    if st is None:
        best = None                              # extend the nearest piece of this street along its own line to the door
        for r in [r for r in roads if r["kind"] == "street" and abs(r["pts"][0][1] - ys) < 0.5]:
            x0, x1 = r["pts"][0][0], r["pts"][-1][0]
            after = cx > x1
            src = x1 if after else x0
            tgt = cx + 5 if after else cx - 5
            if abs(tgt - src) > 40 or (x0 <= cx <= x1):
                continue
            pcs = profile((src, ys), (tgt, ys), min_pts=2)
            if len(pcs) == 1 and abs(pcs[0][0][0][0] - src) < 2.5 and abs(pcs[0][-1][0][0] - tgt) < 2.5:
                if best is None or abs(tgt - src) < best[0]:
                    best = (abs(tgt - src), r, pcs[0], after)
        if best:
            _, r, pc, after = best
            add_p = [list(p) for p, _, _ in pc[1:]]
            add_z = [z for _, z, _ in pc[1:]]
            add_l = [lo for _, _, lo in pc[1:]]
            if after:
                r["pts"] += add_p
                r["z"] += add_z
                r["low"] += add_l
            else:
                r["pts"] = add_p[::-1] + r["pts"]
                r["z"] = add_z[::-1] + r["z"]
                r["low"] = add_l[::-1] + r["low"]
            extended += 1
            st, _ = street_at(cx, ys)
    if st is None:
        hw = (b[1] - b[0]) / 2 + 2.0             # last resort: a paved forecourt in front of this house (quay walls may be crossed)
        for fw in (W, 5.0):
            yc = ys if fw == W else front + (-fw / 2 if faces_down else fw / 2)
            IGNORE_WALLS[0] = True
            pcs = profile((cx - hw, yc), (cx + hw, yc), half=fw / 2, min_pts=2)
            IGNORE_WALLS[0] = False
            pcs = [pc for pc in pcs if pc[0][0][0] <= cx - 1.5 and pc[-1][0][0] >= cx + 1.5]
            if pcs:
                walls_opened += open_walls(pcs[0])
                pave(pcs[0], "street", fw)
                st = roads[-1]
                forecourts += 1
                break
    if st is None:
        # no road can reach this door (cliff edge): take the house and its plinth down - every standing door opens onto paving
        unserved.append((a.get_actor_label(), round(cx, 1), round(front, 1)))
        if ARGS.get("drop_unreachable", "1") == "1":
            for pb in plinths:
                if pb[0] < cx < pb[1] and pb[2] < (b[2] + b[3]) / 2 < pb[3]:
                    E.destroy_actor(pb[5])
            E.destroy_actor(a)
        continue
    doors.append((b, a, cx, front, faces_down, st))
print("forecourts", forecourts, "| streets extended", extended, "| unreachable (removed)", unserved)


# ---------------------------------------------------------------- 5b. pieces of one street that (almost) touch become one road
merged_n = 0
while True:
    pair = None
    sts = sorted([r for r in roads if r["kind"] == "street"], key=lambda r: (round(r["pts"][0][1], 1), r["pts"][0][0]))
    for a_, b_ in zip(sts, sts[1:]):
        if abs(a_["pts"][0][1] - b_["pts"][0][1]) < 0.05 and a_["width"] == b_["width"] and 0 <= b_["pts"][0][0] - a_["pts"][-1][0] <= STEP * 1.5:
            pair = (a_, b_)
            break
    if pair is None:
        break
    a_, b_ = pair
    a_["pts"] += b_["pts"]
    a_["z"] += b_["z"]
    a_["low"] += b_["low"]
    roads.remove(b_)
    doors = [(d[0], d[1], d[2], d[3], d[4], a_ if d[5] is b_ else d[5]) for d in doors]
    for r in roads:
        for k_, st_ in list(r.get("join", {}).items()):
            if st_ is b_:
                r["join"][k_] = a_
    merged_n += 1
print("street pieces merged", merged_n)

# ---------------------------------------------------------------- 5c. one network: straight right-angle connectors between road groups
if -1 in LANDINGS and 1 in LANDINGS:
    (bxw, ylw, zw), (bxe, yle, ze) = LANDINGS[-1], LANDINGS[1]
    roads.append({"kind": "bridge", "virtual": True, "width": LINK_W, "pts": [[bxw, ylw], [bxe, yle]], "z": [zw, ze], "low": [zw, ze]})
CONN_W = float(ARGS.get("conn_width", "6"))
CONN_MAX = float(ARGS.get("conn_max", "90"))


def axis(r):
    (x0, y0), (x1, y1) = r["pts"][0], r["pts"][-1]
    ln = math.hypot(x1 - x0, y1 - y0) or 1
    return (x1 - x0) / ln, (y1 - y0) / ln, ln


def inside_road(r, x, y, margin=0.0):
    """Is (x, y) on the carriageway of straight road r?"""
    (x0, y0) = r["pts"][0]
    ux, uy, ln = axis(r)
    t = (x - x0) * ux + (y - y0) * uy
    d = abs(-(x - x0) * uy + (y - y0) * ux)
    return -margin <= t <= ln + margin and d <= r["width"] / 2 + margin


def touching(a, b):
    for x, y in a["pts"][::2] + [a["pts"][-1]]:
        if inside_road(b, x, y, 0.6):
            return True
    for x, y in b["pts"][::2] + [b["pts"][-1]]:
        if inside_road(a, x, y, 0.6):
            return True
    return False


def groups():
    par = list(range(len(roads)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i in range(len(roads)):
        for j in range(i + 1, len(roads)):
            if touching(roads[i], roads[j]):
                par[f(i)] = f(j)
    gs = {}
    for i in range(len(roads)):
        gs.setdefault(f(i), []).append(i)
    return list(gs.values())


def ray(src, sx, sy, dx, dy):
    """March from (sx, sy) along (dx, dy) until another road is met: (length, hit road, hit point) or None."""
    half = CONN_W / 2
    for step_ in range(2, int(CONN_MAX) + 1):
        x, y = sx + dx * step_, sy + dy * step_
        for r in roads:
            if r is not src and inside_road(r, x, y):
                return step_, r, (x, y)
        IGNORE_WALLS[0] = True
        bad = blocked(x, y, half - 0.4)
        IGNORE_WALLS[0] = False
        zs = [G(x - dy * s_ * half, y + dx * s_ * half) for s_ in (-1, 0, 1)]
        if bad or any(z is None or z < 0.15 for z in zs):
            return None
    return None


nconn = 0
failed = set()
import time as _time
_t_end = _time.time() + float(ARGS.get("conn_seconds", "300"))
for _ in range(40):
    if _time.time() > _t_end:
        print("connector search stopped: time budget used")
        break
    gs = groups()
    n_before = len(gs)
    if len(gs) <= 1:
        break
    big = max(gs, key=lambda g_: sum(axis(roads[i])[2] for i in g_))
    best = None
    for g_ in gs:
        if g_ is big:
            continue
        for i in g_:
            r = roads[i]
            ux, uy, ln = axis(r)
            nx, ny = -uy, ux
            # perpendicular from every 4 m of the road edge, and straight on from both ends
            tries = []
            for t in ([] if r.get("virtual") else [k_ * 4.0 for k_ in range(int(ln // 4) + 1)]):
                cx, cy = r["pts"][0][0] + ux * t, r["pts"][0][1] + uy * t
                for sgn in (1, -1):
                    tries.append((cx + nx * sgn * r["width"] / 2, cy + ny * sgn * r["width"] / 2, nx * sgn, ny * sgn))
            tries.append((r["pts"][-1][0], r["pts"][-1][1], ux, uy))
            tries.append((r["pts"][0][0], r["pts"][0][1], -ux, -uy))
            for sx, sy, dx, dy in tries:
                if (round(sx), round(sy), round(dx), round(dy)) in failed:
                    continue
                hit = ray(r, sx, sy, dx, dy)
                if hit is None:
                    continue
                L_, tgt, hp = hit
                if roads.index(tgt) in g_:
                    continue
                if best is None or L_ < best[0]:
                    best = (L_, r, tgt, (sx, sy), hp, (dx, dy))
    if best is None:
        # one right-angle corner: out along (dx, dy) for d1 metres, then straight on at 90 degrees until a road is met
        for g_ in gs:
            if g_ is big:
                continue
            for i in g_:
                r = roads[i]
                ux, uy, ln = axis(r)
                nx, ny = -uy, ux
                starts = [(r["pts"][-1][0], r["pts"][-1][1], ux, uy), (r["pts"][0][0], r["pts"][0][1], -ux, -uy)]
                for t in ([] if r.get("virtual") else [k_ * 4.0 for k_ in range(int(ln // 4) + 1)]):
                    cx, cy = r["pts"][0][0] + ux * t, r["pts"][0][1] + uy * t
                    for sgn in (1, -1):
                        starts.append((cx + nx * sgn * r["width"] / 2, cy + ny * sgn * r["width"] / 2, nx * sgn, ny * sgn))
                for sx, sy, dx, dy in starts:
                    for d1 in range(6, 42, 2):
                        h1 = ray(r, sx, sy, dx, dy)
                        if h1 is not None and h1[0] <= d1:
                            break
                        cxp, cyp = sx + dx * d1, sy + dy * d1
                        IGNORE_WALLS[0] = True
                        ok1 = all(not blocked(sx + dx * q, sy + dy * q, CONN_W / 2 - 0.4) for q in range(2, d1 + 1))
                        IGNORE_WALLS[0] = False
                        if not ok1 or any(G(sx + dx * q, sy + dy * q) is None or G(sx + dx * q, sy + dy * q) < 0.15 for q in range(2, d1 + 1)):
                            break
                        for sg2 in (1, -1):
                            ex, ey = -dy * sg2, dx * sg2
                            h2 = ray(r, cxp - ex * CONN_W / 2, cyp - ey * CONN_W / 2, ex, ey)
                            if h2 is None or roads.index(h2[1]) in g_ or h2[0] < 3:
                                continue
                            tot = d1 + h2[0]
                            if best is None or tot < best[0]:
                                best = (tot, r, h2[1], (sx, sy), (cxp, cyp), (dx, dy), (ex, ey), h2[2])
        if best is None:
            break
        tot, r, tgt, sp, cp, (dx, dy), (ex, ey), hp = best
        IGNORE_WALLS[0] = True
        leg1 = profile(sp, (cp[0] + dx * CONN_W / 2, cp[1] + dy * CONN_W / 2), half=CONN_W / 2, min_pts=2, cliffs_ok=True)
        IGNORE_WALLS[0] = False
        if len(leg1) != 1:
            failed.add((round(sp[0]), round(sp[1]), round(dx), round(dy)))
            continue
        walls_opened += open_walls(leg1[0])
        pave(leg1[0], "connector", CONN_W)
        roads[-1]["join"] = {0: r}
        corner = roads[-1]
        tx, ty = hp
        tux, tuy, _ = axis(tgt)
        if abs(ex * tux + ey * tuy) < 0.5:
            (x0, y0) = tgt["pts"][0]
            d = -(tx - x0) * tuy + (ty - y0) * tux
            off = d - math.copysign(tgt["width"] / 2, d)
            tx, ty = tx + tuy * off, ty - tux * off
        IGNORE_WALLS[0] = True
        leg2 = profile((cp[0] + ex * CONN_W / 2, cp[1] + ey * CONN_W / 2), (tx, ty), half=CONN_W / 2, min_pts=2, cliffs_ok=True)
        IGNORE_WALLS[0] = False
        if len(leg2) != 1:
            roads.remove(corner)
            failed.add((round(sp[0]), round(sp[1]), round(dx), round(dy)))
            continue
        walls_opened += open_walls(leg2[0])
        pave(leg2[0], "connector", CONN_W)
        roads[-1]["join"] = {0: corner, -1: tgt}
        if len(groups()) >= n_before:             # did not join anything new: take both legs back
            roads.remove(roads[-1])
            roads.remove(corner)
            failed.add((round(sp[0]), round(sp[1]), round(dx), round(dy)))
            continue
        nconn += 1
        print("L-connector", nconn, [round(v, 1) for v in sp], "->", [round(v, 1) for v in cp], "->", [round(v, 1) for v in (tx, ty)], round(tot), "m")
        continue
    L_, r, tgt, sp, hp, (dx, dy) = best
    # stop exactly on the target's kerb line
    tx, ty = hp
    tux, tuy, _ = axis(tgt)
    if abs(dx * tux + dy * tuy) < 0.5:          # meeting the target side-on: end on its kerb
        (x0, y0) = tgt["pts"][0]
        d = -(tx - x0) * tuy + (ty - y0) * tux
        off = d - math.copysign(tgt["width"] / 2, d)
        tx, ty = tx + tuy * off, ty - tux * off
    IGNORE_WALLS[0] = True
    pcs = profile(sp, (tx, ty), half=CONN_W / 2, min_pts=2, cliffs_ok=True)
    IGNORE_WALLS[0] = False
    if len(pcs) != 1:
        failed.add((round(sp[0]), round(sp[1]), round(dx), round(dy)))
        continue
    pave(pcs[0], "connector", CONN_W)
    roads[-1]["join"] = {0: r, -1: tgt}
    if len(groups()) >= n_before:                 # did not join anything new: take it back
        roads.remove(roads[-1])
        failed.add((round(sp[0]), round(sp[1]), round(dx), round(dy)))
        continue
    walls_opened += open_walls(pcs[0])
    nconn += 1
    print("connector", nconn, [round(v, 1) for v in sp], "->", [round(v, 1) for v in (tx, ty)], round(L_), "m")
gs = groups()
print("connectors", nconn, "| road groups left", len(gs), [round(sum(axis(roads[i])[2] for i in g_)) for g_ in gs])

# ---------------------------------------------------------------- 6. final height: dead-level stretches joined by straight ramps
RAMP = float(ARGS.get("ramp_grade", "0.08"))        # one constant grade for every ramp (8 %)
TOL = float(ARGS.get("level_tol", "0.6"))           # rock relief swallowed by one level stretch
MIN_FLAT = int(ARGS.get("min_flat", "4"))           # samples (x STEP m)
MERGE_DH = float(ARGS.get("merge_dh", "0.5"))
STAIR = float(ARGS.get("stair_grade", "0.58"))      # a flight of steps: 0.17 m risers on 0.29 m treads       # neighbouring levels closer than this become one level (no micro ramps)


def need_at(r):
    """Per sample: the highest rock under the paving within 1 m along, + CLEAR."""
    pts_ = r["pts"]
    half = r["width"] / 2
    n_ = len(pts_)
    out = []
    for k in range(n_):
        a0, a1 = pts_[max(k - 1, 0)], pts_[min(k + 1, n_ - 1)]
        ln = math.hypot(a1[0] - a0[0], a1[1] - a0[1]) or 1
        ux, uy = (a1[0] - a0[0]) / ln, (a1[1] - a0[1]) / ln
        best = None
        for t in (-1.0, -0.5, 0.0, 0.5, 1.0):
            for i in range(-int(half / 0.5), int(half / 0.5) + 1):
                gz = G(pts_[k][0] + ux * t - uy * i * 0.5, pts_[k][1] + uy * t + ux * i * 0.5)
                if gz is not None and (best is None or gz > best):
                    best = gz
        out.append((best if best is not None else r["z"][k] - CLEAR) + CLEAR)
    return out


def terrace(need, fix0=None, fix1=None):
    """Heights made only of horizontal stretches and constant-grade straight ramps, never below `need`.
    fix0 / fix1: fixed heights at the first / last sample (a junction with a finished street, a bridge deck)."""
    n = len(need)
    flats = []                                   # [start, end, height, fixed]
    i = 0
    while i < n:
        j, lo, hi = i, need[i], need[i]
        while j + 1 < n and max(hi, need[j + 1]) - min(lo, need[j + 1]) <= TOL:
            j += 1
            hi, lo = max(hi, need[j]), min(lo, need[j])
        flats.append([i, j, hi, False])
        i = j + 1
    if fix0 is not None:                          # a one-sample fixed stretch at the very end
        f = flats[0]
        if f[1] == f[0]:
            f[2], f[3] = fix0, True
        else:
            flats.insert(0, [0, 0, fix0, True])
            f[0] = 1
    if fix1 is not None:
        f = flats[-1]
        if f[1] == f[0] and not f[3]:
            f[2], f[3] = fix1, True
        else:
            f[1] -= 1
            flats.append([n - 1, n - 1, fix1, True])
    flats = [f for f in flats if f[1] >= f[0]]

    def ramp_len(dh):
        return int(math.ceil(abs(dh) / (RAMP * STEP)))

    def stair_len(dh):
        return max(1, int(math.ceil(abs(dh) / (STAIR * STEP))))

    kinds = {}

    for _ in range(400):
        changed = False
        for k in range(len(flats) - 1):           # near-equal neighbours: one level at the higher height
            a_, b_ = flats[k], flats[k + 1]
            if not (a_[3] or b_[3]) and abs(a_[2] - b_[2]) < MERGE_DH:
                flats[k:k + 2] = [[a_[0], b_[1], max(a_[2], b_[2]), False]]
                changed = True
                break
        if changed:
            continue
        # a short free stretch joins its nearer-height neighbour at the higher of the two levels
        for k, f in enumerate(flats):
            if f[3] or f[1] - f[0] + 1 >= MIN_FLAT or len(flats) == 1:
                continue
            nbs = [m for m in (k - 1, k + 1) if 0 <= m < len(flats)]
            m = min(nbs, key=lambda q: abs(flats[q][2] - f[2]))
            g = flats[m]
            if g[3]:
                f[2] = max(f[2], g[2]) if abs(g[2] - f[2]) > 1e-6 else f[2]
                if len(nbs) == 1:
                    continue
                m = [q for q in nbs if q != m][0]
                g = flats[m]
            lo_, hi_ = sorted((k, m))
            flats[lo_:hi_ + 1] = [[flats[lo_][0], flats[hi_][1], max(f[2], g[2]), g[3]]]
            changed = True
            break
        if changed:
            continue
        # every ramp lies inside the lower stretch of its pair; a stretch too short for its ramps is raised to its neighbour
        kinds = {}

        def rooms():
            rm = [0] * len(flats)
            for k in range(len(flats) - 1):
                a_, b_ = flats[k], flats[k + 1]
                if abs(a_[2] - b_[2]) < 1e-6:
                    continue
                low = k if a_[2] < b_[2] else k + 1
                if flats[low][3]:
                    low = k + 1 if low == k else k      # cannot ramp inside a fixed sample: use the other side
                rm[low] += (stair_len if kinds.get(k) == "stair" else ramp_len)(a_[2] - b_[2])
            return rm
        room = rooms()
        for k, f in enumerate(flats):              # too short for its ramps: turn them into flights of steps
            if room[k] and not f[3] and f[1] - f[0] + 1 < room[k] + 1:
                for bk in (k - 1, k):
                    if 0 <= bk < len(flats) - 1:
                        kinds[bk] = "stair"
        room = rooms()
        for k, f in enumerate(flats):
            if room[k] and not f[3] and f[1] - f[0] + 1 < room[k] + 1:
                nbs = [m for m in (k - 1, k + 1) if 0 <= m < len(flats) and flats[m][2] > f[2]]
                if not nbs:
                    continue
                m = min(nbs, key=lambda q: flats[q][2])
                g = flats[m]
                lo_, hi_ = sorted((k, m))
                flats[lo_:hi_ + 1] = [[flats[lo_][0], flats[hi_][1], g[2], g[3]]]
                changed = True
                break
        if not changed:
            break
    # merge equal neighbours
    merged = []
    for f in flats:
        if merged and abs(merged[-1][2] - f[2]) < 1e-6 and not (merged[-1][3] or f[3]):
            merged[-1][1] = f[1]
        else:
            merged.append(list(f))
    flats = merged
    z = [0.0] * n
    for f in flats:
        for k in range(f[0], f[1] + 1):
            z[k] = f[2]
    for k in range(len(flats) - 1):
        a_, b_ = flats[k], flats[k + 1]
        dh = b_[2] - a_[2]
        if abs(dh) < 1e-6:
            continue
        nr = (stair_len if kinds.get(k) == "stair" else ramp_len)(dh)
        low_is_a = dh > 0
        if (a_ if low_is_a else b_)[3]:
            low_is_a = not low_is_a
        if low_is_a:      # ramp at the end of A, rising (or falling) straight into B's level
            k0, k1 = max(a_[0], a_[1] - nr), b_[0]
        else:             # ramp at the start of B
            k0, k1 = a_[1], min(b_[1], b_[0] + nr)
        z0_, z1_ = a_[2], b_[2]

        def line(kk, k0=k0, k1=k1, z0_=z0_, z1_=z1_):
            return z0_ + (z1_ - z0_) * (kk - k0) / max(1, k1 - k0)
        # next to a fixed end lower than the rock beside it: shorten (steepen) the ramp until its straight line clears the rock
        while any(line(kk) < need[kk] - 1e-6 for kk in range(k0, k1 + 1)) and k1 - k0 > 1:
            if low_is_a:
                k0 += 1
            else:
                k1 -= 1
        for kk in range(k0, k1 + 1):
            z[kk] = line(kk)
    return z


def ends(r):
    f0 = f1 = None
    for end, st in r.get("join", {}).items():
        x, y = r["pts"][end]
        k = min(range(len(st["pts"])), key=lambda i: (st["pts"][i][0] - x) ** 2 + (st["pts"][i][1] - y) ** 2)
        if end == 0:
            f0 = st["z"][k]
        else:
            f1 = st["z"][k]
    if r.get("deck") is not None:
        f0 = r["deck"]
    return f0, f1


viol = 0
for kind_pass in ("street", "cross", "link", "connector"):   # ('bridge' is virtual: its heights are the landings)
    for r in roads:
        if r["kind"] != kind_pass:
            continue
        need = need_at(r)
        f0, f1 = ends(r) if kind_pass != "street" else (None, None)
        z = terrace(need, f0, f1)
        for k in range(len(z)):                  # a fixed-end ramp that would cut into rock: that sample is lifted (reported)
            if z[k] < need[k] - 1e-6:
                z[k] = need[k]
                viol += 1
        r["z"] = z
print("level stretches + straight ramps (grade %.0f %%); samples lifted off a ramp line: %d" % (RAMP * 100, viol))

# ---------------------------------------------------------------- 7. doors meet the final paving
served = raised = stepped = 0
for b, a, cx, front, faces_down, st in doors:
    xs = [p[0] for p in st["pts"]]
    k = min(range(len(xs)), key=lambda i: abs(xs[i] - cx))
    zr = st["z"][k]
    served += 1
    floor = a.get_actor_location().z / M
    if zr > floor + 0.03:
        d = zr - floor                           # the paving is higher than the threshold: lift the house and its plinth top
        a.set_actor_location(a.get_actor_location() + unreal.Vector(0, 0, d * M), False, False)
        for pb in plinths:
            if pb[0] < cx < pb[1] and pb[2] < (b[2] + b[3]) / 2 < pb[3]:
                pa = pb[5]
                o, e = pa.get_actor_bounds(False)
                bottom = (o.z - e.z) / M
                top = floor + d
                pa.set_actor_location(v(o.x / M, o.y / M, (bottom + top) / 2), False, False)
                sc = pa.get_actor_scale3d()
                pa.set_actor_scale3d(unreal.Vector(sc.x, sc.y, top - bottom))
        raised += 1
    elif floor - zr > 0.22:
        rise = floor - zr                        # door above the paving: dressed-stone steps down onto the street
        n_ = int(math.ceil(rise / 0.18))
        rh = rise / n_
        out = -1 if faces_down else 1
        for i in range(n_):
            depth = 0.4 + (i + 1) * 0.32
            top_z = floor - i * rh
            L.spawn_mesh("/Engine/BasicShapes/Cube", v(cx, front + out * depth / 2, (top_z + zr - 0.2) / 2),
                         rot(), (2.8, depth, top_z - (zr - 0.2)), folder="CK/Architecture/Town/Steps", material=PAVE,
                         label="Town_Steps_%s_%02d" % (a.get_actor_label(), i))
        stepped += 1
print("doors on a street", served, "| houses lifted to the paving", raised, "| front steps", stepped)

roads = [r for r in roads if not r.get("virtual")]      # the bridge stays a landmark, not paving
poke = checked = 0
worst = 0.0
for r in roads:
    pts_, zz = r["pts"], r["z"]
    half = r["width"] / 2
    for (x0, y0), (x1, y1), z0_, z1_ in zip(pts_, pts_[1:], zz, zz[1:]):
        ln = math.hypot(x1 - x0, y1 - y0) or 1
        ux, uy = (x1 - x0) / ln, (y1 - y0) / ln
        for a_ in range(int(ln / 0.5) + 1):
            t = min(a_ * 0.5, ln)
            zt = z0_ + (z1_ - z0_) * t / ln
            for b_ in range(-int(half / 0.5), int(half / 0.5) + 1):
                gx, gy = x0 + ux * t - uy * b_ * 0.5, y0 + uy * t + ux * b_ * 0.5
                gz = G(gx, gy)
                checked += 1
                if gz is not None and gz > zt - 0.02:
                    poke += 1
                    worst = max(worst, gz - zt)
print("rock-through check: %d of %d points under the paving reach its surface (worst %.2f m)" % (poke, checked, worst))
segs = []
for r in roads:
    for (x0, y0), (x1, y1) in zip(r["pts"], r["pts"][1:]):
        segs.append((min(x0, x1) - W / 2 - 1, max(x0, x1) + W / 2 + 1, min(y0, y1) - W / 2 - 1, max(y0, y1) + W / 2 + 1))
cleared = 0
for a in E.get_all_level_actors():
    f = str(a.get_folder_path())
    if not f.startswith(CRYSTALS):
        continue
    o, e = a.get_actor_bounds(False)
    if (o.z - e.z) / M > 35:
        continue
    x0, x1, y0, y1 = (o.x - e.x * 0.7) / M, (o.x + e.x * 0.7) / M, (o.y - e.y * 0.7) / M, (o.y + e.y * 0.7) / M
    if any(not (x1 < s0 or s1 < x0 or y1 < t0 or t1 < y0) for s0, s1, t0, t1 in segs):
        E.destroy_actor(a)
        cleared += 1
with open(os.path.join(unreal.Paths.project_saved_dir(), "road_plan.json"), "w", encoding="utf-8") as fh:
    json.dump({"roads": [{"kind": r["kind"], "width": r["width"], "pts": r["pts"]} for r in roads], "lake_centre": [170, 5]}, fh)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
with open(os.path.join(unreal.Paths.project_saved_dir(), "road_mesh.json"), "w", encoding="utf-8") as fh:
    json.dump({"width": W, "roads": [{"name": "SM_Road_%s_%02d" % (r["kind"].capitalize(), i), "kind": r["kind"], "w": r["width"], "pts": r["pts"],
                                      "z": r["z"], "low": r["low"]} for i, r in enumerate(roads)]}, fh)
print("STREETS roads", len(roads), "crystals cleared", cleared, "-> Saved/road_mesh.json (meshes: SourceArt/Blender/gen_roads.py)")
