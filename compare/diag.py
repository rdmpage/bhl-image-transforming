#!/usr/bin/env python3
"""Routing diagnostics per input image, with truth labels.

colour_std : sqrt(var(rg)+var(yb)) on opponent channels = cast-INVARIANT spread
             of colour (Hasler-Susstrunk). High only for genuine multi-hue colour.
cast       : sqrt(mean(rg)^2+mean(yb)^2) = strength of the dominant tint (sepia).
blur_mid   : midtone mass after strong blur (halftone dots merge into greytone).
"""
import glob, os, numpy as np
from PIL import Image, ImageFilter

INPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input")
TRUTH = {
    "16281064": "text", "46027136": "text", "46027137": "text",
    "6554719": "text", "text_31940305": "text",
    "58740584": "grey", "63294239": "grey", "photo_grapsoid": "grey",
    "63511665": "colour", "plate_bird": "colour", "34921664": "colour",
}


def cstd(im):
    rgb = np.asarray(im, dtype=np.float32)
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    rg, yb = R - G, 0.5 * (R + G) - B
    return float(np.sqrt(rg.var() + yb.var())), float(np.hypot(rg.mean(), yb.mean()))


def diag(path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((500, 500))
    colour_std, cast = cstd(im)
    # denoised: average out JPEG chroma noise; real colour patches survive
    cstd_lo, _ = cstd(im.resize((64, 64), Image.BOX))

    small = im.convert("L").resize((128, 128)).filter(ImageFilter.GaussianBlur(1.2))
    g = np.asarray(small, dtype=np.float32)
    lo, hi = np.percentile(g, 2), np.percentile(g, 98)
    g = np.clip((g - lo) / max(1.0, hi - lo), 0, 1)
    blur_mid = float(((g > 0.25) & (g < 0.75)).mean())
    return colour_std, cstd_lo, cast, blur_mid


paths = sorted(glob.glob(os.path.join(INPUT, "*")))
rows = []
for p in paths:
    if not p.lower().endswith((".jpg", ".jpeg", ".png")):
        continue
    name = os.path.splitext(os.path.basename(p))[0]
    rows.append((TRUTH.get(name, "?"), name, *diag(p)))

print(f"{'truth':7} {'page':16} {'cstd':>6} {'cstd_lo':>8} {'cast':>6} {'blur_mid':>8}")
for t, n, cs, cl, ca, bm in sorted(rows):
    print(f"{t:7} {n:16} {cs:6.2f} {cl:8.2f} {ca:6.1f} {bm:8.3f}")
