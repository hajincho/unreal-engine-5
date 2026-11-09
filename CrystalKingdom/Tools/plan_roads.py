"""Plan the road network from Saved/map_data.json -> Saved/road_plan.json (built by ck_build_level.py stage=roads).
  1. ring road (6 m) round the lake, ~8 m outside the outer shoreline, smoothed into organic curves
  2. a spur (4 m) from every building's front door to the ring, routed round other buildings
  3. lanes (3.5 m) between neighbouring doors (minimum spanning tree, < 38 m) so the quarters interconnect
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


def blocked(path, skip=()):
    for (x, y) in path[1:-1]:
        for b in blds:
            if b["label"] in skip:
                continue
            if inside(b["pts"], x, y):
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
moved = 0
for k, (x, y) in enumerate(ring):
    if any(inside(b["pts"], x, y, grow=4.0) for b in blds):
        dx, dy = cx - x, cy - y
        dl = math.hypot(dx, dy) or 1
        for s_ in range(1, 40):
            nx_, ny_ = x + dx / dl * s_, y + dy / dl * s_
            if not any(inside(b["pts"], nx_, ny_, grow=4.0) for b in blds):
                ring[k] = (nx_, ny_)
                moved += 1
                break
ring = catmull(smooth_closed(ring[::2], w=2, it=2), 2.0, closed=True)
print("ring points steered round buildings:", moved)
roads = [{"kind": "ring", "width": 6.0, "pts": ring}]
for b in blds:
    d = b["door"]
    c = b["c"]
    fx, fy = d[0] - c[0], d[1] - c[1]
    fl = math.hypot(fx, fy) or 1
    fx, fy = fx / fl, fy / fl
    cand = sorted(range(len(ring)), key=lambda k: math.hypot(ring[k][0] - d[0], ring[k][1] - d[1]))
    done = False
    for k in cand[:60:3]:
        p1 = ring[k]
        L = math.hypot(p1[0] - d[0], p1[1] - d[1])
        if L < 2.5:
            done = True
            break
        ctrl = (d[0] + fx * L * 0.5, d[1] + fy * L * 0.5)       # leave the door straight out, then curve to the ring
        path = bezier(d, ctrl, p1)
        if not blocked(path, skip=(b["label"],)):
            roads.append({"kind": "spur", "width": 4.0, "pts": path, "from": b["label"]})
            done = True
            break
    if not done:
        print("no clear spur for", b["label"])

# lanes: MST over doors (Prim), keep edges < 38 m that do not cut through a building
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
for a, b, L in edges:
    if L > 38 or L < 4:
        continue
    pa, pb = doors[a][:2], doors[b][:2]
    mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
    nx_, ny_ = -(pb[1] - pa[1]) / L, (pb[0] - pa[0]) / L
    bend = 0.12 * L * (1 if (a + b) % 2 else -1)              # gentle organic bow
    path = bezier(pa, (mx + nx_ * bend, my + ny_ * bend), pb)
    if not blocked(path, skip=(doors[a][2], doors[b][2])):
        roads.append({"kind": "lane", "width": 3.5, "pts": path})
        lanes += 1

# fallback: buildings with no clear way to the ring join the nearest point of any road already planned
connected = {r.get("from") for r in roads if r["kind"] == "spur"}
for r in roads:
    if r["kind"] == "lane":
        pass
lane_ends = set()
for r in roads:
    if r["kind"] == "lane":
        for b in blds:
            for e in (r["pts"][0], r["pts"][-1]):
                if math.hypot(e[0] - b["door"][0], e[1] - b["door"][1]) < 0.5:
                    lane_ends.add(b["label"])
missing = [b for b in blds if b["label"] not in connected and b["label"] not in lane_ends]
for b in missing:
    d = b["door"]
    pool = [p for r in roads for p in r["pts"]]
    pool.sort(key=lambda p: math.hypot(p[0] - d[0], p[1] - d[1]))
    for p1 in pool[:1500:3]:
        L = math.hypot(p1[0] - d[0], p1[1] - d[1])
        c = b["c"]
        fx, fy = d[0] - c[0], d[1] - c[1]
        fl = math.hypot(fx, fy) or 1
        path = bezier(d, (d[0] + fx / fl * L * 0.4, d[1] + fy / fl * L * 0.4), p1)
        if L > 2.5 and not blocked(path, skip=(b["label"],)):
            roads.append({"kind": "spur", "width": 4.0, "pts": path, "from": b["label"]})
            print("fallback link", b["label"], round(L), "m")
            break
    else:
        # two legs round the obstacle: door -> waypoint (10-35 m away) -> nearest road point
        found = False
        for rad in (8, 12, 18, 25, 35, 50):
            for ak in range(24):
                ang = 2 * math.pi * ak / 24
                wp = (d[0] + math.cos(ang) * rad, d[1] + math.sin(ang) * rad)
                if any(inside(o["pts"], wp[0], wp[1], grow=3.0) for o in blds):
                    continue
                leg1 = bezier(d, ((d[0] + wp[0]) / 2, (d[1] + wp[1]) / 2), wp)
                if blocked(leg1 + [wp], skip=(b["label"],)):
                    continue
                pool2 = sorted(pool, key=lambda p: math.hypot(p[0] - wp[0], p[1] - wp[1]))
                for p1 in pool2[:300:5]:
                    leg2 = bezier(wp, ((wp[0] + p1[0]) / 2, (wp[1] + p1[1]) / 2), p1)
                    if not blocked(leg2):
                        roads.append({"kind": "spur", "width": 4.0, "pts": leg1 + leg2[1:], "from": b["label"]})
                        print("detour link", b["label"], "via", [round(v) for v in wp])
                        found = True
                        break
                if found:
                    break
            if found:
                break
        if not found:
            print("STILL unconnected", b["label"])

json.dump({"roads": roads, "lake_centre": [cx, cy]}, open(sys.argv[2], "w", encoding="utf-8"))
print("ring pts", len(ring), "spurs", sum(1 for r in roads if r["kind"] == "spur"), "lanes", lanes,
      "total length m", round(sum(len(r["pts"]) * 2 for r in roads)))
