#!/bin/bash
# Threshold / routing comparison on representative BHL page types.
# Outputs previews, 100% crops, jbig2 sizes, and a routing-signal table into
# this dir, plus index.html. Run from repo root: bash compare/run.sh
set -e
cd "$(dirname "$0")/.."
OUT=compare
PREVW=620          # preview width in the HTML

TEXT=31940305.jpg
PHOTO=grapsoidcrabsofa00rath_0521.jpg
PLATE=birdsAustraliav6Goul_0336.jpg

CROP="1100x470+470+250"   # a body-text region on the text page (full-res coords)

prev() { magick "$1" -resize ${PREVW}x "$2"; }     # downscaled preview
sz()   { s=$(stat -f%z "$1"); echo $(( (s+512)/1024 )); }   # KB

# jbig2 payload size (KB) for a bilevel PNG: generic coder, sum output bytes.
jbsize() {
  rm -f output.* /tmp/jb.out 2>/dev/null || true
  jbig2 -p "$1" > /tmp/jb.out 2>/dev/null || true
  b=$(cat output.* /tmp/jb.out 2>/dev/null | wc -c | tr -d ' ')
  rm -f output.* /tmp/jb.out 2>/dev/null || true
  echo $(( (b+512)/1024 ))
}

echo "== TEXT page: threshold methods =="
magick "$TEXT" -colorspace Gray g_text.miff
# variants (full-res bilevel)
magick g_text.miff -threshold 60%                 -type bilevel $OUT/t_fixlo.png
magick g_text.miff -threshold 85%                 -type bilevel $OUT/t_fixhi.png
magick g_text.miff -auto-threshold OTSU           -type bilevel $OUT/t_otsu.png
magick g_text.miff -lat 25x25-12%                 -type bilevel $OUT/t_lat.png

prev "$TEXT" $OUT/t_orig_prev.png
for v in fixlo fixhi otsu lat; do prev $OUT/t_$v.png $OUT/t_${v}_prev.png; done
# 100% crops (aligned)
magick "$TEXT" -crop $CROP +repage $OUT/t_orig_crop.png
for v in fixlo fixhi otsu lat; do magick $OUT/t_$v.png -crop $CROP +repage $OUT/t_${v}_crop.png; done

echo "== PHOTO page: binarize (wrong) vs greyscale (right) =="
magick "$PHOTO" -auto-threshold OTSU -type bilevel $OUT/p_otsu.png
magick "$PHOTO" -colorspace Gray -normalize $OUT/p_gray.png
prev "$PHOTO"      $OUT/p_orig_prev.png
prev $OUT/p_otsu.png $OUT/p_otsu_prev.png
prev $OUT/p_gray.png $OUT/p_gray_prev.png

echo "== PLATE: de-sepia =="
magick "$PLATE" -negate -channel all -normalize -negate -channel all $OUT/l_desepia.png
prev "$PLATE"         $OUT/l_orig_prev.png
prev $OUT/l_desepia.png $OUT/l_desepia_prev.png

echo "== sizes =="
J_FIXLO=$(jbsize $OUT/t_fixlo.png); J_FIXHI=$(jbsize $OUT/t_fixhi.png)
J_OTSU=$(jbsize $OUT/t_otsu.png);   J_LAT=$(jbsize $OUT/t_lat.png)
S_TEXTJPG=$(sz "$TEXT")

echo "== routing signals =="
# For each sample: mean saturation, % strongly-saturated pixels (colour signal),
# and midtone fraction in (20%,80%] (photo-vs-bimodal signal).
signals() {
  local f="$1"
  local sat=$(magick "$f" -colorspace HSB -channel G -separate -format "%[fx:mean]" info:)
  local satpct=$(magick "$f" -colorspace HSB -channel G -separate -threshold 25% -format "%[fx:mean]" info:)
  local above20=$(magick "$f" -colorspace Gray -threshold 20% -format "%[fx:mean]" info:)
  local above80=$(magick "$f" -colorspace Gray -threshold 80% -format "%[fx:mean]" info:)
  local mid=$(awk "BEGIN{printf \"%.3f\", $above20-$above80}")
  printf "%.3f|%.3f|%.3f" "$sat" "$satpct" "$mid"
}
SIG_T=$(signals "$TEXT"); SIG_P=$(signals "$PHOTO"); SIG_L=$(signals "$PLATE")
rm -f g_text.miff

# ---------- HTML ----------
row_t() { # variant key, label, jbig2 KB
  echo "<figure><figcaption>$2<br><b>${3} KB</b> jbig2</figcaption>"
  echo "<img src='t_${1}_prev.png'><br><img class=crop src='t_${1}_crop.png'></figure>"
}
{
cat <<HTML
<!doctype html><meta charset=utf-8><title>BHL threshold / routing comparison</title>
<style>
body{font:14px/1.45 -apple-system,sans-serif;margin:24px;max-width:1300px}
h2{margin-top:2em;border-bottom:1px solid #ccc} .row{display:flex;gap:14px;flex-wrap:wrap}
figure{margin:0;width:${PREVW}px} img{width:${PREVW}px;border:1px solid #bbb;display:block}
img.crop{margin-top:6px;height:auto} figcaption{margin:2px 0;color:#333}
table{border-collapse:collapse;margin:1em 0} td,th{border:1px solid #ccc;padding:4px 10px;text-align:right}
th:first-child,td:first-child{text-align:left} .note{background:#fffbe6;padding:10px 14px;border-left:4px solid #e6c200}
</style>
<h1>BHL threshold &amp; routing comparison</h1>
<p class=note>Source text page is ${S_TEXTJPG} KB as the original sepia JPEG. The
binarized + jbig2 variants below are the full-resolution payload that would go
into a PDF.</p>

<h2>1. Text page — automating the threshold</h2>
<p>A <em>fixed</em> threshold can't suit every page: 60% keeps background grime,
85% drops faint strokes. Otsu and adaptive (LAT) derive the cut from the image
itself — no manual <code>-T</code>. Top = full page; bottom = 100% crop.</p>
<div class=row>
$(echo "<figure><figcaption>original (sepia)</figcaption><img src='t_orig_prev.png'><br><img class=crop src='t_orig_crop.png'></figure>")
$(row_t fixlo "fixed −threshold 60%" $J_FIXLO)
$(row_t fixhi "fixed −threshold 85%" $J_FIXHI)
$(row_t otsu  "Otsu (auto, global)"  $J_OTSU)
$(row_t lat   "Adaptive LAT (local)" $J_LAT)
</div>

<h2>2. B&amp;W photo — why routing matters</h2>
<p>The same Otsu binarization that's great for text <b>destroys</b> a continuous-tone
halftone. A greyscale page must be desaturated + contrast-normalised, never binarized.</p>
<div class=row>
<figure><figcaption>original (sepia halftone)</figcaption><img src='p_orig_prev.png'></figure>
<figure><figcaption>Otsu binarized — <b>wrong</b></figcaption><img src='p_otsu_prev.png'></figure>
<figure><figcaption>greyscale + normalize — right</figcaption><img src='p_gray_prev.png'></figure>
</div>

<h2>3. Colour plate — de-sepia</h2>
<div class=row>
<figure><figcaption>original</figcaption><img src='l_orig_prev.png'></figure>
<figure><figcaption>de-sepia (negate·normalize·negate)</figcaption><img src='l_desepia_prev.png'></figure>
</div>

<h2>4. Routing signals — do they separate the types?</h2>
<p>Cheap per-page measurements that drive the routing decision:</p>
<table>
<tr><th>page</th><th>mean saturation</th><th>% saturated (&gt;25%)</th><th>midtone fraction</th><th>→ route</th></tr>
<tr><td>text (31940305)</td><td>$(echo $SIG_T|cut -d'|' -f1)</td><td>$(echo $SIG_T|cut -d'|' -f2)</td><td>$(echo $SIG_T|cut -d'|' -f3)</td><td>binarize</td></tr>
<tr><td>B&amp;W photo (grapsoid)</td><td>$(echo $SIG_P|cut -d'|' -f1)</td><td>$(echo $SIG_P|cut -d'|' -f2)</td><td>$(echo $SIG_P|cut -d'|' -f3)</td><td>greyscale</td></tr>
<tr><td>colour plate (bird)</td><td>$(echo $SIG_L|cut -d'|' -f1)</td><td>$(echo $SIG_L|cut -d'|' -f2)</td><td>$(echo $SIG_L|cut -d'|' -f3)</td><td>de-sepia colour</td></tr>
</table>
<p>Low saturation + low midtone ⇒ text (binarize). Low saturation + high midtone
⇒ greyscale photo (don't binarize). High saturation ⇒ colour plate (de-sepia).</p>
HTML
} > $OUT/index.html
echo "wrote $OUT/index.html"