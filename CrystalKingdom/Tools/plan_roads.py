"""Plan the road network from Saved/map_data.json -> Saved/road_plan.json (built by ck_build_level.py stage=roads).
  1. ring road (6 m) round the lake, ~8 m outside the outer shoreline, smoothed into organic curves
  2. a straight spur (4 m) from every front door to the nearest road (one corner at most), T-joined
  3. a few straight lanes (3.5 m) between neighbouring doors where they add a shortcut
usage: python plan_roads.py <map_data.json> <road_plan.json>
"""
import json
import math
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
xs, ys, step, cells = data["xs"], data["ys"], data["step"], data["cells"]
NX, NY = len(xs), len(ys)


def idx(x, y):
    i = int(round((x - xs[0]) / step))
    j = int(round((y - ys[0]) / step))
    return (i, j) if 0 <= i < NX and 0 <= j < NY else None


def ground(x, y):
    c = idx(x, y)
    if c is None:
        return None
    cell = cells[c[0]][c[1]]
    z = cell[2] if len(cell) > 2 and cell[2] is not None else cell[1]
    if z is None:
        return None
    return max(z, 1.4) if z < -0.3 else z      # water: the causeway deck height


def too_steep(path, step_max=0.8, grade=0.25):
    """True when a straight road would have to climb a terrace edge (embankment towers / gaps)."""
    h = [ground(x, y) for x, y in path]
    h = [v for v in h if v is not None]
    if len(h) < 2:
        return False
    hs = [(h[max(k - 1, 0)] + h[k] + h[min(k + 1, len(h) - 1)]) / 3 for k in range(len(h))]
    if any(abs(hs[k + 1] - hs[k]) > step_max for k in range(len(hs) - 1)):
        return True
    L = math.hypot(path[-1][0] - path[0][0], path[-1][1] - path[0][1]) or 1
    return abs(hs[-1] - hs[0]) > grade * L + 0.6


def is_lake(i, j):
    cell = cells[i][j]
    z = cell[2] if len(cell) > 2 and cell[2] is not None else cell[1]   # terrain height, ignoring crystals standing in the water
    return z is not None and z < -0.3


# ---------------------------------------------------------------- lake distance field (BFS, metres)
INF = 1e9
dist = [[INF] * NY for _ in range(NX)]
q = []
for i in range(NX):
    for j in range(NY):
        if is_lake(i, j):
            dist[i][j] = 0.0
            q.append((i, j))
h = 0
while h < len(q):
    i, j = q[h]
    h += 1
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a, b = i + di, j + dj
        if 0 <= a < NX and 0 <= b < NY and dist[a][b] > dist[i][j] + step:
            dist[a][b] = dist[i][j] + step
            q.append((a, b))

lake = [(xs[i], ys[j]) for i in range(NX) for j in range(NY) if is_lake(i, j)]
cx = sum(p[0] for p in lake) / len(lake)
cy = sum(p[1] for p in lake) / len(lake)

# ---------------------------------------------------------------- buildings and doors
blds = [s for s in data["shapes"] if s["kind"] == "building" and "door" in s]


def inside(poly, x, y, grow=1.5):
    # point in convex quad grown by `grow` metres (test against each edge's inward normal)
    n = len(poly)
    area = sum(poly[k][0] * poly[(k + 1) % n][1] - poly[(k + 1) % n][0] * poly[k][1] for k in range(n))
    sgn = 1 if area > 0 else -1
    for k in range(n):
        x0, y0 = poly[k]
        x1, y1 = poly[(k + 1) % n]
        ex, ey = x1 - x0, y1 - y0
        L = math.hypot(ex, ey) or 1
        if sgn * (ex * (y - y0) - ey * (x - x0)) / L < -grow:
            return False
    return True


for _b in blds:
    _b["bb"] = (min(p[0] for p in _b["pts"]) - 2, max(p[0] for p in _b["pts"]) + 2,
                min(p[1] for p in _b["pts"]) - 2, max(p[1] for p in _b["pts"]) + 2)


def blocked(path, skip=()):
    for (x, y) in path[1:-1]:
        for b in blds:
            bb = b["bb"]
            if not (bb[0] < x < bb[1] and bb[2] < y < bb[3]):
                continue
            if inside(b["pts"], x, y, grow=(-0.3 if b["label"] in skip else 1.5)):
                return True
    return False


def bezier(p0, c, p1, spacing=2.0):
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) + 1e-6
    m = max(2, int(L / spacing))
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1])
            for t in (k / m for k in range(m + 1))]


# ---------------------------------------------------------------- ring: outermost shore along rays + offset
OFF = 8.0
ring = []
for k in range(0, 360, 3):
    a = math.radians(k)
    dx, dy = math.cos(a), math.sin(a)
    last_lake = None
    r = 0.0
    while r < 400:
        p = idx(cx + dx * r, cy + dy * r)
        if p is None:
            break
        if is_lake(*p):
            last_lake = r
        r += 1.0
    if last_lake is None:
        continue
    # walk outward from the outer shore until the lake is OFF metres away
    r = last_lake
    while r < last_lake + 40:
        p = idx(cx + dx * r, cy + dy * r)
        if p is None or dist[p[0]][p[1]] >= OFF:
            break
        g_ = ground(cx + dx * r, cy + dy * r)
        if g_ is not None and g_ > 2.5 and r > last_lake + 1.0:   # terrace foot: stay on the low quay
            r -= 1.0
            break
        r += 0.5
    ring.append((cx + dx * r, cy + dy * r))

# smooth (circular moving average), then Catmull-Rom resample every 2 m
def smooth_closed(pts, w=3, it=3):
    for _ in range(it):
        n = len(pts)
        pts = [(sum(pts[(k + d) % n][0] for d in range(-w, w + 1)) / (2 * w + 1),
                sum(pts[(k + d) % n][1] for d in range(-w, w + 1)) / (2 * w + 1)) for k in range(n)]
    return pts


def catmull(pts, spacing=2.0, closed=True):
    out = []
    n = len(pts)
    rng = range(n) if closed else range(n - 1)
    for k in rng:
        p0, p1, p2, p3 = pts[(k - 1) % n], pts[k], pts[(k + 1) % n], pts[(k + 2) % n]
        if not closed:
            p0 = pts[max(k - 1, 0)]
            p2 = pts[k + 1]
            p3 = pts[min(k + 2, n - 1)]
        L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        m = max(1, int(L / spacing))
        for s in range(m):
            t = s / m
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[d]) + (-p0[d] + p2[d]) * t + (2 * p0[d] - 5 * p1[d] + 4 * p2[d] - p3[d]) * t2 +
                                    (-p0[d] + 3 * p1[d] - 3 * p2[d] + p3[d]) * t3) for d in range(2)))
    if not closed:
        out.append(pts[-1])
    return out


ring = catmull(smooth_closed(ring), 2.0, closed=True)

# steer ring points out of building footprints (toward the lake; water stretches become causeways)
def steer(ring, grow):
    """Push ring points out of building footprints: the nearest free spot toward the lake or straight away from the building."""
    moved = 0
    for k, (x, y) in enumerate(ring):
        hit = [b for b in blds if inside(b["pts"], x, y, grow=grow)]
        if not hit:
            continue
        b = hit[0]
        bx = sum(p[0] for p in b["pts"]) / len(b["pts"])
        by = sum(p[1] for p in b["pts"]) / len(b["pts"])
        dirs = [(cx - x, cy - y), (x - bx, y - by)]
        best = None
        for dx, dy in dirs:
            dl = math.hypot(dx, dy) or 1
            for s_ in range(1, 80):
                nx_, ny_ = x + dx / dl * s_ * 0.5, y + dy / dl * s_ * 0.5
                if not any(inside(o["pts"], nx_, ny_, grow=grow) for o in blds):
                    if best is None or s_ < best[0]:
                        best = (s_, (nx_, ny_))
                    break
        if best:
            ring[k] = best[1]
            moved += 1
    return moved


def lower_ring(ring, top=3.0):
    n = 0
    for k, (x, y) in enumerate(ring):
        g = ground(x, y)
        if g is not None and g > top:
            dx, dy = cx - x, cy - y
            dl = math.hypot(dx, dy) or 1
            for s_ in range(1, 120):
                nx_, ny_ = x + dx / dl * s_ * 0.5, y + dy / dl * s_ * 0.5
                g2 = ground(nx_, ny_)
                if g2 is not None and g2 <= top:
                    ring[k] = (nx_, ny_)
                    n += 1
                    break
    return n


def densify(pts, step=2.0):
    out = []
    n = len(pts)
    for k in range(n):
        a, b = pts[k], pts[(k + 1) % n]
        m = max(1, int(math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / step)))
        out += [(a[0] + (b[0] - a[0]) * t / m, a[1] + (b[1] - a[1]) * t / m) for t in range(m)]
    return out


moved = 0
for it in range(4):
    moved += steer(ring, 5.0)
    ring = catmull(smooth_closed(ring[::2], w=2, it=2), 2.0, closed=True)
ring = densify(ring)
for _ in range(3):                       # final clearance pass: smoothing must not pull the ring back into a footprint
    moved += steer(ring, 4.0)
    ring = smooth_closed(ring, w=1, it=1)
moved += steer(ring, 3.5)
ring = densify(ring)
print("ring points still on terraces:", sum(1 for x, y in ring if (ground(x, y) or 0) > 3.0))
print("ring points steered round buildings:", moved)
roads = [{"kind": "ring", "width": 6.0, "pts": ring}]


# ---------------------------------------------------------------- small roads: straight lines only
def line(p0, p1, spacing=2.0):
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    m = max(1, int(round(L / spacing)))
    return [(p0[0] + (p1[0] - p0[0]) * k / m, p0[1] + (p1[1] - p0[1]) * k / m) for k in range(m + 1)]


def wet_frac(path):
    w = sum(1 for x, y in path if (lambda c: c is not None and is_lake(*c))(idx(x, y)))
    return w / max(1, len(path))


def fg(x, y):
    return x < 45 and -45 < y < 55        # the ring is left open in the camera foreground (ck_build_level): never join there


RING_OPEN = set()


def mark_ring_open():
    """Ring points left unbuilt for the camera: the foreground box plus the causeway stretches that run into it
    (same rule as ck_build_level.build_roads), so nothing is ever joined to a road that will not exist."""
    pts = roads[0]["pts"]
    n = len(pts)
    wet = [(lambda c: c is None or is_lake(*c))(idx(x, y)) for x, y in pts]
    op = [fg(*pts[k]) for k in range(n)]
    changed = True
    while changed:
        changed = False
        for k in range(n):
            if not op[k] and wet[k] and (op[k - 1] or op[(k + 1) % n]):
                op[k] = changed = True
    RING_OPEN.clear()
    RING_OPEN.update(k for k in range(n) if op[k])
    print("ring points left open for the camera:", len(RING_OPEN))


def net_pts():
    out = []
    for ri, r in enumerate(roads):
        for k, (x, y) in enumerate(r["pts"]):
            if ri == 0 and (k in RING_OPEN or fg(x, y)):
                continue
            out.append((x, y, r["width"]))
    return out


def hash_pts(pts, cell=6.0):
    g = {}
    for p in pts:
        g.setdefault((int(p[0] // cell), int(p[1] // cell)), []).append(p)
    return g


def near_pts(g, x, y, cell=6.0):
    i, j = int(x // cell), int(y // cell)
    for a in (i - 1, i, i + 1):
        for b in (j - 1, j, j + 1):
            yield from g.get((a, b), ())


def first_hit(path, g, own_w):
    """Index of the first sample (after leaving the door) that touches an existing road -> join there (clean T)."""
    for k, (x, y) in enumerate(path):
        if k < 2:
            continue
        hits = [(math.hypot(px - x, py - y), px, py) for px, py, pw in near_pts(g, x, y) if math.hypot(px - x, py - y) < pw / 2 + own_w / 2 - 0.5]
        if hits:
            return k, min(hits)[1:]
    return None


def straight_link(d, front, label, max_len=70.0, max_ang=65.0, allow_water=False):
    """Best straight road from door d to the existing network: short, close to the facade normal,
    not through buildings, on land (unless allow_water), trimmed at the first road it meets."""
    pts = net_pts()
    g = hash_pts(pts)
    best = None
    cands = sorted(pts, key=lambda p: math.hypot(p[0] - d[0], p[1] - d[1]))[:900:3]
    for px, py, pw in cands:
        L = math.hypot(px - d[0], py - d[1])
        if L > max_len or (best and L > best[0]):
            break
        if L < pw / 2 + 3.0:
            return "touching"
        ux, uy = (px - d[0]) / L, (py - d[1]) / L
        ang = math.degrees(math.acos(max(-1.0, min(1.0, ux * front[0] + uy * front[1]))))
        if ang > max_ang:
            continue
        path = line(d, (px, py))
        cut = first_hit(path, g, 4.0)
        if cut is not None:   # stop at the first road met and finish ON its centre line (a real junction, no gap)
            path = path[:cut[0]] + [cut[1]]
        if len(path) < 2:
            return "touching"
        side = sum(1 for x, y in path[1:-1] if any(math.hypot(qx - x, qy - y) < qw / 2 + 4.5 for qx, qy, qw in near_pts(g, x, y)))
        if path[1:-1] and side > 0.35 * len(path[1:-1]):
            continue
        wf = wet_frac(path)
        if wf > 0 and not allow_water:
            continue
        if too_steep(path):
            continue
        if blocked(path, skip=(label,)):
            continue
        score = math.hypot(path[-1][0] - d[0], path[-1][1] - d[1]) * (1 + ang / 90.0) + wf * 40
        if best is None or score < best[0]:
            best = (score, path)
    return best[1] if best else None


mark_ring_open()

# spurs: nearest-to-ring buildings first so later spurs can T into earlier ones (a tree, not a tangle)
def ring_dist(b):
    return min(math.hypot(b["door"][0] - x, b["door"][1] - y) for x, y in ring[::3])


for b in sorted(blds, key=ring_dist):
    d = b["door"]
    c = (sum(p[0] for p in b["pts"]) / len(b["pts"]), sum(p[1] for p in b["pts"]) / len(b["pts"]))
    fx, fy = d[0] - c[0], d[1] - c[1]
    fl = math.hypot(fx, fy) or 1
    front = (fx / fl, fy / fl)
    path = straight_link(d, front, b["label"])
    if path is None:
        # one corner: walk straight out of the door 6-14 m, then straight to the network
        for out in (6.0, 10.0, 14.0):
            wp = (d[0] + front[0] * out, d[1] + front[1] * out)
            leg1 = line(d, wp)
            if blocked(leg1 + [wp], skip=(b["label"],)) or wet_frac(leg1) > 0 or too_steep(leg1):
                continue
            leg2 = straight_link(wp, front, b["label"], max_ang=100.0)
            if leg2 == "touching":
                path = leg1
                break
            if leg2:
                path = leg1 + leg2[1:]
                break
    if path is None:
        # one corner round an obstacle: straight to a free waypoint 8-30 m away (any side), then straight on
        for rad in (8.0, 14.0, 20.0, 30.0):
            for ak in range(16):
                ang = 2 * math.pi * ak / 16
                wp = (d[0] + math.cos(ang) * rad, d[1] + math.sin(ang) * rad)
                if any(inside(o["pts"], wp[0], wp[1], grow=3.0) for o in blds):
                    continue
                leg1 = line(d, wp)
                if wet_frac(leg1) > 0 or too_steep(leg1) or blocked(leg1 + [wp], skip=(b["label"],)):
                    continue
                leg2 = straight_link(wp, (math.cos(ang), math.sin(ang)), b["label"], max_ang=110.0)
                if leg2 == "touching":
                    path = leg1
                elif leg2:
                    path = leg1 + leg2[1:]
                if path:
                    break
            if path:
                break
    if path is None:
        # narrow alley between buildings: out of the door, turn 90 degrees along the alley, then straight to the network
        perp = (-front[1], front[0])
        for out in (2.5, 4.0):
            for sd in (1, -1):
                for run in (6.0, 10.0, 15.0, 20.0, 28.0):
                    w1 = (d[0] + front[0] * out, d[1] + front[1] * out)
                    w2 = (w1[0] + perp[0] * sd * run, w1[1] + perp[1] * sd * run)
                    legs = line(d, w1) + line(w1, w2)[1:]
                    if wet_frac(legs) > 0 or too_steep(legs) or blocked(legs + [w2], skip=(b["label"],)):
                        continue
                    leg3 = straight_link(w2, (perp[0] * sd, perp[1] * sd), b["label"], max_ang=120.0)
                    if leg3 == "touching":
                        path = legs
                    elif leg3:
                        path = legs + leg3[1:]
                    if path:
                        break
                if path:
                    break
            if path:
                break
    if path is None:
        path = straight_link(d, front, b["label"], max_len=60.0, max_ang=180.0)
    if path == "touching":
        continue
    if path is None:
        continue
    roads.append({"kind": "spur", "width": 4.0, "pts": path, "from": b["label"]})

unconnected = [b for b in blds if b["label"] not in {r.get("from") for r in roads}]
terr = 0
for b in unconnected:
    d = b["door"]
    others = sorted((o for o in blds if o is not b), key=lambda o: math.hypot(o["door"][0] - d[0], o["door"][1] - d[1]))
    for o in others[:6]:
        e = o["door"]
        L = math.hypot(e[0] - d[0], e[1] - d[1])
        if L > 45:
            break
        path = line(d, e)
        if wet_frac(path) > 0 or too_steep(path) or blocked(path, skip=(b["label"], o["label"])):
            continue
        roads.append({"kind": "spur", "width": 4.0, "pts": path, "from": b["label"], "terrace": True})
        terr += 1
        break
    else:
        print("STILL unconnected (terrace with no level neighbour)", b["label"])
print("terrace street links", terr)

# lanes: a few straight door-to-door links (MST, 6-30 m) only where they add a real shortcut:
# on land, not through buildings, not parallel/duplicate to an existing road
doors = [(b["door"][0], b["door"][1], b["label"]) for b in blds]
n = len(doors)
inT = [False] * n
best = [(INF, -1)] * n
best[0] = (0, -1)
edges = []
for _ in range(n):
    u = min((k for k in range(n) if not inT[k]), key=lambda k: best[k][0])
    inT[u] = True
    if best[u][1] >= 0:
        edges.append((best[u][1], u, best[u][0]))
    for v in range(n):
        if not inT[v]:
            dd = math.hypot(doors[u][0] - doors[v][0], doors[u][1] - doors[v][1])
            if dd < best[v][0]:
                best[v] = (dd, u)
lanes = 0
for a, b, L in (edges if "--lanes" in sys.argv else []):
    if L > 30 or L < 6:
        continue
    path = line(doors[a][:2], doors[b][:2])
    if wet_frac(path) > 0 or blocked(path, skip=(doors[a][2], doors[b][2])):
        continue
    g = hash_pts(net_pts())
    inner = path[2:-2]
    near = sum(1 for x, y in inner if any(math.hypot(px - x, py - y) < pw / 2 + 3.0 for px, py, pw in near_pts(g, x, y)))
    if inner and near > len(inner) * 0.25:      # runs along / over a road that is already there
        continue
    roads.append({"kind": "lane", "width": 3.5, "pts": path})
    lanes += 1

json.dump({"roads": roads, "lake_centre": [cx, cy]}, open(sys.argv[2], "w", encoding="utf-8"))
print("ring pts", len(ring), "spurs", sum(1 for r in roads if r["kind"] == "spur"), "lanes", lanes,
      "total length m", round(sum(len(r["pts"]) * 2 for r in roads)))
