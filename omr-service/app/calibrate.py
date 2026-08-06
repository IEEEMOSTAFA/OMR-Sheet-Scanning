


# ------------------ test :::::::::::



"""
OMR Visual Verification Tool (compatible with OMR Processor v5)
================================================================

Purpose
-------
This tool does NOT generate or replace config.py.
It runs the same production OMRProcessor used by the API and creates a
human-readable visual image so you can manually verify:

1. Student ID bubble positions
2. Q1-Q20 selected/blank answers
3. Perspective normalization
4. Per-question confidence

Usage
-----
    python calibrate.py
    python calibrate.py --image test_images/omr_or_1.jpeg
    python calibrate.py --image test_images/omr_or_3.jpeg --expect-filled 11
    python calibrate.py --folder test_images

Outputs
-------
    visual_results/<image-name>/visual_check.jpg
    visual_results/<image-name>/result.json
    visual_results/<image-name>/normalized.png
    visual_results/<image-name>/gray.png
    visual_results/<image-name>/processor_debug.png
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np


# Resolve paths from the file location, not from the current terminal folder.
# Supported layouts:
#   omr-service/calibrate.py
#   omr-service/app/calibrate.py
HERE = Path(__file__).resolve().parent
APP_DIR = HERE if HERE.name.lower() == "app" else HERE / "app"
PROJECT_ROOT = HERE.parent if HERE.name.lower() == "app" else HERE

for candidate in (APP_DIR, PROJECT_ROOT, HERE):
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

try:
    from omr_processor import OMRProcessor
    from config import OMRConfig
except ImportError:
    try:
        from app.omr_processor import OMRProcessor
        from app.config import OMRConfig
    except ImportError as exc:
        print("❌ omr_processor.py/config.py import করা যায়নি।")
        print("   calibrate.py ফাইলটি omr_processor.py এবং config.py-এর পাশে রাখুন।")
        print(f"   Details: {exc}")
        raise SystemExit(1)


DEFAULT_IMAGE = PROJECT_ROOT / "test_images" / "omr_or_1.jpeg"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "visual_results"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
DEBUG_FILENAMES = {
    "debug_normalized.png": "normalized.png",
    "debug_gray.png": "gray.png",
    "debug_omr.png": "processor_debug.png",
}


def _resolve_user_path(raw_path: str, *, expect_directory: bool = False) -> Path:
    """Resolve a CLI path from CWD first, then from the project root."""
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()

    cwd_candidate = (Path.cwd() / candidate).resolve()
    project_candidate = (PROJECT_ROOT / candidate).resolve()

    checker = Path.is_dir if expect_directory else Path.is_file
    if checker(cwd_candidate):
        return cwd_candidate
    if checker(project_candidate):
        return project_candidate

    # Return the project-root interpretation for a clearer error message.
    return project_candidate


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def _px(frac: float, total: int) -> int:
    return int(round(float(frac) * total))


def _put_text(
    image: np.ndarray,
    text: str,
    origin: Tuple[int, int],
    scale: float = 0.55,
    color: Tuple[int, int, int] = (30, 30, 30),
    thickness: int = 1,
) -> None:
    cv2.putText(
        image,
        text,
        origin,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def _run_processor(image_path: Path, output_dir: Path) -> Dict[str, Any]:
    """Run the exact production processor and keep its debug files isolated."""
    output_dir.mkdir(parents=True, exist_ok=True)
    image_bytes = image_path.read_bytes()
    if not image_bytes:
        return {"success": False, "error": "Image file is empty"}

    processor = OMRProcessor()
    old_cwd = Path.cwd()
    try:
        os.chdir(output_dir)
        try:
            result = processor.process_image(
                image_bytes,
                apply_perspective=True,
                debug=True,
            )
        except TypeError:
            result = processor.process_image(image_bytes, debug=True)
    finally:
        os.chdir(old_cwd)

    # Use clear stable names for generated debug files.
    for source_name, target_name in DEBUG_FILENAMES.items():
        source = output_dir / source_name
        target = output_dir / target_name
        if source.exists():
            if target.exists():
                target.unlink()
            source.rename(target)

    return result


def _draw_mcq_overlay(
    image: np.ndarray,
    answers: Sequence[Optional[str]],
    confidences: Sequence[float],
) -> None:
    h, w = image.shape[:2]
    options = ["A", "B", "C", "D"]
    radius = max(8, int(round(OMRConfig.THRESHOLDS["sample_radius_frac"] * min(h, w))))

    selected_color = (0, 180, 0)      # green
    normal_color = (150, 150, 150)    # gray
    blank_color = (0, 165, 255)       # orange
    label_color = (25, 25, 25)

    for column, offset in (
        (OMRConfig.LEFT_COLUMN, 1),
        (OMRConfig.RIGHT_COLUMN, 11),
    ):
        xs = [_px(value, w) for value in column["option_x_frac"]]
        for row_index, y_frac in enumerate(column["row_y_frac"]):
            question_number = offset + row_index
            answer = answers[question_number - 1] if question_number - 1 < len(answers) else None
            confidence = (
                _safe_float(confidences[question_number - 1])
                if question_number - 1 < len(confidences)
                else 0.0
            )
            y = _px(y_frac, h)

            for option_index, x in enumerate(xs):
                option = options[option_index]
                if answer is None:
                    color = blank_color
                    thickness = 2
                elif option == answer:
                    color = selected_color
                    thickness = 3
                else:
                    color = normal_color
                    thickness = 1
                cv2.circle(image, (x, y), radius, color, thickness, cv2.LINE_AA)



def _draw_student_id_overlay(
    image: np.ndarray,
    student_id: str,
    alignment: Dict[str, int],
) -> None:
    h, w = image.shape[:2]
    cfg = OMRConfig.STUDENT_ID
    dx = int(alignment.get("dx", 0))
    dy = int(alignment.get("dy", 0))
    xs = [_px(value, w) + dx for value in cfg["col_x_frac"]]
    ys = [_px(value, h) + dy for value in cfg["row_y_frac"]]

    selected_color = (220, 0, 220)    # magenta
    normal_color = (180, 180, 180)    # gray
    ambiguous_color = (0, 0, 255)     # red

    for column_index, x in enumerate(xs):
        selected_digit = student_id[column_index] if column_index < len(student_id) else "?"
        for digit, y in enumerate(ys):
            if selected_digit == "?":
                color = ambiguous_color
                thickness = 2
            elif selected_digit == str(digit):
                color = selected_color
                thickness = 3
            else:
                color = normal_color
                thickness = 1
            cv2.circle(image, (x, y), 8, color, thickness, cv2.LINE_AA)

        _put_text(
            image,
            selected_digit,
            (x - 5, max(18, ys[0] - 12)),
            scale=0.55,
            color=selected_color if selected_digit != "?" else ambiguous_color,
            thickness=2,
        )


def _build_side_panel(
    height: int,
    width: int,
    image_path: Path,
    result: Dict[str, Any],
    expect_filled: Optional[int],
) -> np.ndarray:
    panel = np.full((height, width, 3), 248, dtype=np.uint8)
    cv2.rectangle(panel, (0, 0), (width - 1, height - 1), (200, 200, 200), 1)

    answers: List[Optional[str]] = list(result.get("answers") or [])
    confidences = list(result.get("answer_confidences") or [])
    total = int(result.get("total_questions") or len(answers) or 20)
    if len(answers) < total:
        answers.extend([None] * (total - len(answers)))
    if len(confidences) < total:
        confidences.extend([0.0] * (total - len(confidences)))

    answered = sum(answer is not None for answer in answers[:total])
    blanks = [index + 1 for index, answer in enumerate(answers[:total]) if answer is None]
    low_conf = [
        index + 1
        for index, answer in enumerate(answers[:total])
        if answer is not None and _safe_float(confidences[index]) < 0.20
    ]

    sid = str(result.get("student_id") or "")
    sid_valid = bool(result.get("student_id_valid", bool(sid) and "?" not in sid))
    count_ok = expect_filled is None or answered == expect_filled
    auto_ok = bool(result.get("success")) and sid_valid and count_ok and not low_conf

    x = 22
    y = 34
    line = 26

    _put_text(panel, "OMR VISUAL CHECK", (x, y), scale=0.72, color=(20, 20, 20), thickness=2)
    y += 38
    _put_text(panel, f"File: {image_path.name}", (x, y), scale=0.46)
    y += line
    _put_text(panel, f"Student ID: {sid or 'NOT DETECTED'}", (x, y), scale=0.57, thickness=2)
    y += line
    _put_text(panel, f"ID valid: {'YES' if sid_valid else 'NO'}", (x, y), scale=0.48)
    y += line
    _put_text(panel, f"ID confidence: {_safe_float(result.get('student_id_confidence')) * 100:.1f}%", (x, y), scale=0.46)
    y += line
    _put_text(panel, f"Answered: {answered}/{total}", (x, y), scale=0.49)
    y += line
    _put_text(panel, f"Blank/unclear: {len(blanks)}", (x, y), scale=0.49)
    y += line
    _put_text(panel, f"Overall confidence: {_safe_float(result.get('confidence')) * 100:.1f}%", (x, y), scale=0.46)
    y += line
    _put_text(panel, f"Perspective warp: {'YES' if result.get('perspective_normalized') else 'NO/FALLBACK'}", (x, y), scale=0.44)
    y += line

    alignment = result.get("student_id_alignment_px") or {}
    _put_text(panel, f"ID align: dx={int(alignment.get('dx', 0)):+d}, dy={int(alignment.get('dy', 0)):+d}", (x, y), scale=0.44)
    y += line

    if expect_filled is not None:
        _put_text(panel, f"Expected filled: {expect_filled}", (x, y), scale=0.46)
        y += line
        _put_text(panel, f"Count check: {'PASS' if count_ok else 'FAIL'}", (x, y), scale=0.48)
        y += line

    y += 5
    status_color = (0, 145, 0) if auto_ok else (0, 0, 220)
    status_text = "AUTO CHECK: OK" if auto_ok else "AUTO CHECK: REVIEW"
    cv2.rectangle(panel, (x - 4, y - 23), (width - 22, y + 11), (235, 235, 235), -1)
    _put_text(panel, status_text, (x, y), scale=0.62, color=status_color, thickness=2)
    y += 38

    _put_text(panel, "Legend", (x, y), scale=0.54, thickness=2)
    y += 24
    legend = [
        ((0, 180, 0), "Green: selected MCQ"),
        ((150, 150, 150), "Gray: unselected bubble"),
        ((0, 165, 255), "Orange: blank/unclear row"),
        ((220, 0, 220), "Magenta: selected ID digit"),
        ((0, 0, 255), "Red: ambiguous ID"),
    ]
    for color, text in legend:
        cv2.circle(panel, (x + 8, y - 5), 6, color, 2, cv2.LINE_AA)
        _put_text(panel, text, (x + 23, y), scale=0.40)
        y += 22

    y += 8
    _put_text(panel, "Detected answers", (x, y), scale=0.54, thickness=2)
    y += 25
    left_x = x
    right_x = x + 195
    for row in range(10):
        q1 = row
        q2 = row + 10
        a1 = answers[q1] if q1 < total else None
        a2 = answers[q2] if q2 < total else None
        c1 = _safe_float(confidences[q1]) if q1 < total else 0.0
        c2 = _safe_float(confidences[q2]) if q2 < total else 0.0
        _put_text(panel, f"Q{q1 + 1:02d}: {a1 or '-':<1}  {c1 * 100:4.0f}%", (left_x, y), scale=0.40)
        if q2 < total:
            _put_text(panel, f"Q{q2 + 1:02d}: {a2 or '-':<1}  {c2 * 100:4.0f}%", (right_x, y), scale=0.40)
        y += 21

    if blanks:
        y += 3
        blank_text = ", ".join(f"Q{number}" for number in blanks)
        _put_text(panel, f"Blank: {blank_text[:46]}", (x, y), scale=0.38, color=(0, 110, 190))
        if len(blank_text) > 46:
            y += 19
            _put_text(panel, blank_text[46:92], (x + 42, y), scale=0.38, color=(0, 110, 190))

    if low_conf:
        y += 20
        _put_text(panel, "Low-confidence: " + ", ".join(f"Q{n}" for n in low_conf), (x, y), scale=0.38, color=(0, 0, 220))

    reminder_y = height - 42
    _put_text(panel, "Detection check only - not grading.", (x, reminder_y), scale=0.40, color=(80, 80, 80))
    _put_text(panel, "Confirm circles match the filled bubbles.", (x, reminder_y + 20), scale=0.40, color=(80, 80, 80))
    return panel

def _create_visual(
    image_path: Path,
    output_dir: Path,
    result: Dict[str, Any],
    expect_filled: Optional[int],
) -> Path:
    normalized_path = output_dir / "normalized.png"
    normalized = cv2.imread(str(normalized_path))
    if normalized is None:
        raw = cv2.imread(str(image_path))
        if raw is None:
            raise ValueError(f"Could not load image: {image_path}")
        normalized = cv2.resize(
            raw,
            (int(OMRConfig.BASE_WIDTH), int(OMRConfig.BASE_HEIGHT)),
            interpolation=cv2.INTER_AREA,
        )

    overlay = normalized.copy()
    answers = list(result.get("answers") or [])
    confidences = list(result.get("answer_confidences") or [])
    _draw_mcq_overlay(overlay, answers, confidences)
    _draw_student_id_overlay(
        overlay,
        str(result.get("student_id") or ""),
        result.get("student_id_alignment_px") or {},
    )

    final_height = max(900, overlay.shape[0])
    if overlay.shape[0] < final_height:
        padded = np.full((final_height, overlay.shape[1], 3), 248, dtype=np.uint8)
        padded[:overlay.shape[0], :overlay.shape[1]] = overlay
        overlay = padded

    panel_width = 430
    panel = _build_side_panel(
        final_height,
        panel_width,
        image_path,
        result,
        expect_filled,
    )
    final = np.hstack([overlay, panel])

    visual_path = output_dir / "visual_check.jpg"
    if not cv2.imwrite(str(visual_path), final, [int(cv2.IMWRITE_JPEG_QUALITY), 94]):
        raise OSError(f"Could not write: {visual_path}")
    return visual_path


def _write_json(
    output_dir: Path,
    image_path: Path,
    result: Dict[str, Any],
    expect_filled: Optional[int],
) -> Path:
    answers = list(result.get("answers") or [])
    payload = dict(result)
    payload["image"] = str(image_path)
    payload["answers_by_question"] = {
        str(index + 1): answer for index, answer in enumerate(answers)
    }
    payload["expected_filled"] = expect_filled

    json_path = output_dir / "result.json"
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return json_path


def verify_image(
    image_path: Path,
    root_output_dir: Path,
    expect_filled: Optional[int] = None,
) -> bool:
    print("\n" + "=" * 70)
    print(f"🔍 Visual verification: {image_path}")
    print("=" * 70)

    if not image_path.exists() or not image_path.is_file():
        print(f"❌ Image পাওয়া যায়নি: {image_path}")
        return False

    output_dir = root_output_dir / image_path.stem
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = _run_processor(image_path, output_dir)
        if not result.get("success"):
            print(f"❌ Detection failed: {result.get('error', 'Unknown error')}")
            return False

        visual_path = _create_visual(image_path, output_dir, result, expect_filled)
        json_path = _write_json(output_dir, image_path, result, expect_filled)

        answers = list(result.get("answers") or [])
        answered = sum(value is not None for value in answers)
        student_id = result.get("student_id")
        sid_valid = bool(result.get("student_id_valid"))
        count_ok = expect_filled is None or answered == expect_filled
        ok = sid_valid and count_ok

        print("\n✅ Detection complete")
        print(f"   Student ID       : {student_id}")
        print(f"   ID valid         : {'YES' if sid_valid else 'NO'}")
        print(f"   Answered         : {answered}/{result.get('total_questions', len(answers))}")
        print(f"   Visual image     : {visual_path}")
        print(f"   JSON result      : {json_path}")
        print("\n📌 visual_check.jpg খুলে দেখুন:")
        print("   • সবুজ circle actual filled MCQ bubble-এর উপর আছে কি না")
        print("   • magenta circle actual Student ID bubble-এর উপর আছে কি না")
        print("   • blank row হলে চারটি orange circle দেখা যাচ্ছে কি না")
        print("   • normalized sheet বেঁকে/কাটা গেছে কি না")
        return ok

    except Exception as exc:
        import traceback

        traceback.print_exc()
        print(f"❌ Visual verification error: {exc}")
        return False


def _images_from_folder(folder: Path) -> Iterable[Path]:
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Visual check for Student ID and MCQ bubble detection (no grading)."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--image",
        default=None,
        help="Single OMR image path",
    )
    group.add_argument(
        "--folder",
        default=None,
        help="Process every image inside a folder",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Folder for visual results",
    )
    parser.add_argument(
        "--expect-filled",
        type=int,
        default=None,
        help="Optional expected number of filled MCQ answers",
    )
    args = parser.parse_args()

    output_dir_arg = Path(args.output_dir).expanduser()
    output_dir = (
        output_dir_arg.resolve()
        if output_dir_arg.is_absolute()
        else (PROJECT_ROOT / output_dir_arg).resolve()
    )

    if args.folder:
        folder = _resolve_user_path(args.folder, expect_directory=True)
        if not folder.is_dir():
            print(f"❌ Folder পাওয়া যায়নি: {folder}")
            return 1
        images = list(_images_from_folder(folder))
        if not images:
            print(f"❌ কোনো image পাওয়া যায়নি: {folder}")
            return 1
        results = [
            verify_image(path, output_dir, expect_filled=args.expect_filled)
            for path in images
        ]
        passed = sum(results)
        print("\n" + "=" * 70)
        print(f"Batch result: {passed}/{len(results)} basic checks passed")
        print(f"Visual outputs: {output_dir}")
        print("=" * 70)
        return 0 if passed == len(results) else 2

    image_path = _resolve_user_path(args.image) if args.image else DEFAULT_IMAGE.resolve()
    return 0 if verify_image(image_path, output_dir, args.expect_filled) else 2


if __name__ == "__main__":
    raise SystemExit(main())