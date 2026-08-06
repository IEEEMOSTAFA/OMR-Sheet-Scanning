"""Project-root launcher for the visual OMR checker.

Run from the omr-service folder:
    python calibrate.py
    python calibrate.py --image test_images/omr_or_2.jpeg
"""

from app.calibrate import main


if __name__ == "__main__":
    raise SystemExit(main())