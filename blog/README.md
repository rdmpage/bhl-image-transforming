
Notes on transforming BHL images

I've been down this road before, e.g. [BHL, DjVu, and reading the f*cking manual](https://iphylo.blogspot.com/2011/04/bhl-djvu-and-reading-fcking-manual.html) and [Demo of full-text indexing of BHL using CouchDB hosted by Cloudant](https://iphylo.blogspot.com/2015/08/demo-of-full-text-indexing-of-bhl-using.html), but I'm revisiting converting BHL page scans to black and white images, partly to clean them up, partly to make them closer to what a modern reader might expect, and partly to reduce the size of the image. The later means faster loading times, and smaller PDFs for articles.

The links above explored using foreground image layers from DjVu (less useful now that DjVu is almost dead as a format), and using CSS in web browsers to convert a colour image to gray scale. I've also experimented with the approach taken by Google Books (see [https://github.com/rdmpage/google-book-images](https://github.com/rdmpage/google-book-images)), which uses [jbig2enc](https://github.com/agl/jbig2enc) to compress images and reduce the number of colours.

In my latest experiments I use jbig2enc to transform BHL page images into black and white images where each pixel is either black or white (i.e., image depth = 1), then use imagemagick to resize the image to the Google Books with of 685 pixels and a depth of 2. Typically this gives an image around 25Kb - 30Kb in size. It looks clean and readable.

[images]


This approach breaks down for photographs and especially colour plates. For example, this image looks horrible:

[images]

When compressing images that have photos or illustrations jbig2enc can the part of the image that includes the illustration, for example:

[output] 

This isn't perfect, but it raises the possibility that we can convert text and line drawings to black and white, then add back photographs and plates (whether black or white, or colour). After some experimentation using tools such as [ImageMagick composite](https://imagemagick.org/script/composite.php) I have a simple workflow:

- compress page image using jbig2enc
- take the extracted illustration and set all white pixels to be transparent
- convert the black and white image output by jbig2enc to colour (required for the next step)
- create a composite image by overlaying the extracted illustration (now on a transparent background) on top of the black and white page image 

The result looks passable:

[image]

In this case we still have a lot of the sepia-toned background, the illustration hasn't been cleanly separated, but we do at least get some colour. 

Still work to do, but it looks promising, and suggests a way to make dramatically smaller PDFs of BHL content.


## Reading

Adam Langley, Dan S. Bloomberg, "Google Books: making the public domain universally accessible", Proc. SPIE 6500, Document Recognition and Retrieval XIV, 65000H (2007/01/29); [doi:10.1117/12.710609](http://dx.doi.org/10.1117/12.710609)



		// remove background 
			$command = "mogrify -transparent white output.0000.png";
			echo $command . "\n";
			
			system($command);
			
			// base must be in colour if we want a colour plate
			$command = "mogrify $output_filename -define png:color-type=2 $output_filename";
			echo $command . "\n";

			system($command);			
			
			// add the threshold image onto the outout image
			$command = "magick composite output.0000.png $output_filename  $output_filename";
			echo $command . "\n";
			
			system($command);

			// resize
			$depth = 8;
			$command = "mogrify -resize $width -depth $depth " . $output_filename;
	
			echo $command . "\n";
			
			system($command);
