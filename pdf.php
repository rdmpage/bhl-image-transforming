<?php
// JBIG2 Encoder in PHP
// This is a very simple script to make a PDF file out of the output of a
// multipage symbol compression.
// Run jbig2 -s -p <other options> image1.jpeg image1.jpeg ...
// php pdf.php output > out.pdf

$dpi = 72;

class Ref {
    public $x;

    public function __construct($x) {
        $this->x = $x;
    }

    public function __toString() {
        return "$this->x 0 R";
    }
}

class Dict {
    public $d;

    public function __construct($values = []) {
        $this->d = [];
        $this->d = array_merge($this->d, $values);
    }

    public function __toString() {
        $s = '<< ';
        foreach ($this->d as $x => $y) {
            $s .= "/$x $y\n";
        }
        $s .= ">>\n";
        return $s;
    }
}

global $global_next_id;
$global_next_id = 1;

class Obj {
    public static $next_id = 1;
    public $d;
    public $stream;
    public $id;

    public function __construct($d = [], $stream = null) {
        global $global_next_id;

        if ($stream !== null) {
            $d['Length'] = strlen($stream);
        }
        $this->d = new Dict($d);
        $this->stream = $stream;
        $this->id = $global_next_id;
        $global_next_id++;
    }

    public function __toString() {
        $s = strval($this->d);
        if ($this->stream !== null) {
            $s .= "stream\n" . $this->stream . "\nendstream\n";
        }
        $s .= "endobj\n";
        return $s;
    }
}

class Doc {
    public $objs;
    public $pages;

    public function __construct() {
        $this->objs = [];
        $this->pages = [];
    }

    public function add_object($o) {
        $this->objs[] = $o;
        return $o;
    }

    public function add_page($o) {
        $this->pages[] = $o;
        return $this->add_object($o);
    }

    public function __toString() {
        $a = [];
        $j = 0;
        $offsets = [];

        $a[] = "%PDF-1.4";
        foreach ($this->objs as $o) {
            $offsets[] = $j;
            $a[] = "$o->id 0 obj";
            $a[] = strval($o);
            $j += strlen($a[count($a) - 1]) + 1;
        }
        $xrefstart = $j;
        $a[] = "xref";
        $a[] = "0 " . (count($offsets) + 1);
        $a[] = "0000000000 65535 f ";
        foreach ($offsets as $offset) {
            $a[] = sprintf("%010d 00000 n ", $offset);
        }
        $a[] = "";
        $a[] = "trailer";
        $a[] = "<< /Size " . (count($offsets) + 1) . "\n/Root 1 0 R >>";
        $a[] = "startxref";
        $a[] = strval($xrefstart);
        $a[] = "%%EOF";

        return implode("\n", $a);
    }
}

function ref($x) {
    return "$x 0 R";
}

function main($symboltable = 'symboltable', $pagefiles = []) {
    $doc = new Doc();
    $doc->add_object(new Obj(['Type' => '/Catalog', 'Outlines' => ref(2), 'Pages' => ref(3)]));
    $doc->add_object(new Obj(['Type' => '/Outlines', 'Count' => '0']));
    $pages = new Obj(['Type' => '/Pages']);
    $doc->add_object($pages);

    $symd = $doc->add_object(new Obj([], file_get_contents($symboltable)));

    $pagefiles = glob($pagefiles);
    sort($pagefiles);
    $page_objs = [];

    foreach ($pagefiles as $p) {
        if (!file_exists($p)) {
            fwrite(STDERR, "error reading page file $p\n");
            continue;
        }

        $contents = file_get_contents($p);
        list($width, $height, $xres, $yres) = array_values(unpack('N4', substr($contents, 11, 16)));

        if ($xres == 0) {
            $xres = $GLOBALS['dpi'];
        }
        if ($yres == 0) {
            $yres = $GLOBALS['dpi'];
        }

        $xobj = new Obj(['Type' => '/XObject', 'Subtype' => '/Image', 'Width' => strval($width), 'Height' => strval($height), 
            'ColorSpace' => '/DeviceGray', 'BitsPerComponent' => '1', 'Filter' => '/JBIG2Decode', 
            'DecodeParms' => ' << /JBIG2Globals ' . $symd->id . ' 0 R >>'], $contents);
        
        $contents = new Obj([], sprintf('q %f 0 0 %f 0 0 cm /Im1 Do Q', floatval($width * 72) / $xres, floatval($height * 72) / $yres));
        $resources = new Obj(['ProcSet' => '[/PDF /ImageB]', 'XObject' => '<< /Im1 ' . $xobj->id . ' 0 R >>']);

        $page = new Obj(['Type' => '/Page', 'Parent' => '3 0 R', 'MediaBox' => sprintf('[ 0 0 %f %f ]', 
            floatval($width * 72) / $xres, floatval($height * 72) / $yres), 'Contents' => ref($contents->id), 
            'Resources' => ref($resources->id)]);

        foreach ([$xobj, $contents, $resources, $page] as $obj) {
            $doc->add_object($obj);
        }

        $page_objs[] = $page;
        $pages->d->d['Count'] = strval(count($page_objs));
        $pages->d->d['Kids'] = '[' . implode(' ', array_map('ref', array_column($page_objs, 'id'))) . ']';
    }

    echo strval($doc);
}

if (PHP_SAPI == "cli") {
    if ($argc == 2) {
        $sym = $argv[1] . '.sym';
        $pages = $argv[1] . '.[0-9]*';
    } elseif ($argc == 1) {
        $sym = 'symboltable';
        $pages = 'page-*';
    } else {
        fwrite(STDERR, "Usage: {$argv[0]} [file_basename] > out.pdf\n");
        exit(1);
    }

    if (!file_exists($sym)) {
        fwrite(STDERR, "symbol table $sym not found!\n");
        exit(1);
    }

    if (empty(glob($pages))) {
        fwrite(STDERR, "no pages found!\n");
        exit(1);
    }

    main($sym, $pages);
}
?>
