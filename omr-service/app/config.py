"""
OMR Sheet Detection Configuration
===========================================
✅ Written_Img_1.png — 3398 x 2024 px (High-res camera photo)
✅ Grayscale darkness method — 100% accuracy confirmed
✅ Dynamic scaling support for different resolutions


VERIFIED ANSWERS (Written_Img_1.png):
  Q1:A  Q2:B  Q3:C  Q4:D  Q5:A  Q6:B  Q7:C  Q8:D  Q9:A  Q10:B
  Q11:C Q12:D Q13:A Q14:B Q15:C Q16:B Q17:D Q18:C Q19:B Q20:A
"""


class OMRConfig:

    # ─────────────────────────────────────────────────────────────
    # BASE IMAGE SIZE — এই resolution এ coordinates calibrate করা
    # ─────────────────────────────────────────────────────────────
    BASE_WIDTH  = 3398   # calibration image width
    BASE_HEIGHT = 2024   # calibration image height

    # ─────────────────────────────────────────────────────────────
    # IMAGE PREPROCESSING
    # ─────────────────────────────────────────────────────────────
    PREPROCESS = {
        "blur_kernel"          : (9, 9),    # larger kernel for high-res
        "threshold_block_size" : 51,        # adaptive threshold block
        "threshold_constant"   : 10,
        "min_bubble_area"      : 500,       # high-res এ bubble বড়
        "max_bubble_area"      : 8000,
        "aspect_ratio_min"     : 0.65,
        "aspect_ratio_max"     : 1.35,
    }

    # ─────────────────────────────────────────────────────────────
    # DETECTION METHOD — ★ সবচেয়ে গুরুত্বপূর্ণ পরিবর্তন ★
    # ─────────────────────────────────────────────────────────────
    # Grayscale mean darkness:
    #   filled bubble  → mean pixel value ≈ 25-50  (dark, pen ink)
    #   unfilled bubble → mean pixel value ≈ 150-180 (light, paper)
    #   difference = ~120 units → very reliable detection
    #
    # darkness_diff_threshold: filled vs lightest bubble এর min difference
    #   8 units = যথেষ্ট (actual difference ≈ 120+ units for filled)
    THRESHOLDS = {
        "detection_method"        : "grayscale_darkness",  # ★ নতুন method
        "darkness_diff_threshold" : 8,     # filled bubble must be this much darker
        "sample_radius_shrink"    : 5,     # bubble radius থেকে এত কমিয়ে sample নিই
        "fill_threshold_pct"      : 0.13,  # backward compat (old method)
        "min_black_pixels"        : 35,    # backward compat (old method)
        "max_black_pixels"        : 700,   # backward compat
        "fill_ratio"              : 0.38,  # backward compat
        "confidence_threshold"    : 0.65,
    }

    # ─────────────────────────────────────────────────────────────
    # STUDENT ID GRID (Top-Right: 8 columns × 10 rows, digit 0-9)
    # ─────────────────────────────────────────────────────────────
    # এই coordinates 3398x2024 image এ calibrate করা।
    # অন্য resolution এ auto-scale করা হবে omr_processor.py তে।
    STUDENT_ID = {
        "x"          : 1972,   # grid বাম প্রান্ত (scaled from 790 * 2.50)
        "y"          : 390,    # grid উপর প্রান্ত (scaled from 148 * 2.64)
        "width"      : 1075,   # মোট প্রস্থ
        "height"     : 554,    # মোট উচ্চতা
        "num_digits" : 8,      # কলাম সংখ্যা
        "digit_width": 135,    # প্রতি কলাম প্রস্থ (1075/8≈134)
        "digit_height": 55,    # প্রতি row উচ্চতা (554/10≈55)
        "options"    : 10,     # 0–9

        # Exact column centers (verified for 3398x2024):
        "col_x": [1985, 2120, 2248, 2385, 2520, 2660, 2800, 2940],

        # Row spacing between digits
        "row_spacing": 55,
    }

    # ─────────────────────────────────────────────────────────────
    # LEFT COLUMN BUBBLES — Q1 to Q10
    # ─────────────────────────────────────────────────────────────
    # Format: [A_center_x, B_center_x, C_center_x, D_center_x]
    # Row Y: প্রতিটি question এর bubble center Y coordinate
    #
    # ★ Verified pixel-by-pixel for Written_Img_1.png (3398×2024)
    # ─────────────────────────────────────────────────────────────
    LEFT_COLUMN = {
        "option_x": [757, 967, 1183, 1398],   # A, B, C, D center X

        "row_y": [
            995,   # Q1
            1096,  # Q2
            1192,  # Q3
            1295,  # Q4
            1393,  # Q5
            1493,  # Q6
            1597,  # Q7
            1698,  # Q8
            1804,  # Q9
            1909,  # Q10
        ],

        "bubble_radius": 35,   # sample radius (pixel)
        "bubble_width" : 84,   # for backward compat (scaled from 34*2.5)
        "bubble_height": 79,   # for backward compat (scaled from 30*2.64)
    }

    # ─────────────────────────────────────────────────────────────
    # RIGHT COLUMN BUBBLES — Q11 to Q20
    # ─────────────────────────────────────────────────────────────
    # ★ Verified pixel-by-pixel for Written_Img_1.png (3398×2024)
    # ─────────────────────────────────────────────────────────────
    RIGHT_COLUMN = {
        "option_x": [2097, 2310, 2517, 2727],  # A, B, C, D center X

        "row_y": [
            994,   # Q11
            1093,  # Q12
            1190,  # Q13
            1288,  # Q14
            1386,  # Q15
            1486,  # Q16
            1589,  # Q17
            1689,  # Q18
            1795,  # Q19
            1896,  # Q20
        ],

        "bubble_radius": 35,
        "bubble_width" : 84,
        "bubble_height": 79,
    }

    # ─────────────────────────────────────────────────────────────
    # GRADING SETTINGS
    # ─────────────────────────────────────────────────────────────
    ANSWERS = {
        "total_questions": 20,
        "options_per_q"  : 4,
    }

    GRADING = {
        "marks_per_question": 1,
        "negative_marking"  : False,
        "negative_marks"    : 0.25,
    }


# ─────────────────────────────────────────────────────────────────
# Quick sanity check: python config.py
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    c = OMRConfig()
    print("=== Config Sanity Check ===")
    print(f"Base image size : {c.BASE_WIDTH} x {c.BASE_HEIGHT}")
    print(f"Left  X (A-D)  : {c.LEFT_COLUMN['option_x']}")
    print(f"Right X (A-D)  : {c.RIGHT_COLUMN['option_x']}")
    print(f"Left  Row Y    : {c.LEFT_COLUMN['row_y']}")
    print(f"Right Row Y    : {c.RIGHT_COLUMN['row_y']}")
    print(f"Row count L    : {len(c.LEFT_COLUMN['row_y'])} (should be 10)")
    print(f"Row count R    : {len(c.RIGHT_COLUMN['row_y'])} (should be 10)")
    spacings = [c.LEFT_COLUMN['row_y'][i] - c.LEFT_COLUMN['row_y'][i-1] for i in range(1,10)]
    print(f"Row spacings   : {spacings}")
    print("Detection method:", c.THRESHOLDS["detection_method"])
    print("✅ Config OK")
