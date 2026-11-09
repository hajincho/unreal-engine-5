"""Summarise an Unreal CSV profiler capture: python csvstats.py <file.csv> [label] [skip_frames]"""
import csv
import statistics
import sys

path = sys.argv[1]
label = sys.argv[2] if len(sys.argv) > 2 else path
skip = int(sys.argv[3]) if len(sys.argv) > 3 else 120
with open(path, newline="", encoding="utf-8", errors="replace") as f:
    rows = list(csv.reader(f))
head = rows[0]
fi = head.index("FrameTime") if "FrameTime" in head else -1
data = [r for r in rows[1:] if fi >= 0 and len(r) > fi and r[fi].replace(".", "", 1).isdigit()]


def col(*names):
    for n in names:
        if n in head:
            i = head.index(n)
            vals = []
            for r in data[skip:]:
                try:
                    vals.append(float(r[i]))
                except (ValueError, IndexError):
                    pass
            return vals
    return []


ft = col("FrameTime")
gpu = col("GPUTime", "GPU/Total")
gt = col("GameThreadTime")
rt = col("RenderThreadTime")
if not ft:
    print("no FrameTime column; columns:", head[:20])
    sys.exit(1)
s = sorted(ft)
p95 = s[int(len(s) * 0.95)]
print("%s: frames=%d avg_frame=%.2f ms (%.1f fps) median=%.2f ms p95=%.2f ms | gpu=%.2f ms game=%.2f ms render=%.2f ms" % (
    label, len(ft), statistics.mean(ft), 1000.0 / statistics.mean(ft), statistics.median(ft), p95,
    statistics.mean(gpu) if gpu else -1, statistics.mean(gt) if gt else -1, statistics.mean(rt) if rt else -1))
