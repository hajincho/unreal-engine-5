"""Draw the top-view map (SVG) from Saved/map_data.json written by Scripts/Unreal/ck_mapdata.py.
usage: python make_map.py <map_data.json> <out.svg> [road_plan.json]
With a road plan the planned roads are drawn (ochre) and free building lots next to the roads are marked as red boxes.
Orientation: up = +X (the reference camera looks up the map), right = +Y. Units: metres.
Houses/buildings green, roads (bridge, stairs, plaza, arcades) ochre.
"""
import json
import math
import re
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
out = sys.argv[2]
plan = json.load(open(sys.argv[3], encoding="utf-8")) if len(sys.argv) > 3 else None
S = 2.4                      # px per metre
xs, ys, step = data["xs"], data["ys"], data["step"]
X0, X1, Y0, Y1 = xs[0] - step / 2, xs[-1] + step / 2, ys[0] - step / 2, ys[-1] + step / 2
PAD_L, PAD_T, LEG_W = 60, 92, 360
W = int((Y1 - Y0) * S) + PAD_L + 30 + LEG_W
H = int((X1 - X0) * S) + PAD_T + 60


def px(x, y):
    """world metres -> svg px (up = +X, right = +Y)"""
    return PAD_L + (y - Y0) * S, PAD_T + (X1 - x) * S


def lake(z):
    t = max(0.0, min(1.0, -z / 18.0))
    return "rgb(%d,%d,%d)" % (120 - 90 * t, 200 - 110 * t, 215 - 60 * t)


def land(z, base):
    k = max(0.0, min(1.0, z / 40.0))
    r, g, b = base
    return "rgb(%d,%d,%d)" % (r + (255 - r) * k * 0.35, g + (255 - g) * k * 0.35, b + (255 - b) * k * 0.35)


COL = {"ground": (92, 84, 74), "terrace": (176, 166, 148), "rock": (120, 116, 110), "wall": (214, 206, 190),
       "crystal": (196, 176, 232), "building": (70, 160, 80), "road": (200, 150, 62), "other": (150, 150, 150)}

o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="Malgun Gothic, Segoe UI, sans-serif">' % (W, H),
     '<rect width="100%" height="100%" fill="#16181c"/>']
o.append('<text x="%d" y="34" fill="#eee" font-size="22" font-weight="700">Crystal Kingdom — 톱 뷰 지도 (CK_Main)</text>' % PAD_L)
o.append('<text x="%d" y="56" fill="#aaa" font-size="13">위 = +X (레퍼런스 카메라가 바라보는 방향), 오른쪽 = +Y, 단위 m, 격자 %g m 샘플</text>' % (PAD_L, step))

# ---- raster cells
cs = step * S
for i, x in enumerate(xs):
    for j, y in enumerate(ys):
        cat, z = data["cells"][i][j][:2]
        if cat == "void" or z is None:
            continue
        if cat in ("ground", "terrace", "rock") and z < -0.3:
            fill = lake(z)
        elif cat in ("building", "road"):
            fill = "rgb(%d,%d,%d)" % COL[cat]
        else:
            fill = land(z, COL.get(cat, COL["other"]))
        X, Y = px(x + step / 2, y - step / 2)
        o.append('<rect x="%.1f" y="%.1f" width="%.2f" height="%.2f" fill="%s"/>' % (X, Y, cs + 0.3, cs + 0.3, fill))

# ---- grid every 50 m
for gx in range(int(math.ceil(X0 / 50)) * 50, int(X1) + 1, 50):
    a, b = px(gx, Y0), px(gx, Y1)
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#ffffff" stroke-opacity="0.18" stroke-width="1"/>' % (a + b))
    o.append('<text x="%.1f" y="%.1f" fill="#bbb" font-size="11" text-anchor="end">X %d</text>' % (a[0] - 6, a[1] + 4, gx))
for gy in range(int(math.ceil(Y0 / 50)) * 50, int(Y1) + 1, 50):
    a, b = px(X0, gy), px(X1, gy)
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#ffffff" stroke-opacity="0.18" stroke-width="1"/>' % (a + b))
    o.append('<text x="%.1f" y="%.1f" fill="#bbb" font-size="11" text-anchor="middle">Y %d</text>' % (b[0], b[1] - 6, gy))


def short(label):
    s = re.sub(r"^(Fill_|Far_)?SM_(Bldg_|Arch_)?", "", label)
    return s


# ---- planned roads (ochre polylines, true width)
road_pts = []
if plan:
    for r in plan["roads"]:
        pts = " ".join("%.1f,%.1f" % px(x, y) for x, y in r["pts"])
        o.append('<polyline points="%s" fill="none" stroke="#7a5418" stroke-width="%.1f" stroke-linejoin="round" stroke-linecap="round"/>'
                 % (pts, r["width"] * S + 2.5))
        o.append('<polyline points="%s" fill="none" stroke="#c8963e" stroke-width="%.1f" stroke-linejoin="round" stroke-linecap="round"/>'
                 % (pts, r["width"] * S))
        road_pts += [(x, y, r["width"]) for x, y in r["pts"]]

# ---- free building lots (red boxes): flat, dry, unbuilt ground beside a road
lots = []
if plan:
    NX, NY = len(xs), len(ys)
    blocked = set()
    for s_ in data["shapes"]:
        xs_ = [q[0] for q in s_["pts"]]
        ys_ = [q[1] for q in s_["pts"]]
        for i in range(NX):
            if min(xs_) - 4 <= xs[i] <= max(xs_) + 4:
                for j in range(NY):
                    if min(ys_) - 4 <= ys[j] <= max(ys_) + 4:
                        blocked.add((i, j))
    def road_d(x, y):
        return min((math.hypot(x - a, y - b) - w / 2 for a, b, w in road_pts[::2]), default=1e9)
    LOT = 4                     # 4 x 4 cells = 12 m x 12 m
    cand = []
    for i in range(0, NX - LOT):
        for j in range(0, NY - LOT):
            ok = True
            zs = []
            for a in range(i, i + LOT):
                for b in range(j, j + LOT):
                    cell = data["cells"][a][b]
                    c, z = cell[0], cell[1]
                    gz = cell[2] if len(cell) > 2 and cell[2] is not None else z
                    # bare ground / terrace, or ground under small scatter crystals (< 6 m tall; cliffs are excluded)
                    usable = (c in ("ground", "terrace") and z is not None) or (c == "crystal" and gz is not None and z - gz < 6)
                    if not usable or gz is None or gz < 0.3 or (a, b) in blocked:
                        ok = False
                        break
                    zs.append(gz)
                if not ok:
                    break
            if not ok or max(zs) - min(zs) > 1.5:
                continue
            x = (xs[i] + xs[i + LOT - 1]) / 2
            y = (ys[j] + ys[j + LOT - 1]) / 2
            d = road_d(x, y)
            if 7.5 <= d <= 16:      # fronts a road, but the 12 m plot itself stays off the carriageway
                cand.append((d, x, y, sum(zs) / len(zs)))
    cand.sort()
    for d, x, y, z in cand:
        if all(abs(x - a) > 14 or abs(y - b) > 14 for a, b, _ in lots):
            lots.append((x, y, z))
    lots.sort(key=lambda t: (-t[0], t[1]))
    import os
    def nearest_road(x, y):
        return min(((a, b) for a, b, w in road_pts), key=lambda p: math.hypot(p[0] - x, p[1] - y))
    json.dump([{"id": "P%d" % (k + 1), "x": x, "y": y, "z": z, "road": nearest_road(x, y)} for k, (x, y, z) in enumerate(lots)],
              open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "lots.json"), "w", encoding="utf-8"))
    for k, (x, y, z) in enumerate(lots, 1):
        X, Y = px(x + 6, y - 6)
        o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#ff2a2a" fill-opacity="0.18" stroke="#ff3b3b" stroke-width="2"/>'
                 % (X, Y, 12 * S, 12 * S))
        cx_, cy_ = px(x, y)
        o.append('<text x="%.1f" y="%.1f" fill="#ff8080" font-size="10.5" font-weight="700" text-anchor="middle" '
                 'stroke="#000" stroke-width="2.4" paint-order="stroke">P%d</text>' % (cx_, cy_ + 4, k))

# ---- shapes: roads under buildings, numbered
roads = [s for s in data["shapes"] if s["kind"] == "road"]
blds = [s for s in data["shapes"] if s["kind"] == "building"]
roads.sort(key=lambda s: (-s["c"][0], s["c"][1]))
blds.sort(key=lambda s: (-s["c"][0], s["c"][1]))
legend = []
for prefix, items, col, stroke in (("R", roads, "#c8963e", "#ffd590"), ("B", blds, "#46a050", "#b8f5b0")):
    for k, s in enumerate(items, 1):
        pts = " ".join("%.1f,%.1f" % px(x, y) for x, y in s["pts"])
        o.append('<polygon points="%s" fill="%s" fill-opacity="0.92" stroke="%s" stroke-width="1.4"/>' % (pts, col, stroke))
        cx, cy = px(*s["c"])
        tag = "%s%d" % (prefix, k)
        o.append('<text x="%.1f" y="%.1f" fill="#fff" font-size="11" font-weight="700" text-anchor="middle" '
                 'stroke="#000" stroke-width="2.6" paint-order="stroke">%s</text>' % (cx, cy + 4, tag))
        legend.append((tag, short(s["label"]), s["c"], s["z"]))

# ---- cameras
for c in data["cams"]:
    cx, cy = px(c["x"], c["y"])
    ref = c["label"] == "CAM_Reference"
    a = math.radians(c["yaw"])
    for d in (-43, 43):
        ad = a + math.radians(d)
        ex, ey = px(c["x"] + math.cos(ad) * (120 if ref else 25), c["y"] + math.sin(ad) * (120 if ref else 25))
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s" stroke-dasharray="6 4"/>'
                 % (cx, cy, ex, ey, "#ff5a5a" if ref else "#ff9a9a", 2 if ref else 1))
    o.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="#ff5a5a" stroke="#fff" stroke-width="1.5"/>' % (cx, cy, 6 if ref else 4))
    if ref:
        o.append('<text x="%.1f" y="%.1f" fill="#ff8a8a" font-size="12" font-weight="700">레퍼런스 카메라</text>' % (cx + 10, cy + 16))

# ---- legend panel
lx = W - LEG_W + 10
ly = PAD_T
o.append('<text x="%d" y="%d" fill="#eee" font-size="15" font-weight="700">범례</text>' % (lx, ly))
sw = [("건물·집", "#46a050"), ("도로 (계획 도로망 + 다리·계단·광장)", "#c8963e"), ("건축 가능 부지 12×12 m", "#ff3b3b"), ("단구 윗면", "rgb(176,166,148)"),
      ("동굴 바닥", "rgb(92,84,74)"), ("석조 옹벽", "rgb(214,206,190)"), ("수정", "rgb(196,176,232)"), ("암석", "rgb(120,116,110)"),
      ("호수 (진할수록 깊음)", "rgb(60,120,170)")]
for k, (name, col) in enumerate(sw):
    y = ly + 16 + k * 20
    o.append('<rect x="%d" y="%d" width="16" height="14" fill="%s" stroke="#888"/>' % (lx, y, col))
    o.append('<text x="%d" y="%d" fill="#ddd" font-size="12">%s</text>' % (lx + 24, y + 12, name))
ly += 16 + len(sw) * 20 + 18
o.append('<text x="%d" y="%d" fill="#eee" font-size="15" font-weight="700">번호 목록 (X, Y, 높이 m)</text>' % (lx, ly))
for k, (tag, name, c, z) in enumerate(legend):
    y = ly + 18 + k * 15.5
    col = "#ffd590" if tag.startswith("R") else "#b8f5b0"
    o.append('<text x="%d" y="%.1f" fill="%s" font-size="11.5"><tspan font-weight="700">%s</tspan> %s  (%.0f, %.0f, %.0f)</text>'
             % (lx, y, col, tag, name, c[0], c[1], z))
if lots:
    ly2 = ly + 18 + len(legend) * 15.5 + 14
    o.append('<text x="%d" y="%.1f" fill="#ff9a9a" font-size="13" font-weight="700">빈 부지 P (X, Y, 지면 높이 m)</text>' % (lx, ly2))
    for k, (x, y, z) in enumerate(lots, 1):
        col, row = divmod(k - 1, 26)
        o.append('<text x="%.1f" y="%.1f" fill="#ff9a9a" font-size="11">P%d (%.0f, %.0f, %.0f)</text>'
                 % (lx + col * 115, ly2 + 16 + row * 14.5, k, x, y, z))
o.append("</svg>")
open(out, "w", encoding="utf-8").write("\n".join(o))
print("map", out, "roads", len(roads), "buildings", len(blds))
