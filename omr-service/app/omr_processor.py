
# ----------------------------------- test:   




"""Perspective-normalized OMR processor for the supplied 20-question sheet."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

try:
    from app.config import OMRConfig
except ImportError:
    from config import OMRConfig


class OMRProcessor:
    def __init__(self) -> None:
        self.config = OMRConfig
        print("=" * 60)
        print("   OMR Processor v5 — Border Warp + Student-ID Auto Align")
        print(f"   Questions : {self.config.ANSWERS['total_questions']}")
        print("   Method    : perspective normalization + inner bubble score")
        print("=" * 60)

    def process_image(
        self,
        image_bytes: bytes,
        apply_perspective: bool = True,
        debug: bool = False,
    ) -> Dict:
        """Read the student ID and answers from one image.

        ``apply_perspective`` is retained for compatibility with the existing
        FastAPI endpoint. Border normalization is attempted automatically,
        because raw whole-image fractions are not reliable for phone photos.
        """
        try:
            data = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if image is None:
                return {"success": False, "error": "Cannot decode image"}

            h0, w0 = image.shape[:2]
            print(f"\n📥 Image: {w0}×{h0} px")

            # Always try automatic normalization. If no suitable quadrilateral
            # is found, the original image is resized as a safe fallback.
            normalized, warped = self._normalize_sheet(image)
            print(
                f"   Sheet normalization: {'perspective warp' if warped else 'resize fallback'}"
            )

            enhanced = self._enhance(normalized)
            gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
            blur_kernel = self.config.PREPROCESS.get("blur_kernel", (5, 5))
            gray = cv2.GaussianBlur(gray, blur_kernel, 0)

            if debug:
                cv2.imwrite("debug_normalized.png", normalized)
                cv2.imwrite("debug_gray.png", gray)

            student_id, sid_confidence, sid_alignment = self._extract_student_id(gray)
            answers, answer_confidences = self._extract_answers(gray)
            answered = sum(answer is not None for answer in answers)

            if debug:
                self._draw_debug(gray, answers, student_id, sid_alignment)

            answer_conf = (
                float(np.mean(answer_confidences)) if answer_confidences else 0.0
            )
            overall_conf = round((sid_confidence + answer_conf) / 2.0, 3)

            print(f"   🎓 Student ID: {student_id}")
            print(f"   📊 Answered: {answered}/{self.config.ANSWERS['total_questions']}\n")

            return {
                "success": True,
                "student_id": student_id,
                "answers": answers,
                "total_answered": answered,
                "total_blank": self.config.ANSWERS["total_questions"] - answered,
                "total_questions": self.config.ANSWERS["total_questions"],
                "image_type": "camera_or_scan",
                "confidence": overall_conf,
                "student_id_confidence": round(sid_confidence, 3),
                "student_id_valid": "?" not in student_id,
                "student_id_alignment_px": {
                    "dx": int(sid_alignment[0]),
                    "dy": int(sid_alignment[1]),
                },
                "answer_confidences": [round(v, 3) for v in answer_confidences],
                "perspective_normalized": warped,
            }
        except Exception as exc:  # pragma: no cover - defensive API boundary
            import traceback

            traceback.print_exc()
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Perspective normalization
    # ------------------------------------------------------------------
    @staticmethod
    def _order_points(points: np.ndarray) -> np.ndarray:
        pts = points.reshape(4, 2).astype(np.float32)
        ordered = np.zeros((4, 2), dtype=np.float32)
        sums = pts.sum(axis=1)
        diffs = np.diff(pts, axis=1).reshape(-1)
        ordered[0] = pts[np.argmin(sums)]   # top-left
        ordered[2] = pts[np.argmax(sums)]   # bottom-right
        ordered[1] = pts[np.argmin(diffs)]  # top-right
        ordered[3] = pts[np.argmax(diffs)]  # bottom-left
        return ordered

    def _find_sheet_quad(self, image: np.ndarray) -> Optional[np.ndarray]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        threshold_value = self.config.THRESHOLDS.get("warp_threshold", 120)
        _, binary = cv2.threshold(
            gray, threshold_value, 255, cv2.THRESH_BINARY_INV
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        image_area = image.shape[0] * image.shape[1]
        min_ratio = self.config.THRESHOLDS.get("warp_min_area_ratio", 0.25)

        for contour in sorted(contours, key=cv2.contourArea, reverse=True):
            if cv2.contourArea(contour) < image_area * min_ratio:
                break
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            if len(approx) == 4:
                return self._order_points(approx)
        return None

    def _normalize_sheet(self, image: np.ndarray) -> Tuple[np.ndarray, bool]:
        width = self.config.BASE_WIDTH
        height = self.config.BASE_HEIGHT
        quad = self._find_sheet_quad(image)
        if quad is None:
            return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA), False

        destination = np.array(
            [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
            dtype=np.float32,
        )
        matrix = cv2.getPerspectiveTransform(quad, destination)
        warped = cv2.warpPerspective(image, matrix, (width, height))
        return warped, True

    # ------------------------------------------------------------------
    # Bubble measurements
    # ------------------------------------------------------------------
    @staticmethod
    def _px(frac: float, total: int) -> int:
        return int(round(frac * total))

    def _bubble_stats(
        self, gray: np.ndarray, cx: int, cy: int, radius: int
    ) -> Tuple[float, float]:
        h, w = gray.shape[:2]
        cx = int(np.clip(cx, radius, w - radius - 1))
        cy = int(np.clip(cy, radius, h - radius - 1))

        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.circle(mask, (cx, cy), max(radius, 3), 255, -1)
        pixels = gray[mask == 255]
        if pixels.size == 0:
            return 255.0, 0.0

        dark_threshold = self.config.THRESHOLDS["dark_pixel_threshold"]
        mean = float(np.mean(pixels))
        dark_ratio = float(np.mean(pixels < dark_threshold))
        return mean, dark_ratio

    def _choose_mark(
        self,
        stats: Sequence[Tuple[float, float]],
        diff_threshold: float,
    ) -> Tuple[Optional[int], float]:
        means = [item[0] for item in stats]
        ratios = [item[1] for item in stats]
        order = np.argsort(means)
        best = int(order[0])
        second = int(order[1])
        gap = means[second] - means[best]

        mean_limit = self.config.THRESHOLDS["filled_mean_threshold"]
        ratio_limit = self.config.THRESHOLDS["filled_ratio_threshold"]
        absolutely_filled = means[best] <= mean_limit or ratios[best] >= ratio_limit
        clearly_best = gap >= diff_threshold

        # Confidence combines absolute fill and separation from other bubbles.
        fill_strength = max(
            0.0,
            min(
                1.0,
                max((mean_limit - means[best]) / max(mean_limit, 1), ratios[best] - 0.35),
            ),
        )
        separation = max(0.0, min(1.0, gap / 80.0))
        confidence = max(0.0, min(1.0, 0.55 * fill_strength + 0.45 * separation))

        if not (absolutely_filled and clearly_best):
            return None, confidence
        return best, confidence

    # ------------------------------------------------------------------
    # Answers
    # ------------------------------------------------------------------
    def _extract_answers(
        self, gray: np.ndarray
    ) -> Tuple[List[Optional[str]], List[float]]:
        h, w = gray.shape[:2]
        options = ["A", "B", "C", "D"]
        answers: List[Optional[str]] = [None] * self.config.ANSWERS["total_questions"]
        confidences: List[float] = [0.0] * self.config.ANSWERS["total_questions"]
        radius = max(
            4,
            int(round(self.config.THRESHOLDS["sample_radius_frac"] * min(h, w))),
        )
        diff_threshold = self.config.THRESHOLDS["darkness_diff_threshold"]

        def read_column(column: Dict, q_offset: int, label: str) -> None:
            print(f"\n   📝 {label}")
            xs = [self._px(frac, w) for frac in column["option_x_frac"]]
            for row_index, y_frac in enumerate(column["row_y_frac"]):
                y = self._px(y_frac, h)
                stats = [self._bubble_stats(gray, x, y, radius) for x in xs]
                selected, confidence = self._choose_mark(stats, diff_threshold)
                question_index = q_offset + row_index - 1
                answer = options[selected] if selected is not None else None
                answers[question_index] = answer
                confidences[question_index] = confidence
                means = [f"{mean:.0f}" for mean, _ in stats]
                print(
                    f"      Q{q_offset + row_index:2d}: mean={means} "
                    f"→ {answer or 'BLANK'}"
                )

        read_column(self.config.LEFT_COLUMN, 1, "LEFT (Q1-Q10)")
        read_column(self.config.RIGHT_COLUMN, 11, "RIGHT (Q11-Q20)")
        return answers, confidences

    # ------------------------------------------------------------------
    # Student ID
    # ------------------------------------------------------------------
    def _align_student_id_grid(
        self, gray: np.ndarray, xs: Sequence[int], ys: Sequence[int]
    ) -> Tuple[int, int, float]:
        """Find the small global shift of the printed Student-ID grid.

        The outer sheet border is stable, but the ID grid itself moves roughly
        10–15 px between the supplied scans.  We correlate an annulus-shaped
        kernel with all 80 printed bubble outlines, then choose the offset that
        gives the strongest average ring response.  This aligns the grid from
        the printed circles, not from handwritten digits or filled interiors.
        """
        h, w = gray.shape[:2]
        min_side = min(h, w)
        thresholds = self.config.THRESHOLDS

        inner = max(4, int(round(
            thresholds["sid_align_annulus_inner_frac"] * min_side
        )))
        outer = max(inner + 3, int(round(
            thresholds["sid_align_annulus_outer_frac"] * min_side
        )))

        yy, xx = np.mgrid[-outer:outer + 1, -outer:outer + 1]
        annulus = (
            (xx * xx + yy * yy <= outer * outer)
            & (xx * xx + yy * yy >= inner * inner)
        ).astype(np.float32)
        annulus /= max(float(annulus.sum()), 1.0)

        darkness = (255.0 - gray.astype(np.float32))
        response = cv2.filter2D(
            darkness, cv2.CV_32F, annulus, borderType=cv2.BORDER_REPLICATE
        )

        search_x = max(4, int(round(
            thresholds["sid_align_search_x_frac"] * w
        )))
        search_y = max(3, int(round(
            thresholds["sid_align_search_y_frac"] * h
        )))

        base_x = np.asarray(xs, dtype=np.int32)
        base_y = np.asarray(ys, dtype=np.int32)
        best_score = -1.0
        best_dx = best_dy = 0

        for dy in range(-search_y, search_y + 1):
            shifted_y = base_y + dy
            if shifted_y.min() < 0 or shifted_y.max() >= h:
                continue
            for dx in range(-search_x, search_x + 1):
                shifted_x = base_x + dx
                if shifted_x.min() < 0 or shifted_x.max() >= w:
                    continue
                score = float(response[np.ix_(shifted_y, shifted_x)].mean())
                if score > best_score:
                    best_score = score
                    best_dx = dx
                    best_dy = dy

        return best_dx, best_dy, best_score

    def _extract_student_id(
        self, gray: np.ndarray
    ) -> Tuple[str, float, Tuple[int, int]]:
        h, w = gray.shape[:2]
        cfg = self.config.STUDENT_ID
        base_xs = [self._px(frac, w) for frac in cfg["col_x_frac"]]
        base_ys = [self._px(frac, h) for frac in cfg["row_y_frac"]]
        dx, dy, align_score = self._align_student_id_grid(gray, base_xs, base_ys)
        xs = [x + dx for x in base_xs]
        ys = [y + dy for y in base_ys]

        radius = max(
            4,
            int(round(self.config.THRESHOLDS["sid_sample_radius_frac"] * min(h, w))),
        )
        diff_threshold = self.config.THRESHOLDS["sid_darkness_diff_threshold"]

        digits: List[str] = []
        confidences: List[float] = []
        print("\n   📖 Student ID (bubbles):")
        print(f"      Grid alignment: dx={dx:+d}px, dy={dy:+d}px, score={align_score:.1f}")
        for column_index, x in enumerate(xs):
            stats = [self._bubble_stats(gray, x, y, radius) for y in ys]
            selected, confidence = self._choose_mark(stats, diff_threshold)
            confidences.append(confidence)
            if selected is None:
                digit = "?"
                print(f"      Col {column_index + 1}: ❌ ambiguous/blank")
            else:
                digit = str(selected)
                best_mean, best_ratio = stats[selected]
                means = sorted(item[0] for item in stats)
                gap = means[1] - means[0]
                print(
                    f"      Col {column_index + 1}: ✅ {digit} "
                    f"(mean={best_mean:.0f}, fill={best_ratio:.2f}, gap={gap:.0f})"
                )
            digits.append(digit)

        mean_confidence = float(np.mean(confidences)) if confidences else 0.0
        return "".join(digits), mean_confidence, (dx, dy)

    # ------------------------------------------------------------------
    # Grading
    # ------------------------------------------------------------------
    def grade_exam(self, student_answers: List, answer_key: Dict) -> Dict:
        correct = wrong = blank = 0
        details = []
        marks = self.config.GRADING["marks_per_question"]
        negative = (
            self.config.GRADING["negative_marks"]
            if self.config.GRADING["negative_marking"]
            else 0
        )

        for index, answer in enumerate(student_answers):
            question = str(index + 1)
            key = answer_key.get(question)
            if answer is None:
                blank += 1
                status = "blank"
                awarded = 0
            elif answer == key:
                correct += 1
                status = "correct"
                awarded = marks
            else:
                wrong += 1
                status = "wrong"
                awarded = -negative
            details.append(
                {
                    "question": index + 1,
                    "student": answer,
                    "correct": key,
                    "status": status,
                    "marks": awarded,
                }
            )

        total = len(answer_key)
        raw = max(correct * marks - wrong * negative, 0)
        percentage = (raw / total * 100) if total else 0
        grade = (
            "A+" if percentage >= 80 else
            "A" if percentage >= 70 else
            "A-" if percentage >= 60 else
            "B" if percentage >= 50 else
            "C" if percentage >= 40 else
            "D" if percentage >= 33 else "F"
        )
        return {
            "correct": correct,
            "wrong": wrong,
            "blank": blank,
            "total": total,
            "raw_marks": raw,
            "percentage": round(percentage, 1),
            "grade": grade,
            "details": details,
        }

    # ------------------------------------------------------------------
    # Image helpers / debug
    # ------------------------------------------------------------------
    def _enhance(self, image: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        lightness, a, b = cv2.split(lab)
        clip = self.config.PREPROCESS.get("clahe_clip_limit", 2.0)
        grid = self.config.PREPROCESS.get("clahe_grid", (8, 8))
        lightness = cv2.createCLAHE(clipLimit=clip, tileGridSize=grid).apply(lightness)
        return cv2.cvtColor(cv2.merge([lightness, a, b]), cv2.COLOR_LAB2BGR)

    def _draw_debug(
        self,
        gray: np.ndarray,
        answers: List[Optional[str]],
        student_id: str,
        sid_alignment: Tuple[int, int] = (0, 0),
        path: str = "debug_omr.png",
    ) -> None:
        image = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        h, w = gray.shape[:2]
        options = ["A", "B", "C", "D"]
        answer_radius = max(
            6,
            int(round(self.config.THRESHOLDS["sample_radius_frac"] * min(h, w))),
        )

        for column, offset in (
            (self.config.LEFT_COLUMN, 1),
            (self.config.RIGHT_COLUMN, 11),
        ):
            xs = [self._px(frac, w) for frac in column["option_x_frac"]]
            for row_index, y_frac in enumerate(column["row_y_frac"]):
                y = self._px(y_frac, h)
                answer = answers[offset + row_index - 1]
                for option_index, x in enumerate(xs):
                    selected = answer == options[option_index]
                    color = (0, 200, 0) if selected else (0, 0, 220)
                    cv2.circle(image, (x, y), answer_radius, color, 2)

        sid_cfg = self.config.STUDENT_ID
        sid_dx, sid_dy = sid_alignment
        sid_xs = [self._px(frac, w) + sid_dx for frac in sid_cfg["col_x_frac"]]
        sid_ys = [self._px(frac, h) + sid_dy for frac in sid_cfg["row_y_frac"]]
        for column_index, x in enumerate(sid_xs):
            selected_digit = student_id[column_index] if column_index < len(student_id) else "?"
            for digit, y in enumerate(sid_ys):
                color = (255, 0, 255) if selected_digit == str(digit) else (255, 180, 0)
                cv2.circle(image, (x, y), 7, color, 1)

        cv2.imwrite(path, image)
        print(f"   💾 Debug saved: {path}")