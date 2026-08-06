

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
    parser.add_argument("--image", default="test_images/omr_or_4.jpg", help="Student sheet image")
    # parser.add_argument("--image", default="test_images/omr_or_1.jpeg", help="Student sheet image")
    # parser.add_argument("--image", default="test_images/omr_or_3.jpeg", help="Student sheet image")
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
