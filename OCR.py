import os
import re
import json
import glob
import cv2
import numpy as np
import requests
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# ============================================================
# CONFIG
# ============================================================

# OCR.space
API_KEY = "K86395247788957"
OCR_URL = "https://api.ocr.space/parse/image"
OCR_ENGINE = 2

# Input mode:
# - Batch: put images into ./input
# - Single URL test: set TEST_URL below (must be direct image link)
TEST_URL = "https://voicechat.site/image?shortId=K4nzVQq"

# Debug
DEBUG_DIR = "debug_out"
INPUT_DIR = "input"

# Header crop settings
TARGET_W = 1400

OFFSETS = {
    "date":    (-240.5, -49.0, -150.0, 61.0),
    "matches": (-125.5, -14.0,  -66.5, 15.0),
}

TEMPLATE_CANNY_PATH = "template_canny.png"
TEMPLATE_GRAY_PATH  = "template_gray.png"

SEARCH_TOP_FRAC   = 0.35
SEARCH_RIGHT_FRAC = 0.90

COARSE_SCALES = [0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.05, 1.15, 1.25, 1.35]
FINE_DELTAS   = [-0.06, -0.04, -0.02, 0.0, 0.02, 0.04, 0.06]

CANNY1, CANNY2 = 50, 150

THRESH_CANNY = 0.50
THRESH_GRAY  = 0.66

ANCHOR_X_MIN = 0.05
ANCHOR_X_MAX = 0.75
ANCHOR_Y_MIN = 0.00
ANCHOR_Y_MAX = 0.18

TOPK = 15
NMS_RADIUS = 10

# Whitelist
MONTHS = {
    "jan": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr",
    "may": "May", "jun": "Jun", "jul": "Jul", "aug": "Aug",
    "sep": "Sep", "oct": "Oct", "nov": "Nov", "dec": "Dec",
}
DAY_RANGE = (0, 999)
BADGE_RANGE = (0, 999)

# OCR preprocess
OCR_SCALE = 4

# ============================================================
# IO
# ============================================================

def load_image(path: Optional[str], url: Optional[str]) -> np.ndarray:
    if path:
        img = cv2.imread(path)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {path}")
        return img

    if url:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()

        ctype = (r.headers.get("Content-Type") or "").lower()
        if "text/html" in ctype:
            raise RuntimeError("URL returned HTML, not an image. Use a direct image link (png/jpg/webp).")

        data = np.frombuffer(r.content, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            raise RuntimeError("Failed to decode image from URL bytes.")
        return img

    raise ValueError("Provide either path or url.")

# ============================================================
# HEADER CROP (anchor find + union crop)
# ============================================================

def resize_to_target(img_bgr: np.ndarray, target_w: int) -> np.ndarray:
    h, w = img_bgr.shape[:2]
    scale = target_w / w
    new_h = int(round(h * scale))
    return cv2.resize(img_bgr, (target_w, new_h), interpolation=cv2.INTER_CUBIC)

def preprocess_for_mode(region_bgr: np.ndarray, mode: str):
    gray = cv2.cvtColor(region_bgr, cv2.COLOR_BGR2GRAY)
    if mode == "canny":
        return cv2.Canny(gray, CANNY1, CANNY2)
    return gray

def build_fine_scales(s_best: float):
    fine = [s_best + d for d in FINE_DELTAS]
    fine = [s for s in fine if 0.35 <= s <= 1.40]
    fine = sorted(set(round(s, 4) for s in fine))
    return fine

def topk_matches(res: np.ndarray, k: int, nms_radius: int):
    res_work = res.copy()
    out = []
    for _ in range(k):
        _, max_val, _, max_loc = cv2.minMaxLoc(res_work)
        if max_val <= -1e9:
            break
        out.append((float(max_val), (int(max_loc[0]), int(max_loc[1]))))

        x, y = max_loc
        x1 = max(0, x - nms_radius)
        y1 = max(0, y - nms_radius)
        x2 = min(res_work.shape[1], x + nms_radius + 1)
        y2 = min(res_work.shape[0], y + nms_radius + 1)
        res_work[y1:y2, x1:x2] = -1e9
    return out

def run_scales_topk(scales, prepared_region, template_img, method=cv2.TM_CCOEFF_NORMED, topk=TOPK):
    th0, tw0 = template_img.shape[:2]
    candidates = []

    for s in scales:
        tw = int(round(tw0 * s))
        th = int(round(th0 * s))
        if tw < 10 or th < 10:
            continue
        if tw >= prepared_region.shape[1] or th >= prepared_region.shape[0]:
            continue

        templ_s = cv2.resize(template_img, (tw, th), interpolation=cv2.INTER_NEAREST)
        res = cv2.matchTemplate(prepared_region, templ_s, method)

        for sc, loc in topk_matches(res, k=topk, nms_radius=NMS_RADIUS):
            candidates.append({
                "score": sc,
                "loc": loc,
                "tw": tw,
                "th": th,
                "scale": s,
            })

    candidates.sort(key=lambda d: d["score"], reverse=True)
    return candidates

def pick_candidate_with_geometry(cands, x1_region, y1_region, wN, hN):
    for c in cands:
        found_x = x1_region + c["loc"][0]
        found_y = y1_region + c["loc"][1]
        ax = found_x + c["tw"] / 2.0
        ay = found_y + c["th"] / 2.0

        axf = ax / wN
        ayf = ay / hN

        if (ANCHOR_X_MIN <= axf <= ANCHOR_X_MAX) and (ANCHOR_Y_MIN <= ayf <= ANCHOR_Y_MAX):
            return c, ax, ay
    return None, None, None

def find_anchor(img_bgr, template_canny, template_gray):
    img_n = resize_to_target(img_bgr, TARGET_W)
    hN, wN = img_n.shape[:2]

    x1, y1 = 0, 0
    x2 = int(wN * SEARCH_RIGHT_FRAC)
    y2 = int(hN * SEARCH_TOP_FRAC)
    region = img_n[y1:y2, x1:x2]

    # Attempt 1: Canny
    prepared = preprocess_for_mode(region, "canny")
    cands = run_scales_topk(COARSE_SCALES, prepared, template_canny)
    if cands:
        s_best = cands[0]["scale"]
        fine = build_fine_scales(s_best)
        cands = run_scales_topk(fine, prepared, template_canny) + cands
        cands.sort(key=lambda d: d["score"], reverse=True)

        cand, ax, ay = pick_candidate_with_geometry(cands, x1, y1, wN, hN)
        if cand is not None and cand["score"] >= THRESH_CANNY:
            return ax, ay, cand["score"], "canny", img_n, cand

    # Attempt 2: Gray
    prepared = preprocess_for_mode(region, "gray")
    cands = run_scales_topk(COARSE_SCALES, prepared, template_gray)
    if cands:
        s_best = cands[0]["scale"]
        fine = build_fine_scales(s_best)
        cands = run_scales_topk(fine, prepared, template_gray) + cands
        cands.sort(key=lambda d: d["score"], reverse=True)

        cand, ax, ay = pick_candidate_with_geometry(cands, x1, y1, wN, hN)
        if cand is not None and cand["score"] >= THRESH_GRAY:
            return ax, ay, cand["score"], "gray", img_n, cand

    return None, None, None, None, img_n, None

def shift_into_frame(x1, y1, x2, y2, w, h):
    x1 = int(round(x1)); y1 = int(round(y1))
    x2 = int(round(x2)); y2 = int(round(y2))

    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1

    rw = x2 - x1
    rh = y2 - y1
    if rw <= 0 or rh <= 0:
        return None

    if x1 < 0:
        dx = -x1
        x1 += dx; x2 += dx
    if y1 < 0:
        dy = -y1
        y1 += dy; y2 += dy
    if x2 > w:
        dx = x2 - w
        x1 -= dx; x2 -= dx
    if y2 > h:
        dy = y2 - h
        y1 -= dy; y2 -= dy

    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(0, min(x2, w))
    y2 = max(0, min(y2, h))

    if x2 <= x1 or y2 <= y1:
        return None

    return x1, y1, x2, y2

def crop_header_by_anchor(img_n, ax, ay):
    hN, wN = img_n.shape[:2]

    dx1d, dy1d, dx2d, dy2d = OFFSETS["date"]
    dx1m, dy1m, dx2m, dy2m = OFFSETS["matches"]

    cd = shift_into_frame(ax + dx1d, ay + dy1d, ax + dx2d, ay + dy2d, wN, hN)
    cm = shift_into_frame(ax + dx1m, ay + dy1m, ax + dx2m, ay + dy2m, wN, hN)
    if cd is None or cm is None:
        return None, None, (cd, cm)

    x1d, y1d, x2d, y2d = cd
    x1m, y1m, x2m, y2m = cm

    x1 = min(x1d, x1m)
    y1 = min(y1d, y1m)
    x2 = max(x2d, x2m)
    y2 = max(y2d, y2m)

    cu = shift_into_frame(x1, y1, x2, y2, wN, hN)
    if cu is None:
        return None, None, (cd, cm)

    x1, y1, x2, y2 = cu

    header = img_n[y1:y2, x1:x2]
    if header.size == 0:
        return None, None, (cd, cm)

    return header, cu, (cd, cm)

def crop_header(img_bgr: np.ndarray, template_canny, template_gray) -> Tuple[np.ndarray, Dict[str, Any]]:
    ax, ay, sc, mode, img_n, _cand = find_anchor(img_bgr, template_canny, template_gray)
    if ax is None:
        raise RuntimeError("Anchor not found")

    header, header_coords, (cd, cm) = crop_header_by_anchor(img_n, ax, ay)
    if header is None:
        raise RuntimeError(f"Header crop failed: date={cd} matches={cm}")

    meta = {
        "mode": mode,
        "score": float(sc),
        "ax": float(ax),
        "ay": float(ay),
        "header_coords": header_coords,
    }
    return header, meta

# ============================================================
# OCR preprocess + OCR.space + parsing
# ============================================================

def preprocess_for_ocr(header_bgr: np.ndarray, invert: bool, scale: int = OCR_SCALE) -> np.ndarray:
    header_bgr = cv2.resize(header_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(header_bgr, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    if invert:
        bw = 255 - bw

    kernel = np.ones((3, 3), np.uint8)
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel, iterations=1)
    return bw

def ocr_space_file(image_path: str) -> Dict[str, Any]:
    with open(image_path, "rb") as f:
        r = requests.post(
            OCR_URL,
            files={"file": f},
            data={
                "apikey": API_KEY,
                "language": "eng",
                "OCREngine": OCR_ENGINE,
                "scale": True,
                "detectOrientation": False,
                "isOverlayRequired": False,
            },
            timeout=60,
        )
    return r.json()

def parse_month_day_badge(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    t = raw.lower()

    month = None
    for k, v in MONTHS.items():
        if re.search(rf"\b{k}\b", t):
            month = v
            break

    nums = [int(x) for x in re.findall(r"\b\d{1,3}\b", raw)]

    day = next((n for n in nums if DAY_RANGE[0] <= n <= DAY_RANGE[1]), None)

    badge = None
    for n in nums:
        if day is not None and n == day:
            continue
        if BADGE_RANGE[0] <= n <= BADGE_RANGE[1]:
            if day is None or n != day:
                badge = n
                break

    return {"month": month, "day": day, "badge": badge, "raw": raw}

def score_candidate(p: Dict[str, Any]) -> int:
    s = 0
    if p.get("month"): s += 3
    if p.get("day") is not None: s += 2
    if p.get("badge") is not None: s += 2

    raw = p.get("raw", "")
    if raw and "(" not in raw and ")" not in raw:
        s += 1
    return s

def run_ocr_variant(header_bgr: np.ndarray, invert: bool, debug_dir: Optional[str], tag: str):
    processed = preprocess_for_ocr(header_bgr, invert=invert, scale=OCR_SCALE)

    # Persist preprocessed only for debug
    if debug_dir:
        os.makedirs(debug_dir, exist_ok=True)
        dbg_path = os.path.join(debug_dir, f"{tag}_pre_inv_{invert}.png")
        cv2.imwrite(dbg_path, processed)

    with tempfile.TemporaryDirectory() as td:
        out_path = str(Path(td) / f"header_pre_inv_{invert}.png")
        cv2.imwrite(out_path, processed)
        res = ocr_space_file(out_path)

    if res.get("IsErroredOnProcessing"):
        parsed = {"month": None, "day": None, "badge": None, "raw": "", "invert": invert, "error": True}
        return res, parsed

    parsed_results = res.get("ParsedResults", [])
    text = parsed_results[0].get("ParsedText", "") if parsed_results else ""
    parsed = parse_month_day_badge(text)
    parsed["invert"] = invert
    parsed["error"] = False
    return res, parsed

def ocr_header_best(header_bgr: np.ndarray, debug_dir: Optional[str], tag: str) -> Dict[str, Any]:
    _res0, p0 = run_ocr_variant(header_bgr, invert=False, debug_dir=debug_dir, tag=tag)
    _res1, p1 = run_ocr_variant(header_bgr, invert=True,  debug_dir=debug_dir, tag=tag)

    best = p0 if score_candidate(p0) >= score_candidate(p1) else p1
    return {"best": best, "candidates": [p0, p1]}

# ============================================================
# DEBUG CLEANUP: keep only bad cases
# ============================================================

def is_good_result(parsed: Dict[str, Any]) -> bool:
    return (
        not parsed.get("error", False)
        and parsed.get("month") is not None
        and parsed.get("day") is not None
        and parsed.get("badge") is not None
    )

def cleanup_debug_artifacts(debug_dir: str, tag: str) -> None:
    if not debug_dir or not os.path.isdir(debug_dir):
        return

    # Remove preprocessed variants
    for p in glob.glob(os.path.join(debug_dir, f"{tag}_pre_inv_*.png")):
        try:
            os.remove(p)
        except OSError:
            pass

    # Remove header crop
    hp = os.path.join(debug_dir, f"{tag}_header.png")
    if os.path.isfile(hp):
        try:
            os.remove(hp)
        except OSError:
            pass

# ============================================================
# PIPELINE
# ============================================================

def process_one(path: Optional[str], url: Optional[str], debug_dir: str = DEBUG_DIR) -> Dict[str, Any]:
    template_canny = cv2.imread(TEMPLATE_CANNY_PATH, cv2.IMREAD_GRAYSCALE)
    template_gray  = cv2.imread(TEMPLATE_GRAY_PATH,  cv2.IMREAD_GRAYSCALE)
    if template_canny is None or template_gray is None:
        raise RuntimeError("Template(s) not found рядом со скриптом.")

    img = load_image(path, url)

    header, crop_meta = crop_header(img, template_canny, template_gray)

    os.makedirs(debug_dir, exist_ok=True)
    tag = "url" if url else Path(path).stem

    # Save header for debug first
    header_path = os.path.join(debug_dir, f"{tag}_header.png")
    cv2.imwrite(header_path, header)

    ocr_meta = ocr_header_best(header, debug_dir=debug_dir, tag=tag)

    # Keep debug only for bad cases
    best = ocr_meta["best"]
    if is_good_result(best):
        cleanup_debug_artifacts(debug_dir, tag)

    return {
        "input": {"path": path, "url": url},
        "crop": {**crop_meta, "header_path": header_path},
        "ocr": ocr_meta,
    }

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(DEBUG_DIR, exist_ok=True)

    exts = (".png", ".jpg", ".jpeg", ".webp")
    files = [os.path.join(INPUT_DIR, f) for f in os.listdir(INPUT_DIR) if f.lower().endswith(exts)]

    results = []
    ok = 0
    fail = 0

    if files:
        for p in files:
            try:
                res = process_one(path=p, url=None, debug_dir=DEBUG_DIR)
                results.append(res)
                ok += 1
                best = res["ocr"]["best"]
                print(f"OK: {os.path.basename(p)} -> {best} (crop={res['crop']['mode']} score={res['crop']['score']:.3f})")
            except Exception as e:
                fail += 1
                print(f"FAIL: {os.path.basename(p)} -> {e}")

        print(f"Done. OK={ok} FAIL={fail}. Debug in ./{DEBUG_DIR}/")

        with open(os.path.join(DEBUG_DIR, "results.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    else:
        if not TEST_URL:
            print("Put images into ./input or set TEST_URL in the script.")
            raise SystemExit(0)
        
        req = requests.post(TEST_URL)
        url = req.json()["rawUrl"]

        res = process_one(path=None, url=url, debug_dir=DEBUG_DIR)
        print(json.dumps(res, ensure_ascii=False, indent=2))