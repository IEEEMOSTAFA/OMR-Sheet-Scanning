"""
Utility functions for OMR processing
✅ Camera image support added
✅ Auto perspective correction
✅ Dynamic image enhancement
✅ Scale-aware bubble detection
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional


class OMRUtils:

    # ─────────────────────────────────────────────────────
    # TARGET resolution — config.py এই resolution এ calibrate করা
    # Camera image যাই হোক, এই size এ resize করা হবে
    # ─────────────────────────────────────────────────────
    TARGET_WIDTH  = 1361
    TARGET_HEIGHT = 768

    # ─────────────────────────────────────────────────────
    # 1. MAIN IMAGE NORMALIZER
    #    যেকোনো camera/phone image → standard size + corrected
    # ─────────────────────────────────────────────────────
    @staticmethod
    def normalize_image(image: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """
        যেকোনো image কে TARGET resolution এ নিয়ে আসে।
        Returns: (normalized_image, scale_x, scale_y)
        scale_x/y দিয়ে config coordinate scale করা হয়।
        """
        h, w = image.shape[:2]
        scale_x = OMRUtils.TARGET_WIDTH  / w
        scale_y = OMRUtils.TARGET_HEIGHT / h
        resized = cv2.resize(image, (OMRUtils.TARGET_WIDTH, OMRUtils.TARGET_HEIGHT),
                             interpolation=cv2.INTER_LINEAR)
        print(f"   📐 Original: {w}×{h} → Normalized: {OMRUtils.TARGET_WIDTH}×{OMRUtils.TARGET_HEIGHT}")
        print(f"   📏 Scale X: {scale_x:.3f}, Scale Y: {scale_y:.3f}")
        return resized, scale_x, scale_y

    # ─────────────────────────────────────────────────────
    # 2. PERSPECTIVE CORRECTION (Camera angle ঠিক করে)
    # ─────────────────────────────────────────────────────
    @staticmethod
    def correct_perspective(image: np.ndarray) -> np.ndarray:
        """
        Camera থেকে তোলা image এ perspective distortion থাকে।
        Corner markers (কালো আয়তক্ষেত্র) খুঁজে straight করে।
        """
        gray  = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # ── Step 1: Edge detect ──
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges   = cv2.Canny(blurred, 30, 120)

        # Dilate edges → better contour
        kernel = np.ones((3, 3), np.uint8)
        edges  = cv2.dilate(edges, kernel, iterations=1)

        # ── Step 2: Largest 4-point contour খুঁজি ──
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            print("   ⚠️ No contours found — skipping perspective correction")
            return image

        # area অনুসারে sort, বড় থেকে ছোট
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        sheet_contour = None
        for cnt in contours[:10]:
            peri   = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) == 4:
                sheet_contour = approx
                break

        if sheet_contour is None:
            print("   ⚠️ 4-corner sheet not found — skipping perspective correction")
            return image

        # ── Step 3: Perspective transform ──
        pts = sheet_contour.reshape(4, 2).astype("float32")
        warped = OMRUtils.four_point_transform(image, pts)
        print(f"   ✅ Perspective corrected: {warped.shape[1]}×{warped.shape[0]}")
        return warped

    @staticmethod
    def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
        """Bird's eye view transform"""
        rect = OMRUtils.order_points(pts)
        (tl, tr, br, bl) = rect

        widthA  = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB  = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))

        heightA  = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB  = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")

        M      = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
        return warped

    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        """Corner points কে clockwise order এ সাজায়: TL, TR, BR, BL"""
        rect = np.zeros((4, 2), dtype="float32")
        s    = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        rect[0] = pts[np.argmin(s)]    # top-left
        rect[2] = pts[np.argmax(s)]    # bottom-right
        rect[1] = pts[np.argmin(diff)] # top-right
        rect[3] = pts[np.argmax(diff)] # bottom-left
        return rect

    # ─────────────────────────────────────────────────────
    # 3. IMAGE ENHANCEMENT (Camera photo → clean)
    # ─────────────────────────────────────────────────────
    @staticmethod
    def enhance_camera_image(image: np.ndarray) -> np.ndarray:
        """
        Phone camera image এর common সমস্যা fix করে:
        - Uneven lighting (shadow)
        - Low contrast
        - Slight blur
        """
        # BGR → LAB color space (luminance আলাদা করি)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # CLAHE দিয়ে adaptive contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)

        # আবার merge করি
        enhanced_lab = cv2.merge([l_enhanced, a, b])
        enhanced     = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        # Slight sharpening
        kernel  = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharpen = cv2.filter2D(enhanced, -1, kernel)

        print("   ✅ Camera image enhanced (contrast + sharpening)")
        return sharpen

    # ─────────────────────────────────────────────────────
    # 4. PREPROCESSING (Color → Binary)
    # ─────────────────────────────────────────────────────
    @staticmethod
    def preprocess_image(image: np.ndarray, is_camera: bool = False) -> np.ndarray:
        """
        Image কে binary (black & white) তে convert করে।
        is_camera=True হলে extra noise removal করা হয়।
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        if is_camera:
            # Camera image → stronger blur
            blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        else:
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Adaptive threshold — uneven lighting handle করে
        binary = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=15 if not is_camera else 21,
            C=3 if not is_camera else 5
        )

        # Morphological cleaning
        kernel  = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

        if is_camera:
            # Extra noise removal for camera images
            cleaned = cv2.medianBlur(cleaned, 3)

        return cleaned

    # ─────────────────────────────────────────────────────
    # 5. IS CAMERA IMAGE? (auto-detect)
    # ─────────────────────────────────────────────────────
    @staticmethod
    def is_camera_image(image: np.ndarray) -> bool:
        """
        Image টা camera দিয়ে তোলা কিনা auto-detect করে।
        Noise level + contrast variation দেখে বোঝা যায়।
        """
        gray     = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w     = gray.shape

        # Laplacian variance → blur measure
        lap_var  = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Local contrast variation (8 blocks)
        block_h, block_w = h // 4, w // 4
        contrasts = []
        for r in range(4):
            for c in range(4):
                block = gray[r*block_h:(r+1)*block_h, c*block_w:(c+1)*block_w]
                contrasts.append(block.std())
        contrast_var = np.std(contrasts)

        is_cam = (lap_var < 500) or (contrast_var > 25)
        print(f"   🔍 Camera detect: blur={lap_var:.0f}, contrast_var={contrast_var:.1f} → {'📷 Camera' if is_cam else '🖥️ Clean'}")
        return is_cam

    # ─────────────────────────────────────────────────────
    # 6. BUBBLE DETECTION HELPERS
    # ─────────────────────────────────────────────────────
    @staticmethod
    def count_black_pixels(region: np.ndarray) -> int:
        if region.size == 0:
            return 0
        return int(np.sum(region == 255))

    @staticmethod
    def detect_bubble(region: np.ndarray, threshold: int = 150) -> Tuple[bool, int]:
        black_pixels = OMRUtils.count_black_pixels(region)
        return black_pixels > threshold, black_pixels

    @staticmethod
    def find_contours(image: np.ndarray) -> List:
        contours, _ = cv2.findContours(
            image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        return list(contours)

    @staticmethod
    def is_circular(contour, circularity_threshold: float = 0.65) -> bool:
        area      = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            return False
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        return circularity > circularity_threshold

    # ─────────────────────────────────────────────────────
    # 7. DEBUG VISUALIZATION
    # ─────────────────────────────────────────────────────
    @staticmethod
    def visualize_bubbles(image: np.ndarray, bubbles: List, output_path: str):
        debug_img = image.copy()
        for (x, y, w, h) in bubbles:
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(debug_img, (x + w // 2, y + h // 2), 3, (0, 0, 255), -1)
        cv2.imwrite(output_path, debug_img)
        print(f"   📸 Debug image saved: {output_path}")

    @staticmethod
    def draw_answer_grid(
        image: np.ndarray,
        left_col: dict,
        right_col: dict,
        answers: list,
        output_path: str = "debug_answers.png"
    ):
        """
        Detected answer positions image এ draw করে — debugging এর জন্য
        """
        vis = image.copy()
        options = ['A', 'B', 'C', 'D']

        def _draw_col(col_cfg, answers_slice, q_offset):
            for q_i, y in enumerate(col_cfg["row_y"]):
                q_num = q_i + q_offset
                ans   = answers_slice[q_i] if q_i < len(answers_slice) else None
                for o_i, x in enumerate(col_cfg["option_x"]):
                    bw = col_cfg["bubble_width"]
                    bh = col_cfg["bubble_height"]
                    color = (0, 255, 0) if options[o_i] == ans else (200, 200, 200)
                    cv2.rectangle(vis, (x, y), (x + bw, y + bh), color, 2)
                # Label
                cv2.putText(vis, f"Q{q_num}", (col_cfg["option_x"][0] - 40, y + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        _draw_col(left_col,  answers[:10],  1)
        _draw_col(right_col, answers[10:20], 11)
        cv2.imwrite(output_path, vis)
        print(f"   📸 Answer grid debug saved: {output_path}")



















