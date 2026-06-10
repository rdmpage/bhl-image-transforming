#!/usr/bin/env python3
"""
Build a threshold/routing comparison sheet for every image in compare/input/.

For each page it computes routing signals (in CIELAB, the right space for this),
runs the candidate transforms (Otsu / adaptive binarize, de-sepia, greyscale),
records jbig2 payload sizes, and writes compare/out/index.html.

Run with the sibling venv that has PIL+numpy:
  ~/Development/bhl-all-the-images/.venv/bin/python compare/build.py

Drop more images into compare/input/ and re-run to extend the comparison.
"""
import glob
import os
import subprocess
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(HERE, "input")
OUT = os.path.join(HERE, "out")
PREVW = 560                      # preview width (px) in the HTML

# routing thresholds (provisional — tune as more examples arrive)
CHROMA_C = 8.0                   # residual chroma above which a pixel is "chromatic"
COLOUR_FRAC = 0.06               # min chromatic fraction to consider "has colour"
HUE_CONC_MAX = 0.90              # below this hue-concentration => polychrome
MIDTONE_MIN = 0.30               # above this => continuous-tone (don't binarize)


def sh(*args):
    subprocess.run(args, check=False, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


def kb(path):
    try:
        return (os.path.getsize(path) + 512) // 1024
    except OSError:
        return 0


def jbig2_kb(bilevel_png):
    """jbig2 generic-coder payload size (KB) for a bilevel PNG."""
    for f in glob.glob(os.path.join(OUT, "output.*")):
        os.remove(f)
    cwd = os.getcwd()
    os.chdir(OUT)
    try:
        with open(os.devnull, "w") as dn:
            r = subprocess.run(["jbig2", "-p", bilevel_png],
                               stdout=subprocess.PIPE, stderr=dn)
        n = len(r.stdout)
        for f in glob.glob("output.*"):
            n += os.path.getsize(f)
            os.remove(f)
    finally:
        os.chdir(cwd)
    return (n + 512) // 1024


def metrics(path):
    """Routing signals in CIELAB + tone, computed on a downscaled copy."""
    im = Image.open(path).convert("RGB")
    im.thumbnail((500, 500))
    rgb = np.asarray(im, dtype=np.float32)
    lab = np.asarray(im.convert("LAB"), dtype=np.float32)
    L, a, b = lab[..., 0], lab[..., 1] - 128.0, lab[..., 2] - 128.0

    # Remove the page's dominant colour cast (sepia/paper) before measuring
    # chroma, so a uniformly-tinted page collapses toward neutral and only
    # genuinely-coloured regions survive.
    ra, rb = a - np.median(a), b - np.median(b)
    chroma = np.hypot(ra, rb)
    chromatic = chroma > CHROMA_C
    chromatic_frac = float(chromatic.mean())

    # hue concentration of the (cast-removed) chromatic pixels: |mean unit
    # vector| in (0..1). ~1 => one residual hue; low => many hues (real colour)
    if chromatic.sum() > 50:
        ang = np.arctan2(rb[chromatic], ra[chromatic])
        R = float(np.hypot(np.cos(ang).mean(), np.sin(ang).mean()))
    else:
        R = 1.0

    # tone: contrast-stretch (robust percentiles) before measuring midtone mass,
    # so soft/low-contrast text scans still read as bimodal, not continuous-tone.
    lo, hi = np.percentile(L, 2), np.percentile(L, 98)
    gray = np.clip((L - lo) / max(1.0, hi - lo), 0, 1)
    midtone_frac = float(((gray > 0.25) & (gray < 0.75)).mean())

    # naive HSB saturation, kept only to show why it misleads
    mx = rgb.max(-1); mn = rgb.min(-1)
    naive_sat = float(np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0).mean())

    return dict(chroma_mean=float(chroma.mean()), chromatic_frac=chromatic_frac,
                hue_conc=R, midtone=midtone_frac, naive_sat=naive_sat)


def route(m):
    if m["chromatic_frac"] >= COLOUR_FRAC and m["hue_conc"] <= HUE_CONC_MAX:
        return "colour"
    if m["midtone"] >= MIDTONE_MIN:
        return "greyscale"
    return "text"


def process(path):
    name = os.path.splitext(os.path.basename(path))[0]
    W, H = Image.open(path).size
    p = lambda s: os.path.join(OUT, f"{name}_{s}")     # output path helper
    rel = lambda s: f"{name}_{s}"                       # html-relative path

    # central zoom crop (adapts to any page size)
    cw, ch = int(W * 0.5), int(H * 0.14)
    cx, cy = int(W * 0.25), int(H * 0.30)
    crop = f"{cw}x{ch}+{cx}+{cy}"
    win = max(15, int(W * 0.02))

    # previews + crop of original
    sh("magick", path, "-resize", f"{PREVW}x", p("orig_prev.png"))
    sh("magick", path, "-crop", crop, "+repage", p("orig_crop.png"))

    # binarizations (full-res bilevel for honest jbig2 size)
    sh("magick", path, "-colorspace", "Gray", "-auto-threshold", "OTSU",
       "-type", "bilevel", p("otsu.png"))
    sh("magick", path, "-colorspace", "Gray", "-lat", f"{win}x{win}-12%",
       "-type", "bilevel", p("lat.png"))
    for v in ("otsu", "lat"):
        sh("magick", p(f"{v}.png"), "-resize", f"{PREVW}x", p(f"{v}_prev.png"))
        sh("magick", p(f"{v}.png"), "-crop", crop, "+repage", p(f"{v}_crop.png"))

    # colour cleanup + greyscale paths
    sh("magick", path, "-negate", "-channel", "all", "-normalize", "-negate",
       "+channel", "-resize", f"{PREVW}x", p("desepia_prev.png"))
    sh("magick", path, "-colorspace", "Gray", "-normalize",
       "-resize", f"{PREVW}x", p("gray_prev.png"))

    m = metrics(path)
    return dict(name=name, dims=f"{W}×{H}", src_kb=kb(path), m=m, route=route(m),
                otsu_kb=jbig2_kb(p("otsu.png")), lat_kb=jbig2_kb(p("lat.png")),
                rel=rel)


def html(results):
    rows = []
    for r in results:
        m = r["m"]
        rows.append(
            f"<tr><td>{r['name']}</td><td>{r['dims']}</td>"
            f"<td>{m['naive_sat']:.3f}</td><td>{m['chroma_mean']:.1f}</td>"
            f"<td>{m['chromatic_frac']:.3f}</td><td>{m['hue_conc']:.2f}</td>"
            f"<td>{m['midtone']:.3f}</td><td><b>{r['route']}</b></td></tr>"
        )
    table = "\n".join(rows)

    sections = []
    for r in results:
        rel = r["rel"]
        sections.append(f"""
<h2>{r['name']} &nbsp;<small>{r['dims']} · route: <b>{r['route']}</b></small></h2>
<div class=row>
  <figure><figcaption>original ({r['src_kb']} KB jpg)</figcaption>
    <img src="{rel('orig_prev.png')}"><img class=crop src="{rel('orig_crop.png')}"></figure>
  <figure><figcaption>Otsu binarize — <b>{r['otsu_kb']} KB</b> jbig2</figcaption>
    <img src="{rel('otsu_prev.png')}"><img class=crop src="{rel('otsu_crop.png')}"></figure>
  <figure><figcaption>adaptive LAT — <b>{r['lat_kb']} KB</b> jbig2</figcaption>
    <img src="{rel('lat_prev.png')}"><img class=crop src="{rel('lat_crop.png')}"></figure>
  <figure><figcaption>de-sepia (colour)</figcaption><img src="{rel('desepia_prev.png')}"></figure>
  <figure><figcaption>greyscale + normalize</figcaption><img src="{rel('gray_prev.png')}"></figure>
</div>""")

    doc = f"""<!doctype html><meta charset=utf-8><title>BHL transform comparison</title>
<style>
body{{font:14px/1.45 -apple-system,sans-serif;margin:24px;max-width:1400px}}
h2{{margin-top:2em;border-bottom:1px solid #ccc}} small{{color:#666;font-weight:normal}}
.row{{display:flex;gap:12px;flex-wrap:wrap}} figure{{margin:0;width:{PREVW}px}}
img{{width:{PREVW}px;border:1px solid #bbb;display:block}} img.crop{{margin-top:6px}}
figcaption{{margin:2px 0;color:#333}}
table{{border-collapse:collapse;margin:1em 0}} td,th{{border:1px solid #ccc;padding:4px 9px;text-align:right}}
th:first-child,td:first-child,td:last-child{{text-align:left}}
.note{{background:#fffbe6;padding:10px 14px;border-left:4px solid #e6c200}}
</style>
<h1>BHL transform &amp; routing comparison</h1>
<p class=note><b>Routing signals (CIELAB).</b> <code>chromatic_frac</code> = share of
pixels with real chroma; <code>hue_conc</code> = how concentrated those hues are
(~1 = single cast like sepia, low = many hues = genuine colour);
<code>midtone</code> = continuous-tone mass (high = photo, don't binarize).
<code>naive_sat</code> is shown only to demonstrate it does <i>not</i> separate the
types. Route = colour if chromatic &amp; polychrome; else greyscale if mid-tonal;
else text.</p>
<table>
<tr><th>page</th><th>dims</th><th>naive_sat</th><th>chroma_mean</th>
<th>chromatic_frac</th><th>hue_conc</th><th>midtone</th><th>route</th></tr>
{table}
</table>
{''.join(sections)}"""
    with open(os.path.join(OUT, "index.html"), "w") as f:
        f.write(doc)


def main():
    os.makedirs(OUT, exist_ok=True)
    paths = sorted(p for p in glob.glob(os.path.join(INPUT, "*"))
                   if p.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff")))
    if not paths:
        print("no images in compare/input/")
        return
    results = []
    for path in paths:
        print("processing", os.path.basename(path))
        results.append(process(path))
    html(results)
    print(f"\nwrote {os.path.join(OUT, 'index.html')}  ({len(results)} pages)")
    print(f"{'page':22} {'chrom_frac':>10} {'hue_conc':>9} {'midtone':>8}  route")
    for r in results:
        m = r["m"]
        print(f"{r['name']:22} {m['chromatic_frac']:10.3f} {m['hue_conc']:9.2f} "
              f"{m['midtone']:8.3f}  {r['route']}")


if __name__ == "__main__":
    main()
