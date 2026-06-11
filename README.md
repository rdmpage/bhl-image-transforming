# Experiments with making small black and white images and PDFs for BHL

Once again, messing about with ideas to make small PDFs from BHL content, using jbig2 for compression, aiming at PDFs from images 685 pixels wide (Google Books dimensions).

On a Mac OCR is almost redundant as the OS automatically OCRs images.

## Handling plates

Turns out there is a simple way to remove (most) of the sepia tone in a BHL scan:

```
convert 16281585.jpg -negate -channel all -normalize -negate -channel all 16281585-rgb.jpg
```

where `16281585.jpg` is a BHL page image. This is based on the thread [Removing orange tint-mask from color-negatives](https://www.imagemagick.org/discourse-server/viewtopic.php?t=14081).

## Routing pages automatically (`compare/`)

The recipes above each suit a *particular kind* of page (binarize text,
de-sepia a plate, leave a photo as greytone). The `compare/` directory adds a
**router** that looks at a page and picks the right one automatically, so a
whole scanned item can be processed without hand-sorting.

```bash
python compare/pipeline.py        # processes every image in compare/input/
# -> writes compare/work/<page>/final.png and compare/pipeline.html
```

**The key idea: use `jbig2 -S` for the *decision*, not the output.**
`jbig2 -s -S -p page.jpg` separates the page into a symbol layer (the text) and
a *residual* layer `output.0000.png` — everything jbig2 could **not** explain as
repeated text symbols. For a clean text page the residual is near-blank; for a
plate or photo it holds the picture. That residual is a near-perfect "is there a
picture here, and what is it like?" probe — but it is **lossy** (it drops text
and degrades the image), so it is used **only to route**. The final output is
always a whole-page transform, never the residual itself.

Measured from the residual (and the whole page), in order:

1. **Coloured paper** — strong whole-page colour cast that is *not* warm
   (cool blue/green, not sepia-yellow) ⇒ `preserve`, passed through untouched
   (e.g. a teal title page). Sepia is always warm, so it never matches here.
2. **`ink_frac`** (residual coverage) ≈ 1.0 ⇒ jbig2 didn't segment (e.g. CJK
   text); fall back to whole-page colourfulness. Very low ⇒ pure text/line art
   ⇒ binarize.
3. **`pic_cstd`** — colourfulness of the *picture* pixels (cast-invariant
   opponent-channel spread). High ⇒ a real colour plate ⇒ de-sepia. The
   threshold sits above tinted-but-monochrome photos so a warm cast alone
   doesn't read as colour.
4. **`solid_frac`** — fill density of the dark marks. Solidly filled ⇒ a
   continuous-tone (halftone) **photo** ⇒ keep as neutral greytone. Thin strokes
   ⇒ line art ⇒ binarize.

So each page lands in one of four routes:

| route | output transform |
|---|---|
| text / line art | Otsu binarize → jbig2 (smallest, sharpest) |
| greyscale photo | `-colorspace Gray -normalize` (no binarizing — halftones look bad as bilevel) |
| colour plate | the whole-page de-sepia recipe above |
| coloured paper | preserved untouched |

`compare/pipeline.py` is the router; `compare/input/` is a small labelled test
set spanning all four cases (plus jp2/webp and CJK edge cases); `pipeline.html`
shows every page with its residual, route, and before/after. The earlier
`build.py` / `run.sh` / `diag.py` are threshold-exploration scratch tools.

Known edge case: a faint continuous-tone figure that jbig2 *doesn't* separate
(it stays in the symbol layer) is invisible to the residual probe and gets
binarized, losing its shading — this needs region-based figure detection.

## Making small PDFs

Reading the original work by Google there is a script to build PDF from jbig2 output that reduces PDF size using the encodings. Original code in Python 2, I failed to get it working for Python 3, so got ChatGPT to convert it to PHP. Works fine. Example:

```
jbig2 -s -p -T 100 *.jp2       
pdf.php output > output.pdf
```


## Reading

- Page, R. (2024). Notes on transforming BHL images [doi:10.59350/2gpbb-98a53](https://doi.org/10.59350/2gpbb-98a53)