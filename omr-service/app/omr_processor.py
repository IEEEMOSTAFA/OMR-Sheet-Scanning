# """
# OMR Processor — Handwritten MCQ Answer Sheet
# ==============================================
# ✅ Grayscale darkness detection (works on clear phone-camera photos)
# ✅ Auto-scaling for different resolutions of the SAME sheet design
# ✅ CLAHE enhancement for uneven lighting
# ✅ Student ID extraction
# ✅ Left column Q1-Q10 | Right column Q11-Q20

# Detection:
#   filled bubble  → grayscale mean ≈ 30–70
#   unfilled       → grayscale mean ≈ 130–200
#   darkest bubble = selected answer
#   diff < threshold → blank
# """

# import cv2
# import numpy as np
# from typing import Dict, List, Optional, Tuple

# try:
#     from app.config import OMRConfig
#     from app.utils import OMRUtils
# except ImportError:
#     from config import OMRConfig
#     try:
#         from utils import OMRUtils
#     except ImportError:
#         OMRUtils = None


# class OMRProcessor:

#     def __init__(self):
#         self.config = OMRConfig
#         self.utils  = OMRUtils

#         print("=" * 60)
#         print("   OMR Processor v2.1 — Phone Camera Support")
#         print(f"   Total Questions : {self.config.ANSWERS['total_questions']}")
#         print(f"   Left  X (A-D)  : {self.config.LEFT_COLUMN['option_x']}")
#         print(f"   Right X (A-D)  : {self.config.RIGHT_COLUMN['option_x']}")
#         print(f"   Base resolution: {self.config.BASE_WIDTH}×{self.config.BASE_HEIGHT}")
#         print(f"   Method         : {self.config.THRESHOLDS['detection_method']}")
#         print("=" * 60)

#     # ─────────────────────────────────────────────────────────────
#     # MAIN ENTRY
#     # ─────────────────────────────────────────────────────────────
#     def process_image(
#         self,
#         image_bytes: bytes,
#         apply_perspective: bool = False,
#         debug: bool = False
#     ) -> Dict:
#         try:
#             nparr = np.frombuffer(image_bytes, np.uint8)
#             image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#             if image is None:
#                 return {"success": False, "error": "Image decode failed"}

#             orig_h, orig_w = image.shape[:2]
#             print(f"\n{'='*60}")
#             print(f"📥 Image: {orig_w}×{orig_h} px")

#             is_cam = self._is_camera_image(image)
#             if is_cam:
#                 print("   📷 Camera image → CLAHE enhance...")
#                 image = self._enhance_camera_image(image)

#             if apply_perspective and self.utils is not None:
#                 try:
#                     print("   🔄 Perspective correction...")
#                     image = self.utils.correct_perspective(image)
#                 except Exception as e:
#                     print(f"   ⚠️ Perspective skipped: {e}")

#             curr_h, curr_w = image.shape[:2]
#             sx = curr_w / float(self.config.BASE_WIDTH)
#             sy = curr_h / float(self.config.BASE_HEIGHT)
#             print(f"   📐 Scale: sx={sx:.3f}, sy={sy:.3f}")

#             gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#             blur_k = self.config.PREPROCESS.get("blur_kernel", (5, 5))
#             gray_blur = cv2.GaussianBlur(gray, blur_k, 0)

#             if debug:
#                 cv2.imwrite("debug_gray.png", gray_blur)

#             student_id = self._extract_student_id(gray_blur, sx, sy, debug=debug)
#             print(f"   🎓 Student ID: {student_id}")

#             answers = self._extract_answers(gray_blur, sx, sy, debug=debug)

#             answered = sum(1 for a in answers if a is not None)
#             blank    = self.config.ANSWERS["total_questions"] - answered

#             print(f"   📊 Answered: {answered}/{self.config.ANSWERS['total_questions']}")
#             print(f"{'='*60}\n")

#             return {
#                 "success"         : True,
#                 "student_id"      : student_id,
#                 "answers"         : answers,
#                 "total_answered"  : answered,
#                 "total_blank"     : blank,
#                 "total_questions" : self.config.ANSWERS["total_questions"],
#                 "image_type"      : "camera" if is_cam else "scanned",
#                 "confidence"      : round(answered / self.config.ANSWERS["total_questions"], 2),
#             }

#         except Exception as e:
#             import traceback
#             traceback.print_exc()
#             return {"success": False, "error": str(e)}

#     # ─────────────────────────────────────────────────────────────
#     # BUBBLE READER — lower mean = darker = filled
#     # ─────────────────────────────────────────────────────────────
#     def _read_bubble_darkness(
#         self,
#         gray: np.ndarray,
#         cx: int,
#         cy: int,
#         radius: int
#     ) -> float:
#         shrink = self.config.THRESHOLDS.get("sample_radius_shrink", 3)
#         sample_r = max(radius - shrink, 4)

#         h, w = gray.shape[:2]
#         cx = int(np.clip(cx, 0, w - 1))
#         cy = int(np.clip(cy, 0, h - 1))

#         mask = np.zeros(gray.shape, dtype="uint8")
#         cv2.circle(mask, (cx, cy), sample_r, 255, -1)
#         return cv2.mean(gray, mask=mask)[0]

#     def _select_answer_from_row(
#         self,
#         gray: np.ndarray,
#         bubble_centers: List[Tuple[int, int]],
#         radius: int,
#         options: List[str]
#     ) -> Optional[str]:
#         threshold = self.config.THRESHOLDS.get("darkness_diff_threshold", 30)

#         values = [
#             self._read_bubble_darkness(gray, cx, cy, radius)
#             for cx, cy in bubble_centers
#         ]

#         min_val = min(values)
#         max_val = max(values)
#         diff = max_val - min_val

#         if diff < threshold:
#             return None

#         return options[values.index(min_val)]

#     # ─────────────────────────────────────────────────────────────
#     # ANSWERS Q1–Q20
#     # ─────────────────────────────────────────────────────────────
#     def _extract_answers(
#         self,
#         gray: np.ndarray,
#         sx: float,
#         sy: float,
#         debug: bool = False
#     ) -> List[Optional[str]]:
#         options     = ['A', 'B', 'C', 'D']
#         all_answers = [None] * self.config.ANSWERS["total_questions"]

#         def _read_column(col_cfg: dict, q_offset: int, label: str):
#             print(f"\n   📝 {label}:")
#             scaled_x = [int(x * sx) for x in col_cfg["option_x"]]
#             radius   = max(int(col_cfg.get("bubble_radius", 12) * min(sx, sy)), 6)

#             for q_idx, base_y in enumerate(col_cfg["row_y"]):
#                 q_num    = q_idx + q_offset
#                 scaled_y = int(base_y * sy)
#                 centers  = [(x, scaled_y) for x in scaled_x]

#                 dark_vals = [
#                     self._read_bubble_darkness(gray, cx, cy, radius)
#                     for cx, cy in centers
#                 ]
#                 answer = self._select_answer_from_row(gray, centers, radius, options)
#                 all_answers[q_num - 1] = answer
#                 status = answer if answer else "---"
#                 print(f"      Q{q_num:2d}: dark={[f'{v:.0f}' for v in dark_vals]} → {status}")

#         _read_column(self.config.LEFT_COLUMN,  1,  "LEFT  COLUMN (Q1-Q10)")
#         _read_column(self.config.RIGHT_COLUMN, 11, "RIGHT COLUMN (Q11-Q20)")

#         if debug:
#             self._draw_debug(gray, all_answers, sx, sy)
#         return all_answers

#     # ─────────────────────────────────────────────────────────────
#     # STUDENT ID
#     # ─────────────────────────────────────────────────────────────
#     def _extract_student_id(
#         self,
#         gray: np.ndarray,
#         sx: float,
#         sy: float,
#         debug: bool = False
#     ) -> str:
#         id_cfg = self.config.STUDENT_ID
#         digits = []
#         options_count = id_cfg.get("options", 10)

#         print(f"\n   📖 Extracting Student ID...")

#         for col in range(id_cfg["num_digits"]):
#             col_x_list = id_cfg.get("col_x", None)
#             if col_x_list and col < len(col_x_list):
#                 col_x = int(col_x_list[col] * sx)
#             else:
#                 col_x = int((id_cfg["x"] + col * id_cfg["digit_width"]) * sx)

#             darkness_vals = []
#             row_spacing = int(id_cfg.get("row_spacing", id_cfg["digit_height"]) * sy)
#             d_height    = max(int(id_cfg["digit_height"] * sy), 8)
#             d_width     = max(int(id_cfg["digit_width"] * sx), 10)

#             for row in range(options_count):
#                 y_pos = int(id_cfg["y"] * sy) + row * row_spacing
#                 y1 = max(0, y_pos)
#                 y2 = min(gray.shape[0], y_pos + d_height)
#                 x1 = max(0, col_x - d_width // 2)
#                 x2 = min(gray.shape[1], col_x + d_width // 2)

#                 roi = gray[y1:y2, x1:x2]
#                 if roi.size < 10:
#                     darkness_vals.append(255.0)
#                 else:
#                     darkness_vals.append(float(np.mean(roi)))

#             min_val = min(darkness_vals)
#             max_val = max(darkness_vals)
#             diff    = max_val - min_val
#             threshold = self.config.THRESHOLDS.get("darkness_diff_threshold", 30)

#             if diff >= threshold:
#                 selected = str(darkness_vals.index(min_val))
#                 print(f"      Col {col+1}: ✅ {selected}  (dark={min_val:.0f}, diff={diff:.0f})")
#             else:
#                 selected = "?"
#                 print(f"      Col {col+1}: ❌ blank  (diff={diff:.0f})")
#             digits.append(selected)

#         return "".join(digits)

#     # ─────────────────────────────────────────────────────────────
#     # GRADING
#     # ─────────────────────────────────────────────────────────────
#     def grade_exam(self, student_answers: List, answer_key: Dict) -> Dict:
#         correct = wrong = blank = 0
#         details = []
#         grading = self.config.GRADING

#         for i, student_ans in enumerate(student_answers):
#             q_num = str(i + 1)
#             correct_ans = answer_key.get(q_num)

#             if student_ans is None:
#                 blank += 1
#                 details.append({
#                     "question": i + 1, "student": None,
#                     "correct": correct_ans, "status": "blank", "marks": 0
#                 })
#             elif student_ans == correct_ans:
#                 correct += 1
#                 details.append({
#                     "question": i + 1, "student": student_ans,
#                     "correct": correct_ans, "status": "correct",
#                     "marks": grading["marks_per_question"]
#                 })
#             else:
#                 wrong += 1
#                 neg = grading["negative_marks"] if grading["negative_marking"] else 0
#                 details.append({
#                     "question": i + 1, "student": student_ans,
#                     "correct": correct_ans, "status": "wrong", "marks": -neg
#                 })

#         total_q = len(answer_key)
#         raw_marks = correct * grading["marks_per_question"]
#         if grading["negative_marking"]:
#             raw_marks -= wrong * grading["negative_marks"]
#         raw_marks = max(raw_marks, 0)
#         percentage = (raw_marks / total_q * 100) if total_q > 0 else 0

#         if   percentage >= 80: grade = "A+"
#         elif percentage >= 70: grade = "A"
#         elif percentage >= 60: grade = "A-"
#         elif percentage >= 50: grade = "B"
#         elif percentage >= 40: grade = "C"
#         elif percentage >= 33: grade = "D"
#         else: grade = "F"

#         print(f"\n   🏆 {correct}/{total_q} correct | {percentage:.1f}% | Grade: {grade}")
#         return {
#             "correct": correct, "wrong": wrong, "blank": blank, "total": total_q,
#             "raw_marks": raw_marks, "percentage": round(percentage, 1),
#             "grade": grade, "details": details,
#         }

#     # ─────────────────────────────────────────────────────────────
#     # HELPERS
#     # ─────────────────────────────────────────────────────────────
#     def _is_camera_image(self, image: np.ndarray) -> bool:
#         gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#         laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
#         h, w = image.shape[:2]
#         return (w > 2000 or h > 2000) or laplacian_var < 5000

#     def _enhance_camera_image(self, image: np.ndarray) -> np.ndarray:
#         lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
#         l, a, b = cv2.split(lab)
#         clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
#         l_enhanced = clahe.apply(l)
#         return cv2.cvtColor(cv2.merge([l_enhanced, a, b]), cv2.COLOR_LAB2BGR)

#     def _draw_debug(
#         self,
#         gray: np.ndarray,
#         answers: List[Optional[str]],
#         sx: float,
#         sy: float,
#         output_path: str = "debug_answers.png"
#     ):
#         color_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
#         options = ['A', 'B', 'C', 'D']

#         def _draw_column(col_cfg, q_offset):
#             scaled_x = [int(x * sx) for x in col_cfg["option_x"]]
#             radius = max(int(col_cfg.get("bubble_radius", 12) * min(sx, sy)), 6)
#             for q_idx, base_y in enumerate(col_cfg["row_y"]):
#                 q_num = q_idx + q_offset
#                 scaled_y = int(base_y * sy)
#                 ans = answers[q_num - 1]
#                 for i, cx in enumerate(scaled_x):
#                     color = (0, 200, 0) if options[i] == ans else (0, 0, 200)
#                     cv2.circle(color_img, (cx, scaled_y), radius, color, 2)
#                 label_x = max(5, scaled_x[0] - 50)
#                 cv2.putText(
#                     color_img, f"Q{q_num}:{ans or '?'}",
#                     (label_x, scaled_y + 5),
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 100, 0), 1
#                 )

#         _draw_column(self.config.LEFT_COLUMN, 1)
#         _draw_column(self.config.RIGHT_COLUMN, 11)
#         cv2.imwrite(output_path, color_img)
#         print(f"   💾 Debug saved: {output_path}")

















# ----------------------------------- test:   









"""
OMR Processor v3 — Resolution-robust bubble tracking
=====================================================
✅ Relative coordinates (fractions of W/H) — size change OK
✅ Local search around expected center — small crop shift OK
✅ CLAHE for phone lighting
✅ Same printed sheet design → works across phone photos

Detection:
  expected bubble position → search nearby window → pick darkest mean
  darkest option in row = answer (if gap > threshold)
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple

try:
    from app.config import OMRConfig
except ImportError:
    from config import OMRConfig


class OMRProcessor:

    def __init__(self):
        self.config = OMRConfig
        print("=" * 60)
        print("   OMR Processor v3 — Relative + Local Search")
        print(f"   Questions : {self.config.ANSWERS['total_questions']}")
        print(f"   Method    : relative coords + local dark search")
        print("=" * 60)

    # ─────────────────────────────────────────────────────────
    # PUBLIC
    # ─────────────────────────────────────────────────────────
    def process_image(self, image_bytes: bytes, debug: bool = False) -> Dict:
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                return {"success": False, "error": "Cannot decode image"}

            h0, w0 = image.shape[:2]
            print(f"\n📥 Image: {w0}×{h0} px")

            # Enhance phone photos
            image = self._enhance(image)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)

            h, w = gray.shape[:2]
            print(f"   Working size: {w}×{h}")

            if debug:
                cv2.imwrite("debug_gray.png", gray)

            student_id = self._extract_student_id(gray)
            print(f"   🎓 Student ID: {student_id}")

            answers = self._extract_answers(gray, debug=debug)
            answered = sum(1 for a in answers if a is not None)

            print(f"   📊 Answered: {answered}/{self.config.ANSWERS['total_questions']}\n")

            return {
                "success": True,
                "student_id": student_id,
                "answers": answers,
                "total_answered": answered,
                "total_blank": self.config.ANSWERS["total_questions"] - answered,
                "total_questions": self.config.ANSWERS["total_questions"],
                "image_type": "camera",
                "confidence": round(answered / self.config.ANSWERS["total_questions"], 2),
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def grade_exam(self, student_answers: List, answer_key: Dict) -> Dict:
        correct = wrong = blank = 0
        details = []
        marks = self.config.GRADING["marks_per_question"]
        neg = self.config.GRADING["negative_marks"] if self.config.GRADING["negative_marking"] else 0

        for i, ans in enumerate(student_answers):
            q = str(i + 1)
            key = answer_key.get(q)
            if ans is None:
                blank += 1
                details.append({"question": i+1, "student": None, "correct": key, "status": "blank", "marks": 0})
            elif ans == key:
                correct += 1
                details.append({"question": i+1, "student": ans, "correct": key, "status": "correct", "marks": marks})
            else:
                wrong += 1
                details.append({"question": i+1, "student": ans, "correct": key, "status": "wrong", "marks": -neg})

        total = len(answer_key)
        raw = max(correct * marks - wrong * neg, 0)
        pct = (raw / total * 100) if total else 0
        grade = ("A+" if pct >= 80 else "A" if pct >= 70 else "A-" if pct >= 60
                 else "B" if pct >= 50 else "C" if pct >= 40 else "D" if pct >= 33 else "F")

        return {
            "correct": correct, "wrong": wrong, "blank": blank, "total": total,
            "raw_marks": raw, "percentage": round(pct, 1), "grade": grade, "details": details,
        }

    # ─────────────────────────────────────────────────────────
    # CORE: relative position + local dark search
    # ─────────────────────────────────────────────────────────
    def _px(self, frac: float, total: int) -> int:
        return int(round(frac * total))

    def _sample_mean(self, gray: np.ndarray, cx: int, cy: int, radius: int) -> float:
        h, w = gray.shape
        cx = int(np.clip(cx, 0, w - 1))
        cy = int(np.clip(cy, 0, h - 1))
        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.circle(mask, (cx, cy), max(radius, 3), 255, -1)
        return float(cv2.mean(gray, mask=mask)[0])

    def _local_darkest(
        self, gray: np.ndarray, cx: int, cy: int, search_r: int, sample_r: int
    ) -> Tuple[float, int, int]:
        """
        Search a window around (cx, cy). Return (min_mean, best_x, best_y).
        This absorbs small shifts when the photo is cropped differently.
        """
        h, w = gray.shape
        x1, x2 = max(0, cx - search_r), min(w, cx + search_r + 1)
        y1, y2 = max(0, cy - search_r), min(h, cy + search_r + 1)

        best_val, best_x, best_y = 999.0, cx, cy
        # step 2 px for speed
        for y in range(y1, y2, 2):
            for x in range(x1, x2, 2):
                v = self._sample_mean(gray, x, y, sample_r)
                if v < best_val:
                    best_val, best_x, best_y = v, x, y
        return best_val, best_x, best_y

    def _read_row(
        self, gray: np.ndarray, xs: List[int], y: int, options: List[str]
    ) -> Optional[str]:
        h, w = gray.shape
        min_side = min(h, w)
        search_r = max(int(self.config.THRESHOLDS["local_search_frac"] * min_side), 6)
        sample_r = max(int(self.config.THRESHOLDS["sample_radius_frac"] * min_side), 4)
        threshold = self.config.THRESHOLDS["darkness_diff_threshold"]

        values = []
        for x in xs:
            val, _, _ = self._local_darkest(gray, x, y, search_r, sample_r)
            values.append(val)

        min_v, max_v = min(values), max(values)
        if max_v - min_v < threshold:
            return None
        return options[values.index(min_v)]

    def _extract_answers(self, gray: np.ndarray, debug: bool = False) -> List[Optional[str]]:
        h, w = gray.shape
        options = ["A", "B", "C", "D"]
        answers: List[Optional[str]] = [None] * self.config.ANSWERS["total_questions"]

        def read_col(col_cfg, q_offset, label):
            print(f"\n   📝 {label}")
            xs = [self._px(f, w) for f in col_cfg["option_x_frac"]]
            for i, yf in enumerate(col_cfg["row_y_frac"]):
                y = self._px(yf, h)
                # raw values for log
                min_side = min(h, w)
                search_r = max(int(self.config.THRESHOLDS["local_search_frac"] * min_side), 6)
                sample_r = max(int(self.config.THRESHOLDS["sample_radius_frac"] * min_side), 4)
                vals = [self._local_darkest(gray, x, y, search_r, sample_r)[0] for x in xs]
                ans = self._read_row(gray, xs, y, options)
                answers[q_offset + i - 1] = ans
                print(f"      Q{q_offset+i:2d}: dark={[f'{v:.0f}' for v in vals]} → {ans or '---'}")

        read_col(self.config.LEFT_COLUMN, 1, "LEFT (Q1-Q10)")
        read_col(self.config.RIGHT_COLUMN, 11, "RIGHT (Q11-Q20)")

        if debug:
            self._draw_debug(gray, answers)
        return answers

    def _extract_student_id(self, gray: np.ndarray) -> str:
        h, w = gray.shape
        cfg = self.config.STUDENT_ID
        min_side = min(h, w)
        sample_r = max(int(self.config.THRESHOLDS["sample_radius_frac"] * min_side), 3)
        search_r = max(int(self.config.THRESHOLDS["local_search_frac"] * min_side), 4)
        threshold = self.config.THRESHOLDS.get("sid_darkness_diff_threshold", 15)

        y0 = self._px(cfg["y0_frac"], h)
        row_sp = self._px(cfg["row_spacing_frac"], h)
        cols_x = [self._px(f, w) for f in cfg["col_x_frac"]]

        digits = []
        print("\n   📖 Student ID (bubbles):")
        for ci, cx in enumerate(cols_x):
            vals = []
            for r in range(cfg["options"]):
                cy = y0 + r * row_sp
                v, _, _ = self._local_darkest(gray, cx, cy, search_r, sample_r)
                vals.append(v)
            mn, mx = min(vals), max(vals)
            if mx - mn >= threshold:
                d = str(vals.index(mn))
                print(f"      Col {ci+1}: ✅ {d}  (dark={mn:.0f}, diff={mx-mn:.0f})")
            else:
                d = "?"
                print(f"      Col {ci+1}: ❌ blank (diff={mx-mn:.0f})")
            digits.append(d)
        return "".join(digits)

    # ─────────────────────────────────────────────────────────
    def _enhance(self, image: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
        return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    def _draw_debug(self, gray, answers, path="debug_answers.png"):
        img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        h, w = gray.shape
        options = ["A", "B", "C", "D"]
        for col_cfg, off in [(self.config.LEFT_COLUMN, 1), (self.config.RIGHT_COLUMN, 11)]:
            xs = [self._px(f, w) for f in col_cfg["option_x_frac"]]
            for i, yf in enumerate(col_cfg["row_y_frac"]):
                y = self._px(yf, h)
                ans = answers[off + i - 1]
                r = max(int(0.01 * min(h, w)), 6)
                for j, x in enumerate(xs):
                    color = (0, 200, 0) if options[j] == ans else (0, 0, 200)
                    cv2.circle(img, (x, y), r, color, 2)
        cv2.imwrite(path, img)
        print(f"   💾 {path}")
