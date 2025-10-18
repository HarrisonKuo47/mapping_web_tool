import os
import cv2
import numpy as np
import pytesseract
from typing import Dict, List, Tuple, Any, Optional
from pdf2image import convert_from_path
from PIL import Image

def _set_tesseract_cmd_from_env():
    cmd = os.environ.get("TESSERACT_CMD")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd

def load_image(path: str) -> np.ndarray:
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    return img

def _resize_for_dpi(img: np.ndarray, scale: float) -> np.ndarray:
    if scale is None or abs(scale - 1.0) < 1e-3:
        return img
    h, w = img.shape[:2]
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

def _deskew(img_gray: np.ndarray) -> Tuple[np.ndarray, float]:
    # Estimate skew using Hough line transform on edges
    edges = cv2.Canny(img_gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180.0, threshold=200)
    if lines is None or len(lines) == 0:
        return img_gray, 0.0

    angles = []
    for rho, theta in lines[:, 0]:
        angle = (theta * 180.0 / np.pi) - 90.0
        # Normalize angle to [-45, 45] to avoid vertical bias
        if angle < -45:
            angle += 90
        elif angle > 45:
            angle -= 90
        angles.append(angle)

    if not angles:
        return img_gray, 0.0

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5:
        return img_gray, 0.0

    h, w = img_gray.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(img_gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated, median_angle

def _remove_long_lines(bin_img: np.ndarray, line_kernel_scale: float = 0.02) -> np.ndarray:
    # bin_img is expected to be 0/255 (text=white on black bg after threshold inversion)
    h, w = bin_img.shape[:2]
    # Horizontal lines
    hor_kernel_len = max(10, int(w * line_kernel_scale))
    hor_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (hor_kernel_len, 1))
    # Vertical lines
    ver_kernel_len = max(10, int(h * line_kernel_scale))
    ver_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, ver_kernel_len))

    remove_h = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, hor_kernel, iterations=1)
    remove_v = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, ver_kernel, iterations=1)

    lines = cv2.bitwise_or(remove_h, remove_v)
    cleaned = cv2.subtract(bin_img, lines)
    return cleaned

def preprocess(
    img_bgr: np.ndarray,
    threshold_mode: str = "otsu",
    dpi_boost: float = 1.0,
    remove_lines: bool = True,
    deskew: bool = False,
    line_kernel_scale: float = 0.02,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    # 1) scale
    img = _resize_for_dpi(img_bgr, dpi_boost)

    # 2) grayscale + denoise
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Preserve edges while denoising
    gray = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)

    # 3) (optional) deskew
    angle = 0.0
    if deskew:
        gray, angle = _deskew(gray)

    # 4) thresholding
    if threshold_mode == "adaptive":
        th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 35, 15)
    else:
        # Otsu
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Invert so that text is white on black (better for line removal subtract)
    th_inv = 255 - th

    # 5) remove long lines (dimension lines, gridlines)
    if remove_lines:
        th_inv = _remove_long_lines(th_inv, line_kernel_scale=line_kernel_scale)

    # Optional light morphology close to connect broken strokes
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    th_inv = cv2.morphologyEx(th_inv, cv2.MORPH_CLOSE, kernel, iterations=1)

    # Back to normal white background for Tesseract (black text)
    prepped = 255 - th_inv
    return prepped, {"deskew_angle": angle, "scale": dpi_boost}

def _rotate_image_keep_size(img: np.ndarray, angle: int) -> np.ndarray:
    angle = angle % 360
    if angle == 0:
        return img
    if angle == 90:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    if angle == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    if angle == 270:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    # Fallback arbitrary angle (shouldn't happen here)
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

def _remap_bbox_from_rotated(bbox: Tuple[int, int, int, int], angle: int, orig_w: int, orig_h: int) -> Tuple[int, int, int, int]:
    # bbox: (x, y, w, h) in rotated image coordinate
    x, y, w, h = bbox
    angle = angle % 360
    if angle == 0:
        return x, y, w, h
    if angle == 90:
        # Rotated clockwise: (x',y') -> (orig_x, orig_y) = (orig_w - (y+h), x)
        new_x = orig_w - (y + h)
        new_y = x
        return new_x, new_y, h, w
    if angle == 180:
        new_x = orig_w - (x + w)
        new_y = orig_h - (y + h)
        return new_x, new_y, w, h
    if angle == 270:
        # Rotated counter-clockwise when mapping back from 90CCW equivalent
        new_x = y
        new_y = orig_h - (x + w)
        return new_x, new_y, h, w
    # For arbitrary angles, skip remap (not used here)
    return x, y, w, h

def _parse_tesseract_data(data: str) -> List[Dict[str, Any]]:
    # Parse TSV returned by image_to_data
    lines = data.strip().splitlines()
    if not lines:
        return []
    header = lines[0].split("\t")
    idx_map = {name: i for i, name in enumerate(header)}
    out = []
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) != len(header):
            continue
        try:
            text = parts[idx_map["text"]].strip()
            conf = int(float(parts[idx_map["conf"]]))
            left = int(parts[idx_map["left"]])
            top = int(parts[idx_map["top"]])
            width = int(parts[idx_map["width"]])
            height = int(parts[idx_map["height"]])
        except Exception:
            continue
        out.append({
            "text": text,
            "conf": conf,
            "bbox": (left, top, width, height),
        })
    return out

def _is_numeric_text(s: str) -> bool:
    if not s:
        return False
    # Keep nums with optional +/-, decimal, slash (for fractions), and spaces trimmed away
    allowed = set("0123456789+-. /")
    return all(ch in allowed for ch in s)

def ocr_digits(
    img_bgr: np.ndarray,
    rotations: List[int] = [0, 90, 180, 270],
    min_conf: int = 55,
    tesseract_psm: int = 6,
    whitelist: str = "0123456789+-./",
    threshold_mode: str = "otsu",
    dpi_boost: float = 1.0,
    remove_lines: bool = True,
    deskew: bool = False,
    line_kernel_scale: float = 0.02,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    _set_tesseract_cmd_from_env()

    prepped, meta = preprocess(
        img_bgr,
        threshold_mode=threshold_mode,
        dpi_boost=dpi_boost,
        remove_lines=remove_lines,
        deskew=deskew,
        line_kernel_scale=line_kernel_scale,
    )
    H, W = prepped.shape[:2]
    results = []

    for angle in rotations:
        rotated = _rotate_image_keep_size(prepped, angle)
        config = f"--oem 3 --psm {tesseract_psm} -c tessedit_char_whitelist={whitelist}"
        data = pytesseract.image_to_data(rotated, output_type=pytesseract.Output.STRING, config=config, lang="eng")
        entries = _parse_tesseract_data(data)

        dets = []
        for e in entries:
            text = e["text"].strip()
            conf = e["conf"]
            if conf < min_conf:
                continue
            if not _is_numeric_text(text):
                continue
            # Normalize whitespace and leading/trailing punctuation
            norm = text.replace(" ", "")
            # Discard if empty or just punctuation
            if not any(ch.isdigit() for ch in norm):
                continue

            x, y, w, h = e["bbox"]
            # map bbox back to original orientation
            bx, by, bw, bh = _remap_bbox_from_rotated((x, y, w, h), angle, W, H)
            dets.append({
                "text": norm,
                "conf": conf,
                "bbox": [int(bx), int(by), int(bw), int(bh)],
            })
            if verbose:
                print(f"[angle={angle}] '{norm}' conf={conf} bbox={bx,by,bw,bh}")

        if dets:
            results.append({
                "rotation": angle,
                "deskew_angle": meta.get("deskew_angle", 0.0),
                "scale": meta.get("scale", 1.0),
                "detections": dets,
            })

    return results

def pdf_to_images(pdf_path: str, dpi: int = 300) -> List[np.ndarray]:
    pages = convert_from_path(pdf_path, dpi=dpi)
    imgs = []
    for p in pages:
        # convert PIL Image to OpenCV BGR
        rgb = np.array(p)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        imgs.append(bgr)
    return imgs

def run_on_path(
    path: str,
    **kwargs,
) -> List[Dict[str, Any]]:
    outputs = []
    if os.path.isdir(path):
        for root, _, files in os.walk(path):
            for fn in sorted(files):
                fpath = os.path.join(root, fn)
                lower = fn.lower()
                try:
                    if lower.endswith(".pdf"):
                        images = pdf_to_images(fpath, dpi=300)
                        for i, img in enumerate(images):
                            res = ocr_digits(img, **kwargs)
                            outputs.append({"source": f"{fpath}#page={i+1}", "results": res})
                    elif any(lower.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"]):
                        img = load_image(fpath)
                        res = ocr_digits(img, **kwargs)
                        outputs.append({"source": fpath, "results": res})
                except Exception as e:
                    outputs.append({"source": fpath, "error": str(e)})
    else:
        lower = path.lower()
        if lower.endswith(".pdf"):
            images = pdf_to_images(path, dpi=300)
            for i, img in enumerate(images):
                res = ocr_digits(img, **kwargs)
                outputs.append({"source": f"{path}#page={i+1}", "results": res})
        else:
            img = load_image(path)
            res = ocr_digits(img, **kwargs)
            outputs.append({"source": path, "results": res})

    return outputs