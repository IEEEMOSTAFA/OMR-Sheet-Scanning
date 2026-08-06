
















"""Configuration for the fixed-layout OMR sheet.

All coordinates are measured after the outer black sheet border is
perspective-warped to BASE_WIDTH x BASE_HEIGHT.
"""


class OMRConfig:
    BASE_WIDTH = 1600
    BASE_HEIGHT = 525

    PREPROCESS = {
        "blur_kernel": (5, 5),
        "clahe_clip_limit": 2.0,
        "clahe_grid": (8, 8),
    }

    THRESHOLDS = {
        # Detecting the outer rectangular border
        "warp_min_area_ratio": 0.25,
        "warp_threshold": 120,

        # Bubble sampling
        "sample_radius_frac": 0.0152,       # about 8 px at 525 px height
        "sid_sample_radius_frac": 0.0133,   # about 7 px at 525 px height
        "dark_pixel_threshold": 100,

        # A selected bubble must satisfy an absolute fill condition AND
        # be clearly darker than the second-best bubble in the same row.
        "filled_mean_threshold": 85,
        "filled_ratio_threshold": 0.65,
        "darkness_diff_threshold": 25,
        "sid_darkness_diff_threshold": 25,

        # Student-ID grid auto-alignment. The printed ID block shifts a few
        # pixels between scans even after the outer border is warped.
        "sid_align_search_x_frac": 0.0150,
        "sid_align_search_y_frac": 0.0250,
        "sid_align_annulus_inner_frac": 0.0130,
        "sid_align_annulus_outer_frac": 0.0250,
    }

    # Coordinates calibrated from the perspective-normalized sheet.
    LEFT_COLUMN = {
        "option_x_frac": [0.07950, 0.12931, 0.17850, 0.22888],
        "row_y_frac": [
            0.10000, 0.18857, 0.27619, 0.36310, 0.45167,
            0.54071, 0.62810, 0.71619, 0.80500, 0.89476,
        ],
    }

    RIGHT_COLUMN = {
        "option_x_frac": [0.33338, 0.38294, 0.43275, 0.48175],
        "row_y_frac": [
            0.10000, 0.18857, 0.27619, 0.36310, 0.45167,
            0.54071, 0.62810, 0.71619, 0.80500, 0.89476,
        ],
    }

    STUDENT_ID = {
        "num_digits": 8,
        "options": 10,
        "col_x_frac": [
            0.52831, 0.56506, 0.60213, 0.63956,
            0.67706, 0.71456, 0.75275, 0.79063,
        ],
        "row_y_frac": [
            0.22762, 0.30381, 0.38167, 0.45857, 0.53405,
            0.61167, 0.68905, 0.76571, 0.84262, 0.92048,
        ],
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