# vc_extractor — Vacuum Cup & Chamber Coordinate Extraction

This module extracts vacuum cup/chamber coordinates from Handler Kit drawings (PDF/images), OCRs axis labels, and matches them to detected vacuum cups. It produces analysis-ready JSON and annotated images for downstream overlap detection against DXF lead frames.

Core pipeline:
1) Preprocess and clean the page image
2) OCR axis ticks/labels (with orientation handling)
3) Detect vacuum cups (multiple methods available)
4) Match each cup to nearest X/Y labels
5) Export structured results + visualization

Repo context: this folder is part of the [mapping_web_tool](https://github.com/HarrisonKuo47/mapping_web_tool) project.

---

## Files and Responsibilities

- axis_locate.py  
  Interactive image helper for clicking on rotated images to understand rotation → original coordinate mapping.  
  [view source](https://github.com/HarrisonKuo47/mapping_web_tool/blob/main/vc_extractor/axis_locate.py)

- extract_axis.py  
  OCR engine for numeric axis labels (X/Y), including preprocessing, deskew, line removal, 0/90/180/270° rotation handling and bounding-box remapping.  
  [view source](https://github.com/HarrisonKuo47/mapping_web_tool/blob/main/vc_extractor/extract_axis.py)

- vacuum_cup_detector.py  
  Multiple vacuum cup detectors:
  - Geometric (Hough circles + validation)
  - Contour-based (circularity/area/aspect ratio)
  - Adaptive (synthetic multi-template matching with NMS)
  - Hybrid (fusion and clustering across the three)  
  [view source](https://github.com/HarrisonKuo47/mapping_web_tool/blob/main/vc_extractor/vacuum_cup_detector.py)

- coordinate_matcher.py  
  Orchestrates the full extraction:
  - Page cleaning via filter_page (external)
  - Axis OCR via extract_axis
  - Cup detection (template/geometric/contour/adaptive/hybrid)
  - Nearest-label matching with rotation-aware remapping
  - Visualization export  
  [view source](https://github.com/HarrisonKuo47/mapping_web_tool/blob/main/vc_extractor/coordinate_matcher.py)

- run_extraction.py  
  Example runner that iterates PDFs, runs the extractor, and prints results.  
  [view source](https://github.com/HarrisonKuo47/mapping_web_tool/blob/main/vc_extractor/run_extraction.py)

- requirements.txt  
  Minimal, module-level Python requirements (see also project root requirements if running via FastAPI).  
  [view source](https://github.com/HarrisonKuo47/mapping_web_tool/blob/main/vc_extractor/requirements.txt)

---

## Installation

Option A — Module-only
```bash
pip install -r vc_extractor/requirements.txt
```

Option B — Full web tool (recommended if using the FastAPI app)
```bash
pip install -r requirements.txt
```

Additional system dependencies:
- Tesseract OCR (required by pytesseract)
  - Set env var TESSERACT_CMD to the executable path (e.g., Windows: C:\Program Files\Tesseract-OCR\tesseract.exe)
- Optional (only if you use extract_axis.pdf_to_images): Poppler for PDF rasterization (used by pdf2image)
- PyMuPDF (fitz) is used by coordinate_matcher to rasterize PDFs via filter_page

Note: extract_axis.py imports pdf2image and PIL; if you call those functions directly, ensure these are installed:
```bash
pip install pdf2image pillow
```

---

## axis_locate.py

Purpose
- Visual debugging tool to click on displayed images (with rotation) and print both rotated and original image coordinates.

Key API
```python
show_click_coords(img, rotation: int, title: str)
```
- rotation: 0, 90 (clockwise), 180
- Displays the image, prints each clicked point’s (x, y) on the rotated image and the remapped (orig_x, orig_y) on the original.

Quick demo
```python
import cv2
from axis_locate import show_click_coords

img = cv2.imread('example.png')
show_click_coords(img, rotation=0, title="Original")
show_click_coords(img, rotation=90, title="CW90")
show_click_coords(img, rotation=180, title="Rot180")
```

---

## extract_axis.py

Purpose
- OCR numeric labels on axes robustly, with preprocessing, optional deskew, long-line removal (dimension/grid), and rotation handling. Returns normalized digits with bounding boxes remapped back to original orientation.

Primary functions
- preprocess(img_bgr, ...): returns a prepped, binarized image with metadata (deskew angle, scale)
- ocr_digits(img_bgr, rotations=[0,90,180,270], ...): runs Tesseract across rotations; remaps detected boxes back to original
- pdf_to_images(pdf_path, dpi=300): rasterize PDF pages (via pdf2image)
- run_on_path(path, **kwargs): batch process over a folder or single file (PDF or image)

Environment
- Set TESSERACT_CMD to specify tesseract binary path.
- Parameters allow choosing thresholding mode (otsu/adaptive), deskew, and line removal aggressiveness.

Output shape (from ocr_digits)
```python
[
  {
    "rotation": 90,
    "deskew_angle": 0.0,
    "scale": 1.0,
    "detections": [
      {"text": "45.5", "conf": 87, "bbox": [x, y, w, h]},
      ...
    ]
  },
  ...
]
```

Notes
- _remap_bbox_from_rotated ensures detected boxes map onto the original image coordinate system regardless of the tested rotation.
- _is_numeric_text keeps digits and + - . / for robust axis labels.

---

## vacuum_cup_detector.py

Purpose
- Provide multiple strategies to find vacuum cups on the drawing:
  - GeometricVacuumCupDetector: Hough circle with a center-structure validation
  - ContourVacuumCupDetector: Canny + morphology + circularity/area/aspect filters
  - AdaptiveVacuumCupDetector: Synthetic templates (circle/cross/dot) with cv2.matchTemplate and NMS
  - HybridVacuumCupDetector: Combine all methods via clustering + voting to stabilize detections

Return format
```python
List[Tuple[int, int, int, int]]  # bounding boxes as (x, y, w, h)
```

Configuration tips
- Geometric: tune min_radius, max_radius, min_dist for your PDF resolution
- Contour: tune min_area, max_area, circularity_threshold
- Adaptive: adjust threshold (default 0.5) and template sizes (16..32) if needed
- Hybrid: fusion distance threshold default ~25px (see _cluster_detections)

---

## coordinate_matcher.py

Purpose
- End-to-end vacuum cup coordinate extraction from a PDF:
  1. Render and clean the target PDF page (via filter_page)
  2. OCR X and Y axis labels using extract_axis
     - X labels read at rotate 180
     - Y labels read at rotate 90
     - All detections remapped to original image coordinates
  3. Detect vacuum cups with chosen method: "template", "geometric", "contour", "adaptive", or "hybrid"
     - Template mode requires template images and multi_scale_match
  4. Match each cup’s center to nearest X and Y labels in the appropriate oriented space
  5. Export JSON results and a color-coded visualization PNG

Key data classes
```python
@dataclass
class CoordinateLabel:
    value: str
    x: int; y: int            # original image coordinates
    axis: str                 # 'x' or 'y'
    rotation: int             # rotation used during OCR
    original_x: int; original_y: int  # coords before remapping

@dataclass
class VacuumCup:
    id: int
    center_x: int; center_y: int
    bbox: Tuple[int, int, int, int]
    detection_method: str
    nearest_x_coord: Optional[CoordinateLabel]
    nearest_y_coord: Optional[CoordinateLabel]
```

Main API
```python
from coordinate_matcher import VacuumCupCoordinateExtractor

extractor = VacuumCupCoordinateExtractor(
    template_paths=[...],          # required for "template" mode
    detection_method="hybrid"      # "template"|"geometric"|"contour"|"adaptive"|"hybrid"
)
results = extractor.process_pdf_page(pdf_path="input.pdf", page_num=0, output_dir="temp")
```

Results JSON
```json
{
  "detection_method": "hybrid",
  "total_vacuum_cups": 12,
  "total_coordinates": 40,
  "vacuum_cups": [
    {
      "id": 1,
      "detection_method": "hybrid",
      "center_position": {"x": 123, "y": 456},
      "bounding_box": {"x": 110, "y": 440, "width": 26, "height": 26},
      "coordinates": {"x": "−139.36", "y": "45.5"}
    }
  ],
  "coordinate_labels": [
    {"value": "45.5", "position": {"x": 800, "y": 200}, "axis": "y", "rotation": 90},
    {"value": "−139.36", "position": {"x": 500, "y": 600}, "axis": "x", "rotation": 180}
  ]
}
```

Visualization
- Saved to: `output_dir/visualization_result_{basename}_{detection_method}.png`
- Color-coding by detection method:
  - template: red
  - geometric: blue
  - contour: green
  - adaptive: cyan
  - hybrid: magenta
- X labels: red dots; Y labels: green dots

Dependencies and external modules
- filter_page: cleans a PDF page to an image (module `filter.py`)
- multi_scale_match: template matching utility (module `template_matcher.py`)
- fitz (PyMuPDF) for PDF loading
- scipy.spatial.distance.euclidean (if you extend distance logic)

Paths to check
- In process_pdf_page, `origin_img` points to a local Windows path:
  ```
  C:\Users\a1246807\Plunger_extraction\png\{pdf_basename}.png
  ```
  Adjust to your environment or replace with the cleaned page image if you don't maintain a separate original.

Non-maximum suppression (NMS)
- Duplicate matches are reduced using IoU-based NMS in `_remove_duplicate_matches`.

Nearest-label matching
- Y labels are compared to cup.center_x (after 90° OCR workflow)
- X labels are compared to adjusted y (after 180° OCR workflow)
- Matching uses absolute vertical/horizontal deltas to infer nearest tick/label

---

## run_extraction.py

Purpose
- Example batch runner over a directory of PDFs. Configures detection method and template directory, runs the extractor, and prints per-cup X/Y label matches.

Quick start
```python
from run_extraction import run_extraction
results = run_extraction(detection_method="hybrid")
```

Defaults (change to your local paths):
- pdf_dir: C:\Users\a1246807\Plunger_extraction\pdf
- template_dir: C:\Users\a1246807\Plunger_extraction\templates
- output_dir: extraction_results_{detection_method}

---

## Minimal Usage Examples

Detect cups via hybrid fusion and export results
```python
from coordinate_matcher import VacuumCupCoordinateExtractor

extractor = VacuumCupCoordinateExtractor(detection_method="hybrid")
res = extractor.process_pdf_page("sample.pdf", page_num=0, output_dir="out")
print(res["total_vacuum_cups"], "cups detected")
```

Run OCR only (single image)
```python
import cv2
from extract_axis import ocr_digits

img = cv2.imread("page.png")
ocr = ocr_digits(img, rotations=[0, 90, 180, 270], min_conf=60, threshold_mode="otsu")
for block in ocr:
    for d in block["detections"]:
        print(d["text"], d["bbox"])
```

Use a specific detector (geometric)
```python
from vacuum_cup_detector import GeometricVacuumCupDetector
det = GeometricVacuumCupDetector(min_radius=12, max_radius=22, min_dist=18)
boxes = det.detect_vacuum_cups("page.png")
```

---

## Troubleshooting

- No OCR results
  - Verify Tesseract installation and TESSERACT_CMD env var
  - Try `threshold_mode="adaptive"`, `dpi_boost=1.25`, or enable `deskew=True`
  - Consider increasing `min_conf` or expanding `whitelist`

- Too many false cup detections
  - Geometric: tighten min/max radius; raise param2 in Hough
  - Contour: increase `circularity_threshold` or adjust area bounds
  - Adaptive: raise template `threshold` and add NMS

- Misaligned label matching
  - Ensure rotations used during OCR (90 for Y, 180 for X) match the page orientation
  - Verify `_transform_coordinates_back` and image sizes are correct
  - Use axis_locate.py to confirm rotation/origin mapping visually

- PDF rendering quality
  - The flow uses PyMuPDF + filter_page to rasterize/clean pages. If you use pdf2image, set DPI=300–600.

---

## License

This folder inherits the project’s root license. If none is present, all rights reserved by default.

---
