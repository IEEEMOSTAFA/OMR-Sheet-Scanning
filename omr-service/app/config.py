# """
# OMR Sheet Detection Configuration
# ===========================================
# Calibrated for the standard sheet layout (omr_or_1 style)
# Base resolution: 1600 x 561 px
# Works with phone-camera photos of the SAME sheet design
# (slight angle / lighting / resolution differences are OK)
# """


# class OMRConfig:

#     # ─────────────────────────────────────────────────────────────
#     # BASE IMAGE SIZE — coordinates calibrated for this resolution
#     # Other resolutions auto-scale in omr_processor.py
#     # ─────────────────────────────────────────────────────────────
#     BASE_WIDTH  = 1600
#     BASE_HEIGHT = 561

#     # ─────────────────────────────────────────────────────────────
#     # IMAGE PREPROCESSING
#     # ─────────────────────────────────────────────────────────────
#     PREPROCESS = {
#         "blur_kernel"          : (5, 5),
#         "threshold_block_size" : 21,
#         "threshold_constant"   : 5,
#         "min_bubble_area"      : 40,
#         "max_bubble_area"      : 800,
#         "aspect_ratio_min"     : 0.5,
#         "aspect_ratio_max"     : 1.8,
#     }

#     # ─────────────────────────────────────────────────────────────
#     # DETECTION METHOD — grayscale darkness
#     # filled  ≈ 30–70   |  unfilled ≈ 130–200
#     # ─────────────────────────────────────────────────────────────
#     THRESHOLDS = {
#         "detection_method"        : "grayscale_darkness",
#         "darkness_diff_threshold" : 30,   # filled must be this much darker than lightest
#         "sample_radius_shrink"    : 3,
#         "fill_threshold_pct"      : 0.13,
#         "min_black_pixels"        : 20,
#         "max_black_pixels"        : 400,
#         "fill_ratio"              : 0.38,
#         "confidence_threshold"    : 0.65,
#     }

#     # ─────────────────────────────────────────────────────────────
#     # STUDENT ID GRID (8 columns × 10 rows, digit 0–9)
#     # Handwritten ID on sample: 21702066
#     # Note: bubble fills on phone photos are often partial
#     # ─────────────────────────────────────────────────────────────
#     STUDENT_ID = {
#         "x"           : 1060,
#         "y"           : 115,
#         "width"       : 360,
#         "height"      : 180,
#         "num_digits"  : 8,
#         "digit_width" : 40,
#         "digit_height": 14,
#         "options"     : 10,
#         "col_x"       : [1070, 1115, 1160, 1205, 1250, 1295, 1340, 1385],
#         "row_spacing" : 17,
#     }

#     # ─────────────────────────────────────────────────────────────
#     # LEFT COLUMN — Q1 to Q10
#     # option_x = [A, B, C, D] center X
#     # ─────────────────────────────────────────────────────────────
#     LEFT_COLUMN = {
#         "option_x": [158, 235, 312, 389],

#         "row_y": [
#             76,    # Q1
#             118,   # Q2
#             161,   # Q3
#             204,   # Q4
#             247,   # Q5
#             290,   # Q6
#             332,   # Q7
#             376,   # Q8
#             421,   # Q9
#             465,   # Q10
#         ],

#         "bubble_radius": 12,
#         "bubble_width" : 28,
#         "bubble_height": 28,
#     }

#     # ─────────────────────────────────────────────────────────────
#     # RIGHT COLUMN — Q11 to Q20
#     # ─────────────────────────────────────────────────────────────
#     RIGHT_COLUMN = {
#         "option_x": [552, 628, 704, 777],

#         "row_y": [
#             75,    # Q11
#             117,   # Q12
#             160,   # Q13
#             202,   # Q14
#             244,   # Q15
#             286,   # Q16
#             329,   # Q17
#             372,   # Q18
#             415,   # Q19
#             459,   # Q20
#         ],

#         "bubble_radius": 12,
#         "bubble_width" : 28,
#         "bubble_height": 28,
#     }

#     # ─────────────────────────────────────────────────────────────
#     # GRADING
#     # ─────────────────────────────────────────────────────────────
#     ANSWERS = {
#         "total_questions": 20,
#         "options_per_q"  : 4,
#     }

#     GRADING = {
#         "marks_per_question": 1,
#         "negative_marking"  : False,
#         "negative_marks"    : 0.25,
#     }


# if __name__ == "__main__":
#     c = OMRConfig()
#     print("=== Config Sanity Check ===")
#     print(f"Base image size : {c.BASE_WIDTH} x {c.BASE_HEIGHT}")
#     print(f"Left  X (A-D)  : {c.LEFT_COLUMN['option_x']}")
#     print(f"Right X (A-D)  : {c.RIGHT_COLUMN['option_x']}")
#     print(f"Left  rows     : {len(c.LEFT_COLUMN['row_y'])}")
#     print(f"Right rows     : {len(c.RIGHT_COLUMN['row_y'])}")
#     print("Detection method:", c.THRESHOLDS["detection_method"])
#     print("✅ Config OK")



# -------------------------------- test:

"""
OMR Config — RELATIVE coordinates (0.0–1.0 of image width/height)
Works across different phone resolutions of the SAME printed sheet design.
"""

class OMRConfig:

    # Standard size after perspective warp (optional)
    BASE_WIDTH  = 1280
    BASE_HEIGHT = 461

    PREPROCESS = {
        "blur_kernel": (5, 5),
    }

    THRESHOLDS = {
        "detection_method": "grayscale_darkness",
        # filled must be this much darker than lightest option in the row
        "darkness_diff_threshold": 25,
        # local search radius (fraction of min(w,h)) around expected center
        "local_search_frac": 0.012,
        "sample_radius_frac": 0.008,   # bubble sample radius as fraction of min(w,h)
        "sid_darkness_diff_threshold": 15,
    }

    # ── Relative coords: fraction of width (x) / height (y) ──
    # Calibrated from omr_or_2; local-search absorbs small crop differences
    LEFT_COLUMN = {
        # A B C D  as fraction of image width
        "option_x_frac": [0.094, 0.144, 0.195, 0.245],
        # Q1–Q10 row centers as fraction of image height
        "row_y_frac": [
            0.115, 0.193, 0.273, 0.354, 0.432,
            0.512, 0.590, 0.670, 0.748, 0.831,
        ],
    }

    RIGHT_COLUMN = {
        "option_x_frac": [0.350, 0.400, 0.448, 0.496],
        "row_y_frac": [
            0.119, 0.195, 0.271, 0.347, 0.425,
            0.501, 0.579, 0.657, 0.733, 0.811,
        ],
    }

    # STUDENT_ID = {
    #     "num_digits": 8,
    #     "options": 10,
    #     "col_x_frac": [0.639, 0.667, 0.695, 0.723, 0.751, 0.779, 0.807, 0.836],
    #     "y0_frac": 0.156,
    #     "row_spacing_frac": 0.035,
    # }


    # test 


    STUDENT_ID = {
    "y0_frac"         : 0.23904,
    "row_spacing_frac": 0.06574,
    "col_x_frac"      : [0.52987, 0.56481, 0.59925, 0.63362,
                          0.66825, 0.70306, 0.73819, 0.77306],
    "options"         : 10,
}

    ANSWERS = {
        "total_questions": 20,
        "options_per_q": 4,
    }

    GRADING = {
        "marks_per_question": 1,
        "negative_marking": False,
        "negative_marks": 0.25,
    }
