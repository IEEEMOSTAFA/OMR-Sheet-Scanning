"""
Test Script — OMR Sheet (Written/Camera Image)
================================================
Usage:
  python test_with_your_sheet.py
  python test_with_your_sheet.py --debug        (debug image with img::)
  python test_with_your_sheet.py --image PATH   ( Others :  image  test)

Expected result for Written_Img_1.png:
  Q1:A  Q2:B  Q3:C  Q4:D  Q5:A
  Q6:B  Q7:C  Q8:D  Q9:A  Q10:B
  Q11:C Q12:D Q13:A Q14:B Q15:C
  Q16:B Q17:D Q18:C Q19:B Q20:A
"""

import sys
import os
import json

# ─── Import fix: when running from the app/ folder ───
# If you run this script from the omr-service/ root:
#   python app/test_with_your_sheet.py
# then you do not need to add the path below.
# But if you run it from inside the app/ folder:
#   cd app && python test_with_your_sheet.py

# Automatically fix import path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Try both import styles
try:
    from omr_processor import OMRProcessor
    print("✅ Import: local (app/ folder)")
except ImportError:
    try:
        from app.omr_processor import OMRProcessor
        print("✅ Import: app.omr_processor")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("   Run from: omr-service/ root, or from app/ folder")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────
def test_with_your_sheet(image_path: str, debug: bool = False) -> dict:
    """
    OMR sheet image প্রসেস করে result দেখায়।
    """
    print("=" * 60)
    print(f"  Testing: {image_path}")
    print("=" * 60)

    if not os.path.exists(image_path):
        print(f"❌ File not found: {image_path}")
        return {}

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    print(f"  File size: {len(image_bytes)/1024:.1f} KB\n")

    processor = OMRProcessor()
    result = processor.process_image(image_bytes, debug=debug)

    print("\n" + "=" * 60)
    print("  PROCESSING RESULT")
    print("=" * 60)
    print(f"  Success     : {result.get('success')}")

    if result.get("success"):
        print(f"  Student ID  : {result.get('student_id', 'N/A')}")
        print(f"  Image Type  : {result.get('image_type', 'N/A')}")
        print(f"  Answered    : {result.get('total_answered')}/{result.get('total_questions')}")
        print(f"  Blank       : {result.get('total_blank')}")
        print(f"  Confidence  : {result.get('confidence', 0)*100:.1f}%")

        print("\n  📝 Detected Answers:")
        print("  " + "-" * 40)
        answers = result.get("answers", [])

        # two column print
        for i in range(10):
            q_left  = i + 1
            q_right = i + 11
            ans_l   = answers[i]      if i    < len(answers) else None
            ans_r   = answers[i + 10] if i+10 < len(answers) else None
            l_str   = f"Q{q_left:2d}: {ans_l or '---'}"
            r_str   = f"Q{q_right:2d}: {ans_r or '---'}"
            print(f"    {l_str:<20} {r_str}")

    else:
        print(f"  Error: {result.get('error')}")

    return result


# ─────────────────────────────────────────────────────────────────
def generate_grading_report(answer_key: dict, result: dict) -> None:
    """
    Answer key দিয়ে grading report তৈরি করে।
    """
    if not result.get("success"):
        print("\n❌ Cannot grade — processing failed.")
        return

    answers = result.get("answers", [])

    print("\n" + "=" * 60)
    print("  GRADING REPORT")
    print("=" * 60)
    print(f"  Student ID : {result.get('student_id', 'N/A')}")
    print()

    # Header
    print(f"  {'Q#':<5} {'Student':<10} {'Key':<10} {'Status'}")
    print("  " + "-" * 40)

    correct = wrong = blank = 0

    for q_str, correct_ans in answer_key.items():
        q_idx      = int(q_str) - 1
        student_ans = answers[q_idx] if q_idx < len(answers) else None

        if student_ans is None:
            blank += 1
            status = "○ Blank"
        elif student_ans.upper() == correct_ans.upper():
            correct += 1
            status = "✓ Correct"
        else:
            wrong += 1
            status = f"✗ Wrong"

        print(f"  {q_str:<5} {(student_ans or '-'):<10} {correct_ans:<10} {status}")

    total      = len(answer_key)
    percentage = (correct / total * 100) if total > 0 else 0

    # Grade
    if   percentage >= 80: grade = "A+"
    elif percentage >= 70: grade = "A"
    elif percentage >= 60: grade = "A-"
    elif percentage >= 50: grade = "B"
    elif percentage >= 40: grade = "C"
    elif percentage >= 33: grade = "D"
    else:                   grade = "F"

    print("  " + "=" * 40)
    print(f"\n  Correct    : {correct}/{total}")
    print(f"  Wrong      : {wrong}")
    print(f"  Blank      : {blank}")
    print(f"  Score      : {percentage:.1f}%")
    print(f"  Grade      : {grade}")
    print()


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OMR Sheet Test")
    parser.add_argument(
        "--image", type=str,
        default="./test_images/Written_Img_1.png",
        help="Path to OMR sheet image"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Save debug visualization image"
    )
    parser.add_argument(
        "--key", type=str, default=None,
        help='Answer key JSON: \'{"1":"A","2":"B",...}\''
    )
    args = parser.parse_args()

    # ── Process image ──
    result = test_with_your_sheet(args.image, debug=args.debug)

    # ── Grade (answer key দিলে) ──
    if args.key:
        answer_key = json.loads(args.key)
    else:
        # ★ Written_Img_1.png এর actual answers (image দেখে verify করা)
        answer_key = {
            "1": "A",  "2": "B",  "3": "C",  "4": "D",  "5": "A",
            "6": "B",  "7": "C",  "8": "D",  "9": "A",  "10": "B",
            "11": "C", "12": "D", "13": "A", "14": "B", "15": "C",
            "16": "B", "17": "D", "18": "C", "19": "B", "20": "A",
        }
        print("\n  ℹ️  Using default answer key (Written_Img_1.png actual answers)")
        print("     Pass --key '{...}' to use your own answer key")

    if result.get("success"):
        generate_grading_report(answer_key, result)

    if args.debug:
        print("  💾 Debug image saved as: debug_answers.png")


