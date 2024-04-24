# Experiments with making small black and white images and PDFs for BHL

Once again, messing about with ideas to make small PDFs from BHL content, using jbig2 for compression, aiming at PDFs from images 685 pixels wide (Google Books dimensions).

On a Mac OCR is almost redundant as the OS automatically OCRs images.

## Handling plates

Turns out there is a simple way to remove (most) of the sepia tone in a BHL scan:

```
convert 16281585.jpg -negate -channel all -normalize -negate -channel all 16281585-rgb.jpg
```

where `16281585.jpg` is a BHL page image. This is based on the thread [Removing orange tint-mask from color-negatives](https://www.imagemagick.org/discourse-server/viewtopic.php?t=14081).


## Reading

- Page, R. (2024). Notes on transforming BHL images [doi:10.59350/2gpbb-98a53](https://doi.org/10.59350/2gpbb-98a53)