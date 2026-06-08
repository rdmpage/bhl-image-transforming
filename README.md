# Experiments with making small black and white images and PDFs for BHL

Once again, messing about with ideas to make small PDFs from BHL content, using jbig2 for compression, aiming at PDFs from images 685 pixels wide (Google Books dimensions).

On a Mac OCR is almost redundant as the OS automatically OCRs images.

## Handling plates

Turns out there is a simple way to remove (most) of the sepia tone in a BHL scan:

```
convert 16281585.jpg -negate -channel all -normalize -negate -channel all 16281585-rgb.jpg
```

where `16281585.jpg` is a BHL page image. This is based on the thread [Removing orange tint-mask from color-negatives](https://www.imagemagick.org/discourse-server/viewtopic.php?t=14081).

## Making small PDFs

Reading the original work by Google there is a script to build PDF from jbig2 output that reduces PDF size using the encodings. Original code in Python 2, I failed to get it working for Python 3, so got ChatGPT to convert it to PHP. Works fine. Example:

```
jbig2 -s -p -T 100 *.jp2       
pdf.php output > output.pdf
```


## Reading

- Page, R. (2024). Notes on transforming BHL images [doi:10.59350/2gpbb-98a53](https://doi.org/10.59350/2gpbb-98a53)