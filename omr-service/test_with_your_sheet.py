# """
# Test Script — OMR Sheet (Phone Camera Image)
# =============================================
# Usage:
#   python test_with_your_sheet.py
#   python test_with_your_sheet.py --image PATH
#   python test_with_your_sheet.py --debug
# """

# import sys
# import os
# import json

# script_dir = os.path.dirname(os.path.abspath(__file__))
# if script_dir not in sys.path:
#     sys.path.insert(0, script_dir)

# # Also try parent/app layout
# app_dir = os.path.join(os.path.dirname(script_dir), "app")
# if os.path.isdir(app_dir) and app_dir not in sys.path:
#     sys.path.insert(0, app_dir)

# try:
#     from omr_processor import OMRProcessor
#     print("✅ Import: omr_processor")
# except ImportError:
#     try:
#         from app.omr_processor import OMRProcessor
#         print("✅ Import: app.omr_processor")
#     except ImportError as e:
#         print(f"❌ Import failed: {e}")
#         sys.exit(1)


# def test_with_your_sheet(image_path: str, debug: bool = False) -> dict:
#     print("=" * 60)
#     print(f"  Testing: {image_path}")
#     print("=" * 60)

#     if not os.path.exists(image_path):
#         print(f"❌ File not found: {image_path}")
#         return {}

#     with open(image_path, "rb") as f:
#         image_bytes = f.read()

#     print(f"  File size: {len(image_bytes)/1024:.1f} KB\n")

#     processor = OMRProcessor()
#     result = processor.process_image(image_bytes, debug=debug)

#     print("\n" + "=" * 60)
#     print("  PROCESSING RESULT")
#     print("=" * 60)
#     print(f"  Success     : {result.get('success')}")

#     if result.get("success"):
#         print(f"  Student ID  : {result.get('student_id', 'N/A')}")
#         print(f"  Image Type  : {result.get('image_type', 'N/A')}")
#         print(f"  Answered    : {result.get('total_answered')}/{result.get('total_questions')}")
#         print(f"  Blank       : {result.get('total_blank')}")
#         print(f"  Confidence  : {result.get('confidence', 0)*100:.1f}%")

#         print("\n  📝 Detected Answers:")
#         print("  " + "-" * 40)
#         answers = result.get("answers", [])
#         for i in range(10):
#             q_left, q_right = i + 1, i + 11
#             ans_l = answers[i] if i < len(answers) else None
#             ans_r = answers[i + 10] if i + 10 < len(answers) else None
#             print(f"    Q{q_left:2d}: {ans_l or '---':<16} Q{q_right:2d}: {ans_r or '---'}")
#     else:
#         print(f"  Error: {result.get('error')}")

#     return result


# def generate_grading_report(answer_key: dict, result: dict) -> None:
#     if not result.get("success"):
#         print("\n❌ Cannot grade — processing failed.")
#         return

#     answers = result.get("answers", [])
#     print("\n" + "=" * 60)
#     print("  GRADING REPORT")
#     print("=" * 60)
#     print(f"  Student ID : {result.get('student_id', 'N/A')}\n")
#     print(f"  {'Q#':<5} {'Student':<10} {'Key':<10} {'Status'}")
#     print("  " + "-" * 40)

#     correct = wrong = blank = 0
#     for q_str, correct_ans in answer_key.items():
#         q_idx = int(q_str) - 1
#         student_ans = answers[q_idx] if q_idx < len(answers) else None

#         if student_ans is None:
#             blank += 1
#             status = "○ Blank"
#         elif student_ans.upper() == correct_ans.upper():
#             correct += 1
#             status = "✓ Correct"
#         else:
#             wrong += 1
#             status = "✗ Wrong"

#         print(f"  {q_str:<5} {(student_ans or '-'):<10} {correct_ans:<10} {status}")

#     total = len(answer_key)
#     percentage = (correct / total * 100) if total > 0 else 0
#     if   percentage >= 80: grade = "A+"
#     elif percentage >= 70: grade = "A"
#     elif percentage >= 60: grade = "A-"
#     elif percentage >= 50: grade = "B"
#     elif percentage >= 40: grade = "C"
#     elif percentage >= 33: grade = "D"
#     else: grade = "F"

#     print("  " + "=" * 40)
#     print(f"\n  Correct    : {correct}/{total}")
#     print(f"  Wrong      : {wrong}")
#     print(f"  Blank      : {blank}")
#     print(f"  Score      : {percentage:.1f}%")
#     print(f"  Grade      : {grade}\n")


# if __name__ == "__main__":
#     import argparse

#     parser = argparse.ArgumentParser(description="OMR Sheet Test")
#     # parser.add_argument("--image", type=str, default="test_images/omr_or_1.jpeg",
#     # parser.add_argument("--image", type=str, default="test_images/omr_or_1.jpeg",
#     parser.add_argument("--image", type=str, default="test_images/omr_or_2.jpeg",
#                         help="Path to OMR sheet image")
#     parser.add_argument("--debug", action="store_true",
#                         help="Save debug visualization")
#     parser.add_argument("--key", type=str, default=None,
#                         help='Answer key JSON: \'{"1":"A","2":"B",...}\'')
#     args = parser.parse_args()

#     result = test_with_your_sheet(args.image, debug=args.debug)

#     if args.key:
#         answer_key = json.loads(args.key)
#     else:
#         # Ground truth for the sample sheet (omr_or_1.jpeg)
#         answer_key = {
#             "1": "B",  "2": "B",  "3": "A",  "4": "B",  "5": "D",
#             "6": "B",  "7": "C",  "8": "D",  "9": "A",  "10": "D",
#             "11": "B", "12": "A", "13": "D", "14": "A", "15": "B",
#             "16": "A", "17": "C", "18": "D", "19": "B", "20": "A",
#         }
#         print("\n  ℹ️  Using default answer key (sample sheet ground truth)")
#         print("     Pass --key '{...}' to use your own answer key")

#     if result.get("success"):
#         generate_grading_report(answer_key, result)

#     if args.debug:
#         print("  💾 Debug image: debug_answers.png")

















# ------------------------------- test: 


"""
Manual backend test — no database needed.
Usage:
  python test.py
  python test.py --image test_images/omr_or_2.jpeg
  python test.py --image path/to/any_sheet.jpg --key answer_key.json
"""

import sys
import os
import json
import argparse

# allow import from app/ or current folder
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "app"))
if os.path.isdir(os.path.join(HERE, "app")):
    sys.path.insert(0, os.path.join(HERE, "app"))

try:
    from omr_processor import OMRProcessor
except ImportError:
    from app.omr_processor import OMRProcessor


# Default answer key for omr_or_2 style sheet (change per exam)
DEFAULT_KEY = {
    "1": "A",  "2": "B",  "3": "C",  "4": "D",  "5": "C",
    "6": "B",  "7": "A",  "8": "B",  "9": "C",  "10": "D",
    "11": "A", "12": "B", "13": "C", "14": "D", "15": "C",
    "16": "B", "17": "A", "18": "B", "19": "C", "20": "D",
}


def main():
    parser = argparse.ArgumentParser(description="OMR manual test (no DB)")
    # parser.add_argument("--image", default="test_images/omr_or_2.jpeg", help="Student sheet image")
    # parser.add_argument("--image", default="test_images/omr_or_1.jpeg", help="Student sheet image")
    parser.add_argument("--image", default="test_images/omr_or_3.jpeg", help="Student sheet image")
    parser.add_argument("--key", default=None, help="Path to answer_key.json")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"❌ Image not found: {args.image}")
        sys.exit(1)

    if args.key and os.path.exists(args.key):
        with open(args.key, encoding="utf-8") as f:
            answer_key = json.load(f)
        print(f"📋 Answer key loaded: {args.key}")
    else:
        answer_key = DEFAULT_KEY
        print("📋 Using built-in answer key (edit DEFAULT_KEY or pass --key file.json)")

    with open(args.image, "rb") as f:
        data = f.read()

    print(f"\n🔍 Processing: {args.image} ({len(data)/1024:.1f} KB)")
    proc = OMRProcessor()
    result = proc.process_image(data, debug=args.debug)

    if not result.get("success"):
        print("❌ Failed:", result.get("error"))
        sys.exit(1)

    answers = result["answers"]
    print("\n" + "=" * 50)
    print("  DETECTED ANSWERS")
    print("=" * 50)
    print(f"  Student ID : {result.get('student_id')}")
    for i in range(10):
        a = answers[i] or "---"
        b = answers[i+10] or "---"
        print(f"  Q{i+1:2d}: {a:<6}  Q{i+11:2d}: {b}")

    grading = proc.grade_exam(answers, answer_key)

    print("\n" + "=" * 50)
    print("  GRADING")
    print("=" * 50)
    print(f"  {'Q':<4} {'Got':<6} {'Key':<6} Status")
    print("  " + "-" * 36)
    for d in grading["details"]:
        got = d["student"] or "-"
        st = {"correct": "✓", "wrong": "✗", "blank": "○"}[d["status"]]
        print(f"  {d['question']:<4} {got:<6} {d['correct'] or '-':<6} {st}")
    print("  " + "=" * 36)
    print(f"  Correct : {grading['correct']}/{grading['total']}")
    print(f"  Wrong   : {grading['wrong']}")
    print(f"  Blank   : {grading['blank']}")
    print(f"  Score   : {grading['percentage']}%")
    print(f"  Grade   : {grading['grade']}")
    print()


if __name__ == "__main__":
    main()
