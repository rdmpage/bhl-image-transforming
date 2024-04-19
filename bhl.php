<?php

function get($url, $format = '')
{
	
	$ch = curl_init();
	curl_setopt($ch, CURLOPT_URL, $url);
	curl_setopt($ch, CURLOPT_HEADER, 0);
	curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
	curl_setopt($ch, CURLOPT_FOLLOWLOCATION, 1);
	
	if ($format != '')
	{
		curl_setopt($ch, CURLOPT_HTTPHEADER, array("Accept: " . $format));	
	}
	
	$response = curl_exec($ch);
	if($response == FALSE) 
	{
		$errorText = curl_error($ch);
		curl_close($ch);
		die($errorText);
	}
	
	$info = curl_getinfo($ch);
	$http_code = $info['http_code'];
	
	curl_close($ch);
	
	return $response;
}

$pages = array(
"62994238",
"62994239",
"62994240",
"62994241",
"62994242",
"62994243",
"62994244",
"62994245",
"62994246",
"62994247",
);

// 248475
$pages = array(
 "43605918",
"43605919"
);

// 115363
$pages = array(
"41229695",
        "41229696",
        "41229697",
        "41229698",
        "41229699",
        "41229700",
        "41229701",
        "41229702",
        "41229703",
        "41229704",
        "41229705",
        "41229706",
        "41229707",
        "41229708",
        "41229709",
        "41229710",
        "41229711",
        "41229712",
        "41229713",
        "41229714",
        "41229715",
        "41229716",
        "41229717",
        "41229718",
        "41229719",
        "41229720",
        "41229721",
        "41229722",
        "41229723",
        "41229724",
        "41229725",
        "41229726",
        "41229727",
        "41229728",
        "41229729",
        "41229730",
        "41229731",
        "41229732",
        "41229733",
        "41229734",
        "41229735",
        "41229736",
        "41229737",
        "41229738",
        "41229739",
        "41229740",
        "41229741",
        "41229742",
        "41229743",
        "41229744",
        "41229745",
        "41229746",
        "41229747",
        "41229748",
        "41229749",
        "41229750",
        "41229751",
        "41229752",
        "41229753",
        "41229754",
        "41229755",
        "41229756",
        "41229757",
        "41229758",
        "41229759",
        "41229760",
        "41229761"
        );
        
// photo<a href="../../Sites/classification-o/col/check.php">check.php</a>
$pages=array(
63294239
);

$pages=array(
//16281064, // line drawing
16281585, // plate
//63294239, // photo

//41229702, // line drawing with stippling

//62994245, // line drawing

);

// need to think carefully about detecting photos, plates, etc.

$force_bw = true;
$force_bw = false;

$file_list = array();

foreach ($pages as $PageID)
{
	$filename = $PageID . '.jpg';
	
	if (!file_exists($filename))
	{
		$url = 'https://www.biodiversitylibrary.org/pageimage/' . $PageID;
		$image = get($url);
		file_put_contents($filename, $image);
	}		
}

foreach ($pages as $PageID)
{
	$source_filename = $PageID . '.jpg';
	$output_filename = $PageID . '.png';
	
	$file_list[] = $output_filename;
	
	if (!file_exists($output_filename))
	{
	/*
	Options:
	  -b <basename>: output file root name when using symbol coding
	  -d --duplicate-line-removal: use TPGD in generic region coder
	  -p --pdf: produce PDF ready data
	  -s --symbol-mode: use text region, not generic coder
	  -t <threshold>: set classification threshold for symbol coder (def: 0.85)
	  -T <bw threshold>: set 1 bpp threshold (def: 188)
	  -r --refine: use refinement (requires -s: lossless)
	  -O <outfile>: dump thresholded image as PNG
	  -2: upsample 2x before thresholding
	  -4: upsample 4x before thresholding
	  -S: remove images from mixed input and save separately
	  -j --jpeg-output: write images from mixed input as JPEG
	  -a --auto-thresh: use automatic thresholding in symbol encoder
	  --no-hash: disables use of hash function for automatic thresholding
	  -V --version: version info
	  -v: be verbose
	*/	

		$options = array(
			'-s', // use text region, not generic coder
			'-S', // remove images from mixed input and save separately
			'-p', // produce PDF ready data
			"-O $output_filename", // <outfile>: dump thresholded image as PNG
			
			// 248475, dark background, removes it well
			//"-T 100", // <bw threshold>: set 1 bpp threshold (def: 188)
			
			// 63294239 B&W photo, seems to work quite well
			//"-T 120", // <bw threshold>: set 1 bpp threshold (def: 188)
		);
	
		$command = "jbig2 " . join(" ", $options) . " " . $source_filename;
	
		echo "$command\n";
	
		system($command);
		
		// do we have a separate threshold image?
		$threshold_files = array();
		
		$working_files = scandir(dirname(__FILE__));
		foreach ($working_files as $outfile)
		{
			if (preg_match('/^output/', $outfile))
			{
				$threshold_files[] = $outfile;
			}
		}
		
		// resize
		
		$width = 685; // Google Books
		
		if (count($threshold_files) < 3 || $force_bw)
		{
			// simple resize of output image, typically text or line drawing
			$depth = 2; // 1 is simple black and white, 4 works quite well
			$command = "mogrify -resize $width -depth $depth " . $output_filename;
	
			echo $command . "\n";
	
			system($command);
		}
		else
		{
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
			
		}
		
		// clean up
		foreach ($threshold_files as $threshold_filename)
		{
			unlink($threshold_filename);
		}
	}

}

// make PDF
$file_list_name = "myfiles.txt";
file_put_contents($file_list_name, join("\n", $file_list));

$command = "convert @$file_list_name test.pdf";

echo $command . "\n";
	
system($command);



?>

