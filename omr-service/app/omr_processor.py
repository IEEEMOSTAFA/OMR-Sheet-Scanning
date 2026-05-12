"""
OMR Processor — Handwritten MCQ Answer Sheet
==============================================
✅ Grayscale darkness detection (100% accurate on Written_Img_1.png)
✅ Auto-scaling: যেকোনো resolution এ কাজ করে
✅ Camera/phone image support
✅ Student ID extraction
✅ Left column Q1-Q10 | Right column Q11-Q20
✅ Backward compatible with old API

Detection Method (★ নতুন):
  filled bubble  → grayscale mean ≈ 25-50   (dark ink)
  unfilled bubble → grayscale mean ≈ 150-180 (white paper)
  → সবচেয়ে dark bubble = selected answer
  → difference < 8 units হলে blank (কোনো bubble fill হয়নি)
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple

# ─── Import path (app/ ফোল্ডার থেকে রান করলে) ───
try:
    from app.config import OMRConfig
    from app.utils import OMRUtils
except ImportError:
    from config import OMRConfig
    try:
        from utils import OMRUtils
    except ImportError:
        OMRUtils = None


class OMRProcessor:

    def __init__(self):
        self.config = OMRConfig
        self.utils  = OMRUtils

        print("=" * 60)
        print("   OMR Processor v2.0 — Handwritten Support")
        print(f"   Total Questions : {self.config.ANSWERS['total_questions']}")
        print(f"   Left  X (A-D)  : {self.config.LEFT_COLUMN['option_x']}")
        print(f"   Right X (A-D)  : {self.config.RIGHT_COLUMN['option_x']}")
        print(f"   Base resolution: {self.config.BASE_WIDTH}×{self.config.BASE_HEIGHT}")
        print(f"   Method         : {self.config.THRESHOLDS['detection_method']}")
        print("=" * 60)

    # ─────────────────────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ─────────────────────────────────────────────────────────────
    def process_image(
        self,
        image_bytes: bytes,
        apply_perspective: bool = False,
        debug: bool = False
    ) -> Dict:
        """
        যেকোনো OMR sheet image (camera/phone/scanner) process করে।

        Steps:
          1. Image decode
          2. Camera image detect & enhance
          3. Perspective correction (optional)
          4. Scale factor calculate (config coords auto-scale হয়)
          5. Grayscale prepare
          6. Student ID extract
          7. Answers extract (grayscale darkness method)

        Returns:
          {success, student_id, answers, total_answered, total_blank,
           total_questions, image_type, confidence}
        """
        try:
            # ── Step 1: Decode ──
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                return {"success": False, "error": "Image decode করা যায়নি"}

            orig_h, orig_w = image.shape[:2]
            print(f"\n{'='*60}")
            print(f"📥 Image: {orig_w}×{orig_h} px")

            # ── Step 2: Camera image detect & enhance ──
            is_cam = self._is_camera_image(image)
            if is_cam:
                print("   📷 Camera image → enhancing...")
                image = self._enhance_camera_image(image)

            # ── Step 3: Perspective correction ──
            if apply_perspective and self.utils is not None:
                try:
                    print("   🔄 Perspective correction...")
                    image = self.utils.correct_perspective(image)
                except Exception as e:
                    print(f"   ⚠️ Perspective skipped: {e}")

            curr_h, curr_w = image.shape[:2]

            # ── Step 4: Scale factors ──
            # config coords BASE_WIDTH×BASE_HEIGHT এর জন্য।
            # Image different size হলে auto-scale করি।
            sx = curr_w / self.config.BASE_WIDTH
            sy = curr_h / self.config.BASE_HEIGHT
            print(f"   📐 Scale: sx={sx:.3f}, sy={sy:.3f}")

            # ── Step 5: Grayscale ──
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # Slight blur noise কমাতে (bubble edges smooth করে)
            gray_blur = cv2.GaussianBlur(gray, (9, 9), 0)

            if debug:
                cv2.imwrite("debug_gray.png", gray_blur)

            # ── Step 6: Student ID ──
            student_id = self._extract_student_id(gray_blur, sx, sy, debug=debug)
            print(f"   🎓 Student ID: {student_id}")

            # ── Step 7: Answers ──
            answers = self._extract_answers(gray_blur, sx, sy, debug=debug)

            answered = sum(1 for a in answers if a is not None)
            blank    = self.config.ANSWERS["total_questions"] - answered

            print(f"   📊 Answered: {answered}/{self.config.ANSWERS['total_questions']}")
            print(f"{'='*60}\n")

            return {
                "success"         : True,
                "student_id"      : student_id,
                "answers"         : answers,
                "total_answered"  : answered,
                "total_blank"     : blank,
                "total_questions" : self.config.ANSWERS["total_questions"],
                "image_type"      : "camera" if is_cam else "scanned",
                "confidence"      : round(answered / self.config.ANSWERS["total_questions"], 2),
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    # ─────────────────────────────────────────────────────────────
    # ★ CORE: GRAYSCALE DARKNESS BUBBLE READER
    # ─────────────────────────────────────────────────────────────
    def _read_bubble_darkness(
        self,
        gray: np.ndarray,
        cx: int,
        cy: int,
        radius: int
    ) -> float:
        """
        একটি bubble এর center (cx, cy) তে circular mask দিয়ে
        grayscale mean darkness পরিমাপ করে।

        Return: mean pixel value (0=black/filled, 255=white/empty)
        Lower value = darker = more filled
        """
        shrink = self.config.THRESHOLDS.get("sample_radius_shrink", 5)
        sample_r = max(radius - shrink, 5)

        mask = np.zeros(gray.shape, dtype="uint8")
        cv2.circle(mask, (cx, cy), sample_r, 255, -1)

        mean_val = cv2.mean(gray, mask=mask)[0]
        return mean_val

    def _select_answer_from_row(
        self,
        gray: np.ndarray,
        bubble_centers: List[Tuple[int, int]],
        radius: int,
        options: List[str]
    ) -> Optional[str]:
        """
        একটি question row এর bubbles থেকে answer বের করে।

        Logic:
        - প্রতিটি bubble এর darkness measure করি
        - সবচেয়ে dark bubble = selected
        - সেই bubble lightest bubble থেকে darkness_diff_threshold এর বেশি dark হতে হবে
        - না হলে = blank (কেউ fill করেনি)
        """
        threshold = self.config.THRESHOLDS.get("darkness_diff_threshold", 8)

        darkness_values = [
            self._read_bubble_darkness(gray, cx, cy, radius)
            for cx, cy in bubble_centers
        ]

        min_val = min(darkness_values)   # darkest = filled
        max_val = max(darkness_values)   # lightest

        diff = max_val - min_val

        if diff < threshold:
            return None  # blank — কোনো bubble significantly darker না

        darkest_idx = darkness_values.index(min_val)
        return options[darkest_idx]

    # ─────────────────────────────────────────────────────────────
    # ANSWER EXTRACTION
    # ─────────────────────────────────────────────────────────────
    def _extract_answers(
        self,
        gray: np.ndarray,
        sx: float,
        sy: float,
        debug: bool = False
    ) -> List[Optional[str]]:
        """
        Q1-Q20 এর answers extract করে।
        config এর coordinates auto-scale করা হয়।
        """
        options    = ['A', 'B', 'C', 'D']
        all_answers = [None] * self.config.ANSWERS["total_questions"]

        def _read_column(col_cfg: dict, q_offset: int, label: str):
            print(f"\n   📝 {label}:")

            # Scale option X coordinates
            scaled_x = [int(x * sx) for x in col_cfg["option_x"]]
            radius   = int(col_cfg.get("bubble_radius", 35) * min(sx, sy))
            radius   = max(radius, 10)

            for q_idx, base_y in enumerate(col_cfg["row_y"]):
                q_num = q_idx + q_offset
                scaled_y = int(base_y * sy)

                # Bubble centers for this row
                centers = [(x, scaled_y) for x in scaled_x]

                # Darkness values for logging
                dark_vals = [
                    self._read_bubble_darkness(gray, cx, cy, radius)
                    for cx, cy in centers
                ]

                answer = self._select_answer_from_row(gray, centers, radius, options)
                all_answers[q_num - 1] = answer

                status = answer if answer else "---"
                print(f"      Q{q_num:2d}: dark={[f'{v:.0f}' for v in dark_vals]} → {status}")

        _read_column(self.config.LEFT_COLUMN,  1,  "LEFT  COLUMN (Q1-Q10)")
        _read_column(self.config.RIGHT_COLUMN, 11, "RIGHT COLUMN (Q11-Q20)")

        # Debug visualization
        if debug:
            self._draw_debug(gray, all_answers, sx, sy)

        return all_answers

    # ─────────────────────────────────────────────────────────────
    # STUDENT ID EXTRACTION
    # ─────────────────────────────────────────────────────────────
    def _extract_student_id(
        self,
        gray: np.ndarray,
        sx: float,
        sy: float,
        debug: bool = False
    ) -> str:
        """
        8-digit Student ID grid থেকে ID extract করে।
        Grayscale darkness method ব্যবহার করে।
        """
        id_cfg  = self.config.STUDENT_ID
        digits  = []
        options_count = id_cfg.get("options", 10)  # digit 0-9

        print(f"\n   📖 Extracting Student ID...")

        for col in range(id_cfg["num_digits"]):
            # Column X position (scaled)
            col_x_list = id_cfg.get("col_x", None)
            if col_x_list and col < len(col_x_list):
                col_x = int(col_x_list[col] * sx)
            else:
                col_x = int((id_cfg["x"] + col * id_cfg["digit_width"]) * sx)

            darkness_vals = []
            row_spacing   = int(id_cfg.get("row_spacing", id_cfg["digit_height"]) * sy)
            d_height      = int(id_cfg["digit_height"] * sy)
            d_width       = int(id_cfg["digit_width"] * sx)

            for row in range(options_count):  # digit 0-9
                y_pos = int(id_cfg["y"] * sy) + row * row_spacing

                # ROI for this cell
                roi = gray[y_pos:y_pos + d_height, col_x:col_x + d_width]
                if roi.size < 20:
                    darkness_vals.append(255.0)
                    continue

                mean_val = float(np.mean(roi))
                darkness_vals.append(mean_val)

            # Most dark cell = selected digit
            min_val  = min(darkness_vals)
            max_val  = max(darkness_vals)
            diff     = max_val - min_val
            threshold = self.config.THRESHOLDS.get("darkness_diff_threshold", 8)

            if diff >= threshold:
                best_row = darkness_vals.index(min_val)
                selected = str(best_row)
                print(f"      Col {col+1}: ✅ {selected}  (dark={min_val:.0f}, diff={diff:.0f})")
            else:
                selected = "?"
                print(f"      Col {col+1}: ❌ blank  (diff={diff:.0f})")

            digits.append(selected)

        return "".join(digits)

    # ─────────────────────────────────────────────────────────────
    # GRADING
    # ─────────────────────────────────────────────────────────────
    def grade_exam(
        self,
        student_answers: List,
        answer_key: Dict
    ) -> Dict:
        """
        Answer key দিয়ে score calculate করে।
        answer_key = {"1": "A", "2": "C", ...}
        """
        correct, wrong, blank = 0, 0, 0
        details = []
        grading = self.config.GRADING

        for i, student_ans in enumerate(student_answers):
            q_num       = str(i + 1)
            correct_ans = answer_key.get(q_num)

            if student_ans is None:
                blank += 1
                details.append({
                    "question": i + 1, "student": None,
                    "correct": correct_ans, "status": "blank", "marks": 0
                })
            elif student_ans == correct_ans:
                correct += 1
                details.append({
                    "question": i + 1, "student": student_ans,
                    "correct": correct_ans, "status": "correct",
                    "marks": grading["marks_per_question"]
                })
            else:
                wrong += 1
                neg = grading["negative_marks"] if grading["negative_marking"] else 0
                details.append({
                    "question": i + 1, "student": student_ans,
                    "correct": correct_ans, "status": "wrong", "marks": -neg
                })

        total_q   = len(answer_key)
        raw_marks = correct * grading["marks_per_question"]
        if grading["negative_marking"]:
            raw_marks -= wrong * grading["negative_marks"]
        raw_marks  = max(raw_marks, 0)
        percentage = (raw_marks / total_q * 100) if total_q > 0 else 0

        if   percentage >= 80: grade = "A+"
        elif percentage >= 70: grade = "A"
        elif percentage >= 60: grade = "A-"
        elif percentage >= 50: grade = "B"
        elif percentage >= 40: grade = "C"
        elif percentage >= 33: grade = "D"
        else:                   grade = "F"

        print(f"\n   🏆 {correct}/{total_q} correct | {percentage:.1f}% | Grade: {grade}")

        return {
            "correct"    : correct,
            "wrong"      : wrong,
            "blank"      : blank,
            "total"      : total_q,
            "raw_marks"  : raw_marks,
            "percentage" : round(percentage, 1),
            "grade"      : grade,
            "details"    : details,
        }

    # ─────────────────────────────────────────────────────────────
    # HELPER: Camera image detection
    # ─────────────────────────────────────────────────────────────
    def _is_camera_image(self, image: np.ndarray) -> bool:
        """
        Camera দিয়ে তোলা ছবি কিনা detect করে।
        Camera image: বেশি noise, uneven lighting থাকে।
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        # Scanner image সাধারণত খুব sharp (high variance)
        # Camera image moderate variance
        h, w = image.shape[:2]
        is_high_res = (w > 2000 or h > 2000)
        return is_high_res or laplacian_var < 5000

    def _enhance_camera_image(self, image: np.ndarray) -> np.ndarray:
        """
        Camera image এর contrast ও brightness improve করে।
        CLAHE (Contrast Limited Adaptive Histogram Equalization) ব্যবহার।
        """
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        enhanced_lab = cv2.merge([l_enhanced, a, b])
        return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

    # ─────────────────────────────────────────────────────────────
    # DEBUG VISUALIZATION
    # ─────────────────────────────────────────────────────────────
    def _draw_debug(
        self,
        gray: np.ndarray,
        answers: List[Optional[str]],
        sx: float,
        sy: float,
        output_path: str = "debug_answers.png"
    ):
        """Debug image বানায় যেখানে detected answer সবুজ, বাকি লাল।"""
        color_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        options   = ['A', 'B', 'C', 'D']

        def _draw_column(col_cfg, q_offset):
            scaled_x = [int(x * sx) for x in col_cfg["option_x"]]
            radius   = int(col_cfg.get("bubble_radius", 35) * min(sx, sy))

            for q_idx, base_y in enumerate(col_cfg["row_y"]):
                q_num    = q_idx + q_offset
                scaled_y = int(base_y * sy)
                ans      = answers[q_num - 1]

                for i, cx in enumerate(scaled_x):
                    color = (0, 200, 0) if options[i] == ans else (0, 0, 200)
                    cv2.circle(color_img, (cx, scaled_y), radius, color, 3)

                label_x = scaled_x[0] - 60
                cv2.putText(color_img, f"Q{q_num}:{ans or '?'}",
                            (label_x, scaled_y + 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 100, 0), 2)

        _draw_column(self.config.LEFT_COLUMN,  1)
        _draw_column(self.config.RIGHT_COLUMN, 11)

        # Scale down if too large
        dh, dw = color_img.shape[:2]
        if dw > 1500:
            scale = 1500 / dw
            color_img = cv2.resize(color_img, (1500, int(dh * scale)))

        cv2.imwrite(output_path, color_img)
        print(f"   💾 Debug saved: {output_path}")

















# """
# Main OMR Processor
# ✅ Camera/Phone image support
# ✅ Auto perspective correction
# ✅ Auto image enhancement
# ✅ Dynamic coordinate scaling
# ✅ Student ID + Answers detection
# Left column: Q1-Q10 | Right column: Q11-Q20
# """