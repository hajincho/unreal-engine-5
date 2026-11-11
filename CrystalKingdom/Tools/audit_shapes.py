"""Offline overlap audit of building footprints in Saved/map_data.json (oriented rectangles, SAT)."""
import json
import sys


def axes(p):
    out = []
    for k in range(len(p)):
        x0, y0 = p[k]
        x1, y1 = p[(k + 1) % len(p)]
        out.append((-(y1 - y0), x1 - x0))
    return out


def overlap(a, b, shrink=0.5):
    for ax, ay in axes(a) + axes(b):
        L = (ax * ax + ay * ay) ** 0.5 or 1
        ax, ay = ax / L, ay / L
        pa = [x * ax + y * ay for x, y in a]
        pb = [x * ax + y * ay for x, y in b]
        if max(pa) - shrink <= min(pb) + shrink or max(pb) - shrink <= min(pa) + shrink:
            return False
    return True


if __name__ == "__main__":
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    B = [s for s in d["shapes"] if s["kind"] == "building"]
    for i in range(len(B)):
        for j in range(i + 1, len(B)):
            if overlap(B[i]["pts"], B[j]["pts"]):
                print("OVERLAP", B[i]["label"], B[i]["c"], "<->", B[j]["label"], B[j]["c"])
