"""Procedural, seamlessly tiling textures for Crystal Kingdom (numpy, saved as PNG).

Normal maps are written in OpenGL convention (UE import sets flip_green_channel).
run: blender --background --factory-startup --python gen_textures.py
"""
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ck_common import TEXOUT  # noqa: E402

RNG = np.random.default_rng(1337)


def fft_noise(n, beta, rng=RNG, aniso=(1.0, 1.0)):
    w = rng.standard_normal((n, n))
    F = np.fft.fft2(w)
    fy = np.fft.fftfreq(n)[:, None] * aniso[1]
    fx = np.fft.fftfreq(n)[None, :] * aniso[0]
    k = np.sqrt(fx * fx + fy * fy)
    k[0, 0] = 1.0
    F *= 1.0 / (k ** (beta * 0.5))
    F[0, 0] = 0
    h = np.real(np.fft.ifft2(F))
    h -= h.min()
    h /= h.max()
    return h


def worley(n, cells, rng=RNG):
    """Tileable Worley: returns F1, F2 distances (in cell units) and cell id random."""
    pts = rng.random((cells, cells, 2))
    ids = rng.random((cells, cells))
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    gx = xx / n * cells
    gy = yy / n * cells
    cx = np.floor(gx).astype(int)
    cy = np.floor(gy).astype(int)
    f1 = np.full((n, n), 9.0, np.float32)
    f2 = np.full((n, n), 9.0, np.float32)
    idv = np.zeros((n, n), np.float32)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            ncx = cx + ox
            ncy = cy + oy
            wx = ncx % cells
            wy = ncy % cells
            px = ncx + pts[wy, wx, 0]
            py = ncy + pts[wy, wx, 1]
            d = np.sqrt((px - gx) ** 2 + (py - gy) ** 2)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            idv = np.where(closer, ids[wy, wx], idv)
            f1 = np.where(closer, d, f1)
    return f1, f2, idv


def normal_from_height(h, strength):
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * strength
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * strength
    nz = np.ones_like(h)
    l = np.sqrt(dx * dx + dy * dy + nz * nz)
    return np.stack([-dx / l, -dy / l, nz / l], axis=-1) * 0.5 + 0.5


def save_png(name, rgb):
    rgb = np.clip(rgb, 0, 1).astype(np.float32)
    n = rgb.shape[0]
    rgba = np.concatenate([rgb, np.ones((n, n, 1), np.float32)], axis=-1)
    img = bpy.data.images.new(name, n, n, alpha=False, float_buffer=False)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(rgba.ravel())
    os.makedirs(TEXOUT, exist_ok=True)
    img.filepath_raw = os.path.join(TEXOUT, name + ".png")
    img.file_format = "PNG"
    img.save()
    print("saved", img.filepath_raw)


def norm(a):
    a = a - a.min()
    return a / max(a.max(), 1e-6)


def rock(n=2048):
    big = fft_noise(n, 2.2)
    mid = fft_noise(n, 1.6)
    f1, f2, cid = worley(n, 10)
    edges = np.clip((f2 - f1) * 4.0, 0, 1)  # 0 at cell borders -> cracks
    strata = 0.5 + 0.5 * np.sin(np.mgrid[0:n, 0:n][0] / n * 2 * np.pi * 9 + big * 6.0)
    h = 0.45 * big + 0.25 * mid + 0.18 * edges + 0.12 * strata
    save_png("T_Rock_N", normal_from_height(norm(h), 18.0))
    cavity = 1.0 - np.clip(1.0 - edges, 0, 1) ** 3
    save_png("T_Rock_M", np.stack([norm(h), cavity, norm(cid * 0.5 + big * 0.5)], -1))


def crystal(n=2048):
    f1, f2, _ = worley(n, 7)
    cracks = np.clip(1.0 - (f2 - f1) * 18.0, 0, 1) ** 2  # thin fracture lines
    f1b, f2b, _ = worley(n, 19)
    cracks2 = np.clip(1.0 - (f2b - f1b) * 30.0, 0, 1) ** 3 * 0.5
    cloud = fft_noise(n, 2.6)
    streak = fft_noise(n, 1.8, aniso=(1.0, 0.08))  # stretched along V (growth axis)
    save_png("T_Crystal_M", np.stack([np.clip(cracks + cracks2, 0, 1), cloud, streak], -1))
    hh = 0.6 * fft_noise(n, 2.8) + 0.4 * streak - 0.25 * np.clip(cracks + cracks2, 0, 1)
    save_png("T_Crystal_N", normal_from_height(norm(hh), 6.0))


def water(n=1024):
    a = fft_noise(n, 3.2)
    b = fft_noise(n, 2.4)
    save_png("T_Water_N", normal_from_height(norm(0.7 * a + 0.3 * b), 10.0))


def stone(n=2048):
    """Masonry blocks: 1 texture tile = 2 m x 2 m, 4 courses of 0.5 m."""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    u = xx / n * 2.0  # meters
    v = yy / n * 2.0
    rows = 4
    row = np.floor(v / (2.0 / rows)).astype(int)
    rng = np.random.default_rng(7)
    h = np.zeros((n, n), np.float32)
    blockid = np.zeros((n, n), np.float32)
    mortar = np.zeros((n, n), np.float32)
    for r in range(rows):
        # random block lengths that tile exactly over 2 m
        lens = []
        while sum(lens) < 2.0 - 0.45:
            lens.append(rng.uniform(0.45, 0.9))
        lens.append(2.0 - sum(lens))
        edges = np.cumsum([0] + lens)
        off = rng.uniform(0, 2.0)
        m = row == r
        uu = (u + off) % 2.0
        k = np.searchsorted(edges, uu, side="right") - 1
        k = np.clip(k, 0, len(lens) - 1)
        e0 = edges[k]
        e1 = edges[k + 1]
        v0 = r * (2.0 / rows)
        v1 = v0 + 2.0 / rows
        dist = np.minimum.reduce([uu - e0, e1 - uu, v - v0, v1 - v])
        bevel = np.clip(dist / 0.035, 0, 1)
        bh = np.sqrt(bevel)
        ids = rng.random(len(lens))
        h = np.where(m, bh, h)
        blockid = np.where(m, ids[k], blockid)
        mortar = np.where(m, 1.0 - np.clip(dist / 0.012, 0, 1), mortar)
    grain = fft_noise(n, 1.9)
    chips = np.clip((fft_noise(n, 2.4) - 0.72) * 6, 0, 1)
    height = h * 0.8 + grain * 0.15 - chips * 0.25
    save_png("T_Stone_N", normal_from_height(norm(height), 14.0))
    grime = fft_noise(n, 2.2)
    save_png("T_Stone_M", np.stack([np.clip(mortar + chips * 0.5, 0, 1), blockid, grime], -1))


if __name__ == "__main__":
    rock()
    crystal()
    water()
    stone()
