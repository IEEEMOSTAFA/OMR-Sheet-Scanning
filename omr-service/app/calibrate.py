"""
OMR Sheet Calibration Tool
✅ Camera image support
✅ Auto perspective correction
✅ Dynamic bubble detection
✅ Auto config.py generation

Usage:
    python calibrate.py                        # default image
    python calibrate.py my_omr_photo.jpg       # custom image
"""

import cv2
import numpy as np
import json
import os
import sys
from pathlib import Path


class OMRCalibrator:

    # Target resolution (config.py এর same)
    TARGET_W = 1361
    TARGET_H = 768

    def __init__(self, image_path: str):
        self.image_path = image_path
        raw = cv2.imread(image_path)

        if raw is None:
            raise ValueError(f"❌ Could not load: {image_path}")

        self.original = raw.copy()
        print(f"\n📸 Loaded: {image_path}")
        print(f"   Size: {raw.shape[1]}×{raw.shape[0]} px")

        # ── Auto-enhance camera images ──
        self.is_camera = self._detect_camera(raw)
        if self.is_camera:
            print("   📷 Camera image → enhancing...")
            raw = self._enhance(raw)

        # ── Perspective correction ──
        corrected = self._correct_perspective(raw)

        # ── Normalize to target size ──
        self.image = cv2.resize(
            corrected, (self.TARGET_W, self.TARGET_H),
            interpolation=cv2.INTER_LINEAR
        )
        self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        self.height, self.width = self.image.shape[:2]
        print(f"   Normalized: {self.width}×{self.height} px")

    # ─────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────
    def _detect_camera(self, img: np.ndarray) -> bool:
        gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return lap_var < 500

    def _enhance(self, img: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        return cv2.filter2D(enhanced, -1, kernel)

    def _correct_perspective(self, img: np.ndarray) -> np.ndarray:
        gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges   = cv2.Canny(blurred, 30, 120)
        kernel  = np.ones((3, 3), np.uint8)
        edges   = cv2.dilate(edges, kernel, iterations=1)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return img

        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        for cnt in contours[:10]:
            peri   = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) == 4:
                pts    = approx.reshape(4, 2).astype("float32")
                warped = self._four_point_transform(img, pts)
                print(f"   ✅ Perspective corrected")
                return warped

        print("   ⚠️ Perspective correction skipped")
        return img

    def _four_point_transform(self, img, pts):
        rect = self._order_points(pts)
        tl, tr, br, bl = rect
        w = int(max(
            np.linalg.norm(br - bl),
            np.linalg.norm(tr - tl)
        ))
        h = int(max(
            np.linalg.norm(tr - br),
            np.linalg.norm(tl - bl)
        ))
        dst = np.array([[0,0],[w-1,0],[w-1,h-1],[0,h-1]], dtype="float32")
        M   = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img, M, (w, h))

    def _order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s    = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    # ─────────────────────────────────────────────────────
    # PREPROCESSING
    # ─────────────────────────────────────────────────────
    def preprocess(self) -> np.ndarray:
        blurred = cv2.GaussianBlur(self.gray, (7, 7) if self.is_camera else (5, 5), 0)
        binary  = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            21 if self.is_camera else 15,
            5  if self.is_camera else 3
        )
        kernel  = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        if self.is_camera:
            cleaned = cv2.medianBlur(cleaned, 3)
        return cleaned

    # ─────────────────────────────────────────────────────
    # BUBBLE DETECTION
    # ─────────────────────────────────────────────────────
    def detect_bubbles(self) -> list:
        """সব bubble contour খুঁজে বের করে"""
        processed = self.preprocess()
        contours, _ = cv2.findContours(
            processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        bubbles = []
        areas   = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if not (50 < area < 1500):
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            ar = w / h if h > 0 else 0
            if not (0.6 < ar < 1.4):
                continue

            # Circularity check
            peri = cv2.arcLength(cnt, True)
            circ = 4 * np.pi * area / (peri * peri) if peri > 0 else 0
            if circ < 0.5:
                continue

            bubbles.append({
                "x": x, "y": y, "w": w, "h": h,
                "area": area,
                "cx": x + w // 2,
                "cy": y + h // 2
            })
            areas.append(area)

        print(f"\n🔵 Bubbles found: {len(bubbles)}")
        if areas:
            print(f"   Avg area: {np.mean(areas):.0f}px | Range: {min(areas)}–{max(areas)}")

        return bubbles

    # ─────────────────────────────────────────────────────
    # ID SECTION DETECTION
    # ─────────────────────────────────────────────────────
    def detect_id_section(self, bubbles: list) -> Optional[dict]:
        """
        Student ID grid খুঁজে বের করে।
        সাধারণত image এর উপরের ডান দিকে থাকে।
        """
        if not bubbles:
            return None

        # ডান অর্ধেক + উপরের অর্ধেক এ filter
        right_half = [b for b in bubbles if b["cx"] > self.width // 2]
        top_half   = [b for b in right_half if b["cy"] < self.height // 2]

        if not top_half:
            print("❌ ID section not found in top-right")
            return None

        # Y দিয়ে cluster করি
        ys = sorted(set(b["cy"] for b in top_half))

        # Y cluster (tolerance 10px)
        row_groups = []
        current    = [ys[0]]
        for y in ys[1:]:
            if y - current[-1] < 12:
                current.append(y)
            else:
                row_groups.append(current)
                current = [y]
        row_groups.append(current)

        # 8-10 row এর group চাই (0-9 digits)
        id_groups = [g for g in row_groups if 7 <= len(g) <= 12]

        if not id_groups:
            # fallback: সবচেয়ে বেশি row count এর group
            id_groups = [max(row_groups, key=len)]

        # Y range নির্ধারণ
        all_y = [y for g in id_groups for y in g]
        min_y = min(b["y"] for b in top_half if b["cy"] in all_y) - 5
        max_y = max(b["y"] + b["h"] for b in top_half if b["cy"] in all_y) + 5

        id_bubbles = [b for b in top_half if min_y <= b["y"] <= max_y]
        if not id_bubbles:
            return None

        min_x = min(b["x"] for b in id_bubbles)
        max_x = max(b["x"] + b["w"] for b in id_bubbles)

        # Unique columns
        xs = sorted(set(b["cx"] for b in id_bubbles))
        col_groups = []
        cur = [xs[0]]
        for x in xs[1:]:
            if x - cur[-1] < 15:
                cur.append(x)
            else:
                col_groups.append(int(np.mean(cur)))
                cur = [x]
        col_groups.append(int(np.mean(cur)))

        num_digits   = len(col_groups)
        num_rows     = len(id_groups)
        digit_width  = max(1, (max_x - min_x) // max(num_digits, 1))
        digit_height = max(1, (max_y - min_y)  // max(num_rows, 1))
        row_spacing  = digit_height

        print(f"\n🆔 ID Section:")
        print(f"   Position : ({min_x}, {min_y})")
        print(f"   Columns  : {num_digits}")
        print(f"   Rows     : {num_rows}")
        print(f"   Col X    : {col_groups}")

        return {
            "x"           : min_x,
            "y"           : min_y,
            "width"       : max_x - min_x,
            "height"      : max_y - min_y,
            "num_digits"  : num_digits,
            "digit_width" : digit_width,
            "digit_height": digit_height,
            "row_spacing" : row_spacing,
            "options"     : num_rows,
            "col_x"       : col_groups,
        }

    # ─────────────────────────────────────────────────────
    # ANSWER SECTION DETECTION
    # ─────────────────────────────────────────────────────
    def detect_answer_section(self, bubbles: list, id_section: Optional[dict]) -> Optional[dict]:
        """
        Q1-Q20 এর bubble grid detect করে।
        """
        if not bubbles:
            return None

        id_bottom = (id_section["y"] + id_section["height"] + 30) if id_section else 300
        ans_bubbles = [b for b in bubbles if b["y"] > id_bottom]

        if not ans_bubbles:
            print("❌ Answer section not found")
            return None

        # ── Row clustering (Y দিয়ে) ──
        ys = sorted(set(b["cy"] for b in ans_bubbles))
        row_groups = []
        cur = [ys[0]]
        for y in ys[1:]:
            if y - cur[-1] < 15:
                cur.append(y)
            else:
                row_groups.append(cur)
                cur = [y]
        row_groups.append(cur)

        row_centers = [int(np.mean(g)) for g in row_groups]
        row_centers = sorted(row_centers)

        # ── Column clustering (X দিয়ে) ──
        xs = sorted(set(b["cx"] for b in ans_bubbles))
        col_groups = []
        cur = [xs[0]]
        for x in xs[1:]:
            if x - cur[-1] < 20:
                cur.append(x)
            else:
                col_groups.append(int(np.mean(cur)))
                cur = [x]
        col_groups.append(int(np.mean(cur)))

        # Image মাঝ বরাবর split করি
        mid_x   = self.width // 2
        left_xs = sorted([x for x in col_groups if x < mid_x])
        right_xs= sorted([x for x in col_groups if x >= mid_x])

        # 4 option X positions
        if len(left_xs) >= 4:
            left_option_x = left_xs[:4]
        else:
            left_option_x = left_xs

        if len(right_xs) >= 4:
            right_option_x = right_xs[:4]
        else:
            right_option_x = right_xs

        # Row Y: প্রথম 10 = Q1-10, পরের 10 = Q11-20
        # (সাধারণত দুই column এ একই Y)
        if len(row_centers) >= 10:
            row_y = row_centers[:10]
        else:
            # Spacing extrapolate করি
            if len(row_centers) >= 2:
                spacing = int(np.mean(np.diff(row_centers)))
            else:
                spacing = 40
            row_y = list(row_centers)
            while len(row_y) < 10:
                row_y.append(row_y[-1] + spacing)

        # Bubble size
        sample    = ans_bubbles[:30]
        avg_w     = int(np.mean([b["w"] for b in sample]))
        avg_h     = int(np.mean([b["h"] for b in sample]))

        print(f"\n📝 Answer Section:")
        print(f"   Left  option X : {left_option_x}")
        print(f"   Right option X : {right_option_x}")
        print(f"   Row Y (10)     : {row_y}")
        print(f"   Bubble size    : {avg_w}×{avg_h}")

        return {
            "left_option_x" : left_option_x,
            "right_option_x": right_option_x,
            "row_y"         : row_y,
            "bubble_width"  : avg_w,
            "bubble_height" : avg_h,
        }

    # ─────────────────────────────────────────────────────
    # FULL CALIBRATION
    # ─────────────────────────────────────────────────────
    def run_full_calibration(self) -> Optional[dict]:
        print("\n" + "="*60)
        print("🚀 FULL CALIBRATION START")
        print("="*60)

        bubbles = self.detect_bubbles()
        if not bubbles:
            print("❌ No bubbles detected! Check image quality.")
            return None

        id_section  = self.detect_id_section(bubbles)
        ans_section = self.detect_answer_section(bubbles, id_section)

        if not ans_section:
            print("❌ Answer section not detected!")
            return None

        # ── Build config ──
        config = self._build_config(id_section, ans_section)

        # ── Save files ──
        self._save_json(config)
        self._save_python_config(config)
        self._save_visualization(bubbles, id_section, ans_section)

        print("\n" + "="*60)
        print("✅ CALIBRATION COMPLETE!")
        print("="*60)
        print("\n📁 Files generated:")
        print("   1. omr_configuration.json  — Full config JSON")
        print("   2. config_calibrated.py    — Python config (copy → app/config.py)")
        print("   3. calibrated_output.jpg   — Visual verification")
        print("\n📝 Next steps:")
        print("   1. Open 'calibrated_output.jpg' → check detected areas")
        print("   2. Copy 'config_calibrated.py' → 'app/config.py'")
        print("   3. Test with: python test_omr.py")

        return config

    def _build_config(self, id_sec, ans_sec) -> dict:
        """Detected values থেকে config dict তৈরি করে"""
        return {
            "PREPROCESS": {
                "blur_kernel"          : [5, 5],
                "threshold_block_size" : 21 if self.is_camera else 15,
                "threshold_constant"   : 5  if self.is_camera else 3,
                "min_bubble_area"      : 150,
                "max_bubble_area"      : 1200,
                "aspect_ratio_min"     : 0.6,
                "aspect_ratio_max"     : 1.4,
            },
            "STUDENT_ID": id_sec if id_sec else {
                "x": 790, "y": 148, "width": 430, "height": 210,
                "num_digits": 8, "digit_width": 54, "digit_height": 21,
                "row_spacing": 21, "options": 10,
                "col_x": [794, 848, 900, 955, 1009, 1065, 1120, 1175],
            },
            "THRESHOLDS": {
                "min_black_pixels"   : 25 if self.is_camera else 35,
                "fill_threshold_pct" : 0.10 if self.is_camera else 0.13,
                "max_black_pixels"   : 700,
                "fill_ratio"         : 0.38,
                "confidence_threshold": 0.60 if self.is_camera else 0.65,
                "darkness_threshold" : 120 if self.is_camera else 100,
                "sample_radius"      : 8,
            },
            "LEFT_COLUMN": {
                "option_x"     : ans_sec["left_option_x"],
                "row_y"        : ans_sec["row_y"],
                "bubble_width" : ans_sec["bubble_width"],
                "bubble_height": ans_sec["bubble_height"],
            },
            "RIGHT_COLUMN": {
                "option_x"     : ans_sec["right_option_x"],
                "row_y"        : ans_sec["row_y"],
                "bubble_width" : ans_sec["bubble_width"],
                "bubble_height": ans_sec["bubble_height"],
            },
            "ANSWERS" : {"total_questions": 20, "options_per_q": 4},
            "GRADING" : {
                "marks_per_question": 1,
                "negative_marking"  : False,
                "negative_marks"    : 0.25,
            },
        }

    def _save_json(self, config: dict):
        with open("omr_configuration.json", "w") as f:
            json.dump(config, f, indent=2)
        print("\n💾 Saved: omr_configuration.json")

    def _save_python_config(self, config: dict):
        c  = config
        id = c["STUDENT_ID"]
        lc = c["LEFT_COLUMN"]
        rc = c["RIGHT_COLUMN"]
        th = c["THRESHOLDS"]

        code = f'''"""
Auto-generated OMR Configuration
Generated by calibrate.py
Image type: {"Camera/Phone" if self.is_camera else "Clean/Digital"}
Target size: {self.TARGET_W} × {self.TARGET_H}
"""

class OMRConfig:

    PREPROCESS = {{
        "blur_kernel"          : {c["PREPROCESS"]["blur_kernel"]},
        "threshold_block_size" : {c["PREPROCESS"]["threshold_block_size"]},
        "threshold_constant"   : {c["PREPROCESS"]["threshold_constant"]},
        "min_bubble_area"      : {c["PREPROCESS"]["min_bubble_area"]},
        "max_bubble_area"      : {c["PREPROCESS"]["max_bubble_area"]},
        "aspect_ratio_min"     : {c["PREPROCESS"]["aspect_ratio_min"]},
        "aspect_ratio_max"     : {c["PREPROCESS"]["aspect_ratio_max"]},
    }}

    STUDENT_ID = {{
        "x"           : {id["x"]},
        "y"           : {id["y"]},
        "width"       : {id.get("width", 430)},
        "height"      : {id.get("height", 210)},
        "num_digits"  : {id["num_digits"]},
        "digit_width" : {id["digit_width"]},
        "digit_height": {id["digit_height"]},
        "row_spacing" : {id.get("row_spacing", id["digit_height"])},
        "options"     : {id["options"]},
        "col_x"       : {id.get("col_x", [])},
    }}

    THRESHOLDS = {{
        "min_black_pixels"    : {th["min_black_pixels"]},
        "fill_threshold_pct"  : {th["fill_threshold_pct"]},
        "max_black_pixels"    : {th["max_black_pixels"]},
        "fill_ratio"          : {th["fill_ratio"]},
        "confidence_threshold": {th["confidence_threshold"]},
        "darkness_threshold"  : {th["darkness_threshold"]},
        "sample_radius"       : {th["sample_radius"]},
    }}

    LEFT_COLUMN = {{
        "option_x"     : {lc["option_x"]},
        "row_y"        : {lc["row_y"]},
        "bubble_width" : {lc["bubble_width"]},
        "bubble_height": {lc["bubble_height"]},
    }}

    RIGHT_COLUMN = {{
        "option_x"     : {rc["option_x"]},
        "row_y"        : {rc["row_y"]},
        "bubble_width" : {rc["bubble_width"]},
        "bubble_height": {rc["bubble_height"]},
    }}

    ANSWERS = {{
        "total_questions": {c["ANSWERS"]["total_questions"]},
        "options_per_q"  : {c["ANSWERS"]["options_per_q"]},
    }}

    GRADING = {{
        "marks_per_question": {c["GRADING"]["marks_per_question"]},
        "negative_marking"  : {c["GRADING"]["negative_marking"]},
        "negative_marks"    : {c["GRADING"]["negative_marks"]},
    }}


if __name__ == "__main__":
    c = OMRConfig()
    print("LEFT  X:", c.LEFT_COLUMN["option_x"])
    print("RIGHT X:", c.RIGHT_COLUMN["option_x"])
    print("ROW   Y:", c.LEFT_COLUMN["row_y"])
'''
        with open("config_calibrated.py", "w") as f:
            f.write(code)
        print("💾 Saved: config_calibrated.py")

    def _save_visualization(self, bubbles, id_sec, ans_sec):
        vis = self.image.copy()

        # All bubbles → yellow dots
        for b in bubbles:
            cv2.circle(vis, (b["cx"], b["cy"]), 3, (0, 255, 255), -1)

        # ID section → blue box
        if id_sec:
            cv2.rectangle(vis,
                (id_sec["x"], id_sec["y"]),
                (id_sec["x"] + id_sec.get("width", 300),
                 id_sec["y"] + id_sec.get("height", 210)),
                (255, 0, 0), 2)
            cv2.putText(vis, "ID SECTION",
                (id_sec["x"], id_sec["y"] - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)

        # Answer bubbles → green boxes
        if ans_sec:
            for col_xs in [ans_sec["left_option_x"], ans_sec["right_option_x"]]:
                for row_y in ans_sec["row_y"]:
                    for x in col_xs:
                        cv2.rectangle(vis,
                            (x, row_y),
                            (x + ans_sec["bubble_width"], row_y + ans_sec["bubble_height"]),
                            (0, 255, 0), 1)

        # Info overlay
        for i, txt in enumerate([
            f"Bubbles: {len(bubbles)}",
            f"Size: {self.width}x{self.height}",
            f"Type: {'Camera' if self.is_camera else 'Clean'}",
        ]):
            cv2.putText(vis, txt, (10, 25 + i * 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        cv2.imwrite("calibrated_output.jpg", vis)
        print("💾 Saved: calibrated_output.jpg")


# ─────────────────────────────────────────────────────────
# Optional type import fix
# ─────────────────────────────────────────────────────────
from typing import Optional


def auto_calibrate(image_path: str) -> Optional[dict]:
    """Quick one-call calibration"""
    try:
        cal = OMRCalibrator(image_path)
        return cal.run_full_calibration()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("="*60)
    print("🎯 OMR CALIBRATION TOOL")
    print("="*60)

    # Command-line argument দিলে সেটা use করো
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Default image খোঁজো
        defaults = [
            "test_images/Perfect_image3.png",
            "../test_images/Perfect_image3.png",
            "test_images/sample_omr.jpg",
            "Perfect_image3.png",
        ]
        image_path = None
        for p in defaults:
            if os.path.exists(p):
                image_path = p
                print(f"   Default image: {p}")
                break

        if not image_path:
            image_path = input("📁 Image path দাও: ").strip()

    if not os.path.exists(image_path):
        print(f"❌ File not found: {image_path}")
        return

    auto_calibrate(image_path)


if __name__ == "__main__":
    main()



