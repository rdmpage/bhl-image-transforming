#!/usr/bin/env python3
"""
Routed BHL page transform, end to end, for every image in compare/input/.

Per page: run jbig2 -s -S -p to get the residual picture layer, measure routing
signals, pick a route, and emit the route-appropriate final:
  text      -> Otsu binarize whole page  (tiny B&W, jbig2)
  colour    -> the de-sepia'd residual layer as-is (picture on white)
  greyscale -> the residual, desaturated + contrast-normalised
Writes compare/work/* and compare/pipeline.html.

Run: ~/Development/bhl-all-the-images/.venv/bin/python compare/pipeline.py
"""
import glob, os, shutil, subprocess
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT, WORK = os.path.join(HERE, "input"), os.path.join(HERE, "work")
PREVW = 520
INK_T = 0.13        # residual ink below this => pure text/line-art (binarize)
INK_HIGH = 0.90     # residual ~all ink => jbig2 didn't segment; use page fallback
CSTD_T = 14.0       # picture colourfulness above this => colour (else B&W routes).
                    # Below this catches tinted B&W photos (warm cast, not colour).
WHOLE_CSTD_T = 14.0 # fallback: whole-page colourfulness above this => colour
SOLID_T = 0.40      # residual fill density above this => continuous-tone photo
CAST_STRONG = 35.0  # whole-page cast magnitude above this => strongly tinted page
CAST_WARM_YB = 12.0 # yb above this => warm/sepia (strip); at/below => cool coloured
                    # paper to PRESERVE (sepia is always warm; coloured stock is not)


def sh(*a):
    subprocess.run(a, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def kb(p):
    return (os.path.getsize(p) + 512) // 1024 if os.path.exists(p) else 0


def jbig2_into(dirpath, *args):
    """Run jbig2 in an isolated dir; return total bytes of its output.* files."""
    os.makedirs(dirpath, exist_ok=True)
    for f in glob.glob(os.path.join(dirpath, "output.*")):
        os.remove(f)
    cwd = os.getcwd(); os.chdir(dirpath)
    try:
        with open(os.devnull, "w") as dn:
            subprocess.run(["jbig2", *args], stdout=dn, stderr=dn, check=False)
        files = glob.glob("output.*")
        total = sum(os.path.getsize(f) for f in files)
    finally:
        os.chdir(cwd)
    return total, files


def signals(residual_png):
    im = Image.open(residual_png).convert("RGB"); im.thumbnail((500, 500))
    den = im.filter(ImageFilter.MedianFilter(3))
    a = np.asarray(den, dtype=np.float32); R, G, B = a[..., 0], a[..., 1], a[..., 2]
    content = a.min(-1) < 200
    ink = float(content.mean())
    if content.sum() > 50:
        rg = (R - G)[content]; yb = (0.5 * (R + G) - B)[content]
        cstd = float(np.sqrt(rg.var() + yb.var()))
    else:
        cstd = 0.0
    # fill density of the dark marks: continuous-tone photos are solidly filled,
    # line art / text are thin strokes. Measured from the FULL-RES residual (the
    # antialiased thumbnail would soften strokes and inflate the fill).
    full_L = Image.open(residual_png).convert("L")
    inkimg = full_L.point(lambda p: 255 if p < 150 else 0)
    cov = np.asarray(inkimg.resize((96, 96), Image.BOX), dtype=np.float32) / 255.0
    fig = cov > 0.03
    solid = float((cov[fig] > 0.5).mean()) if fig.any() else 0.0
    return ink, cstd, solid


def whole_colourfulness(path):
    """Cast-invariant opponent-channel std over the whole original page."""
    im = Image.open(path).convert("RGB"); im.thumbnail((400, 400))
    a = np.asarray(im, dtype=np.float32); R, G, B = a[..., 0], a[..., 1], a[..., 2]
    rg, yb = R - G, 0.5 * (R + G) - B
    return float(np.sqrt(rg.var() + yb.var()))


def whole_cast(path):
    """Mean opponent-channel cast (rg, yb) and its magnitude over the page.
    yb>0 is warm/yellow (sepia ageing); yb<0 is cool (blue/green coloured stock)."""
    im = Image.open(path).convert("RGB"); im.thumbnail((400, 400))
    a = np.asarray(im, dtype=np.float32); R, G, B = a[..., 0], a[..., 1], a[..., 2]
    rg = float((R - G).mean()); yb = float((0.5 * (R + G) - B).mean())
    return rg, yb, float(np.hypot(rg, yb))


def route(ink, cstd, solid, whole_cstd, cast):
    rg, yb, mag = cast
    if mag > CAST_STRONG and yb <= CAST_WARM_YB:   # strong, non-warm uniform cast
        return "preserve"                          # intentional coloured paper => keep
    if ink > INK_HIGH:                      # jbig2 -S didn't segment (e.g. CJK text)
        return "colour" if whole_cstd > WHOLE_CSTD_T else "text"
    if ink < INK_T:                        # little/no picture => pure text/line-art
        return "text"
    if cstd > CSTD_T:                      # genuine colour figure
        return "colour"
    if solid > SOLID_T:                    # continuous-tone / halftone photo
        return "greyscale"
    return "text"                          # default: binarize (text + line art)


def process(path):
    name = os.path.splitext(os.path.basename(path))[0]
    d = os.path.join(WORK, name); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    apath = os.path.abspath(path)

    # Normalise to PNG so the whole toolchain works regardless of source format
    # (jbig2/leptonica can't read .jp2, the native BHL/IA format).
    src = os.path.abspath(os.path.join(d, "src.png"))
    sh("magick", apath, src)

    # 1. jbig2 -S: residual picture layer + symbol-coded text stream
    cwd = os.getcwd(); os.chdir(d)
    with open(os.devnull, "w") as dn:
        subprocess.run(["jbig2", "-s", "-S", "-p", src], stdout=dn, stderr=dn, check=False)
    os.chdir(cwd)
    residual = os.path.join(d, "output.0000.png")
    text_stream_b = sum(kb(os.path.join(d, f)) for f in ("output.0000", "output.sym")) * 1024

    # No residual at all => jbig2 -S found nothing to separate => pure text/line.
    if os.path.exists(residual):
        ink, cstd, solid = signals(residual)
    else:
        ink, cstd, solid = 0.0, 0.0, 0.0
    r = route(ink, cstd, solid, whole_colourfulness(src), whole_cast(src))

    # 2. route-appropriate final — WHOLE-PAGE transforms (residual was only for
    #    the routing decision; it is lossy and not used as output).
    final = os.path.join(d, "final.png")
    if r == "text":
        sh("magick", src, "-colorspace", "Gray", "-auto-threshold", "OTSU",
           "-type", "bilevel", final)
        bw_b, _ = jbig2_into(os.path.join(d, "sz"), "-p", os.path.abspath(final))
        final_note = f"binarized whole page · {(bw_b+512)//1024} KB jbig2"
    elif r == "colour":
        # de-sepia the whole page (README recipe): removes the orange mask but
        # keeps text, captions and every element.
        sh("magick", src, "-negate", "-channel", "all", "-normalize",
           "-negate", "-channel", "all", final)
        final_note = f"de-sepia whole page · {kb(final)} KB"
    elif r == "preserve":
        # intentional coloured paper: pass through untouched.
        shutil.copy(src, final)
        final_note = f"preserved (coloured paper) · {kb(final)} KB"
    else:
        # greyscale photo: neutralise the tint, keep tone + text.
        sh("magick", src, "-colorspace", "Gray", "-normalize", final)
        final_note = f"greyscale whole page · {kb(final)} KB"

    # previews
    prev = {}
    for key, img in (("orig", src), ("resid", residual), ("final", final)):
        if not os.path.exists(img):
            prev[key] = None; continue
        out = os.path.join(d, f"{key}_prev.png")
        sh("magick", img, "-resize", f"{PREVW}x", out)
        prev[key] = os.path.relpath(out, HERE)
    return dict(name=name, ink=ink, cstd=cstd, solid=solid, route=r, src_kb=kb(apath),
                text_kb=(text_stream_b + 512) // 1024, final_note=final_note, prev=prev)


def html(results):
    sec = []
    for r in results:
        sec.append(f"""
<h2>{r['name']} &nbsp;<small>route: <b>{r['route']}</b> ·
ink={r['ink']:.3f} · pic_cstd={r['cstd']:.1f} · solid={r['solid']:.2f} · text-stream {r['text_kb']} KB</small></h2>
<div class=row>
  <figure><figcaption>original ({r['src_kb']} KB)</figcaption><img src="{r['prev']['orig']}"></figure>
  <figure><figcaption>jbig2 -S residual (routing only / figure extract)</figcaption>{f'<img src="{r["prev"]["resid"]}">' if r['prev']['resid'] else '<div style="color:#999;padding:2em 0">(none — pure text/line)</div>'}</figure>
  <figure><figcaption>FINAL — {r['final_note']}</figcaption><img src="{r['prev']['final']}"></figure>
</div>""")
    tbl = "\n".join(
        f"<tr><td>{r['name']}</td><td>{r['ink']:.3f}</td><td>{r['cstd']:.1f}</td>"
        f"<td><b>{r['route']}</b></td></tr>" for r in results)
    doc = f"""<!doctype html><meta charset=utf-8><title>BHL routed pipeline</title>
<style>body{{font:14px/1.45 -apple-system,sans-serif;margin:24px;max-width:1300px}}
h2{{margin-top:1.6em;border-bottom:1px solid #ccc}} small{{color:#666;font-weight:normal}}
.row{{display:flex;gap:14px;flex-wrap:wrap}} figure{{margin:0;width:{PREVW}px}}
img{{width:{PREVW}px;border:1px solid #bbb;display:block}} figcaption{{color:#333}}
table{{border-collapse:collapse;margin:1em 0}} td,th{{border:1px solid #ccc;padding:4px 10px}}
td:first-child{{text-align:left}}</style>
<h1>BHL routed transform — jbig2 -S based</h1>
<p>Route: <code>ink&lt;{INK_T}</code> ⇒ text (binarize); else
<code>pic_cstd&gt;{CSTD_T}</code> ⇒ colour (de-sepia) else greyscale.</p>
<table><tr><th>page</th><th>ink_frac</th><th>pic_cstd</th><th>route</th></tr>
{tbl}</table>
{''.join(sec)}"""
    with open(os.path.join(HERE, "pipeline.html"), "w") as f:
        f.write(doc)


def main():
    os.makedirs(WORK, exist_ok=True)
    paths = sorted(p for p in glob.glob(os.path.join(INPUT, "*"))
                   if p.lower().endswith((".jpg", ".jpeg", ".png", ".jp2", ".tif", ".tiff", ".webp")))
    results = []
    for p in paths:
        print("processing", os.path.basename(p))
        results.append(process(p))
    html(results)
    print(f"\nwrote {os.path.join(HERE, 'pipeline.html')}")
    for r in results:
        print(f"  {r['name']:16} {r['route']:9} ink={r['ink']:.3f} cstd={r['cstd']:.1f}")


if __name__ == "__main__":
    main()
