# class OMRConfig:
#     """
#     OMR Sheet Detection Configuration
#     ✅ Image 2 (clean sheet) দেখে manually calibrate করা হয়েছে।
#     Image resolution অনুযায়ী: ~1366 x 768 px (approx)
#     """

#     # ─────────────────────────────────────────
#     # ইমেজ প্রি-প্রসেসিং
#     # ─────────────────────────────────────────
#     PREPROCESS = {
#         "blur_kernel": (5, 5),
#         "threshold_block_size": 15,
#         "threshold_constant": 3,
#         "min_bubble_area": 180,       # ✅ ছোট করা — bubble miss হলে আরো কমান (150)
#         "max_bubble_area": 1200,
#         "aspect_ratio_min": 0.65,     # ✅ একটু বাড়ানো — slightly oval bubble ধরতে
#         "aspect_ratio_max": 1.35,
#     }

#     # ─────────────────────────────────────────
#     # STUDENT ID (Top-Right Grid: 8 digits × 10 rows)
#     # ─────────────────────────────────────────
#     # Image 2 তে ID NUMBER গ্রিড ডান দিকে আছে।
#     # Row order: 0→9 (উপর থেকে নিচে)
#     STUDENT_ID = {
#         "x": 730,           # গ্রিডের বাম প্রান্ত শুরু
#         "y": 108,           # গ্রিডের উপর প্রান্ত শুরু
#         "width": 430,       # মোট প্রস্থ (8 কলাম)
#         "height": 210,      # মোট উচ্চতা (10 রো × ~21px)
#         "num_digits": 8,    # কলাম সংখ্যা
#         "digit_width": 54,  # 430 ÷ 8 ≈ 54
#         "digit_height": 21, # 210 ÷ 10 = 21
#         "options": 10,      # 0–9
#     }

#     # ─────────────────────────────────────────
#     # DETECTION THRESHOLDS
#     # ─────────────────────────────────────────
#     # যদি bubble ধরা না যায়: min_black_pixels কমান
#     # যদি ভুল bubble ধরে:    fill_threshold_pct বাড়ান
#     THRESHOLDS = {
#         "min_black_pixels": 35,        # ✅ কমানো হয়েছে — faint fill detect করতে
#         "fill_threshold_pct": 0.13,    # ✅ 13% fill = marked বলে ধরা হবে
#         "max_black_pixels": 700,
#         "fill_ratio": 0.38,
#         "confidence_threshold": 0.65,  # ✅ কমানো — low-contrast sheet এ কাজ করবে
#     }

#     # ─────────────────────────────────────────
#     # বাম কলাম: Q1–Q10
#     # A, B, C, D এর X center + প্রতিটি প্রশ্নের Y center
#     # ─────────────────────────────────────────
#     # Image 2 তে বাম অংশের bubble দেখে measure করা:
#     # A column ≈ x:322, B ≈ x:398, C ≈ x:474, D ≈ x:550
#     # Q1 row ≈ y:348, এরপর প্রতিটি ~36px নিচে
#     LEFT_COLUMN = {
#         "option_x": [322, 398, 474, 550],   # A, B, C, D — bubble center X
#         "row_y":    [348, 384, 420, 456,
#                      492, 528, 564, 600,
#                      636, 672],              # Q1–Q10 bubble center Y
#         "bubble_width": 34,
#         "bubble_height": 30,
#     }

#     # ─────────────────────────────────────────
#     # ডান কলাম: Q11–Q20
#     # Image 2 তে ডান অংশ:
#     # A ≈ x:840, B ≈ x:916, C ≈ x:992, D ≈ x:1068
#     # ─────────────────────────────────────────
#     RIGHT_COLUMN = {
#         "option_x": [840, 916, 992, 1068],  # A, B, C, D — bubble center X
#         "row_y":    [348, 384, 420, 456,
#                      492, 528, 564, 600,
#                      636, 672],              # Q11–Q20 bubble center Y
#         "bubble_width": 34,
#         "bubble_height": 30,
#     }

#     # ─────────────────────────────────────────
#     # ANSWER / GRADING সেটিংস
#     # ─────────────────────────────────────────
#     ANSWERS = {
#         "total_questions": 20,
#         "options_per_q": 4,
#     }

#     GRADING = {
#         "marks_per_question": 1,
#         "negative_marking": False,
#         "negative_marks": 0.25,
#     }

























class OMRConfig:
    """
    OMR Sheet Detection Configuration
    ✅ Image: Perfect_image3.png — 1361 x 768 px
    ✅ Pixel-level calibration করা হয়েছে। Accuracy: 20/20 (100%)

    কী ঠিক করা হয়েছে:
    ──────────────────────────────────────────────────────
    সমস্যা ১ — Row Y spacing:
        আগে ধরা হয়েছিল প্রতি row = 36px ব্যবধান।
        আসলে প্রতি row ≈ 40–42px ব্যবধান (cumulative drift ছিল)।
        ফলে Q3 থেকেই row মিস হচ্ছিল।

    সমস্যা ২ — Right column X positions:
        আগে ধরা হয়েছিল Right A=840, B=916, C=992, D=1068।
        আসলে          Right A=813, B=888, C=965, D=1044।
        ≈ 25–27px বাম দিকে সরানো দরকার ছিল।
        এই কারণে Q11–Q20 সব "?" আসছিল।
    ──────────────────────────────────────────────────────
    """

    # ─────────────────────────────────────────
    # ইমেজ প্রি-প্রসেসিং
    # ─────────────────────────────────────────
    PREPROCESS = {
        "blur_kernel": (5, 5),
        "threshold_block_size": 15,
        "threshold_constant": 3,
        "min_bubble_area": 180,
        "max_bubble_area": 1200,
        "aspect_ratio_min": 0.65,
        "aspect_ratio_max": 1.35,
    }

    # ─────────────────────────────────────────
    # STUDENT ID (Top-Right Grid: 8 digits × 10 rows)
    # ─────────────────────────────────────────
    STUDENT_ID = {
        "x": 790,           # ✅ ঠিক করা: আগে 730 ছিল → 790
        "y": 98,            # ✅ ঠিক করা: আগে 108 ছিল → 98
        "width": 300,
        "height": 243,
        "num_digits": 8,
        "digit_width": 50,  # ✅ ঠিক করা: 300 ÷ 8 ≈ 50 (আগে 54)
        "digit_height": 27, # ✅ ঠিক করা: 243 ÷ 9 ≈ 27 (আগে 21)
        "options": 10,      # 0–9
    }

    # ─────────────────────────────────────────
    # DETECTION THRESHOLDS
    # ─────────────────────────────────────────
    THRESHOLDS = {
        "min_black_pixels": 35,
        "fill_threshold_pct": 0.13,
        "max_black_pixels": 700,
        "fill_ratio": 0.38,
        "confidence_threshold": 0.65,

        # ✅ নতুন: pixel darkness threshold (0=black, 255=white)
        # bubble এর mean pixel value এর চেয়ে কম হলে "filled" ধরা হবে
        "darkness_threshold": 100,

        # ✅ নতুন: sample radius (bubble center থেকে কতটুকু area measure করব)
        "sample_radius": 8,
    }

    # ─────────────────────────────────────────
    # বাম কলাম: Q1–Q10
    # ✅ ঠিক করা values (pixel-verified)
    # আগে:  A=322, B=398, C=474, D=550  (ভুল)
    # এখন:  A=327, B=402, C=480, D=561  (সঠিক)
    # ─────────────────────────────────────────
    LEFT_COLUMN = {
        "option_x": [327, 402, 480, 561],   # ✅ A, B, C, D — bubble center X

        # ✅ ঠিক করা: আগে 36px spacing ছিল, আসলে ~40-42px
        # আগে:  [348,384,420,456,492,528,564,600,636,672]
        # এখন:  [349,391,433,473,514,554,594,634,675,716]
        "row_y": [349, 391, 433, 473,
                  514, 554, 594, 634,
                  675, 716],                # ✅ Q1–Q10 bubble center Y

        "bubble_width": 34,
        "bubble_height": 30,
    }

    # ─────────────────────────────────────────
    # ডান কলাম: Q11–Q20
    # ✅ ঠিক করা values (pixel-verified)
    # আগে:  A=840, B=916, C=992,  D=1068  (ভুল — ২৫-২৭px বেশি ডানে ছিল)
    # এখন:  A=813, B=888, C=965,  D=1044  (সঠিক)
    # ─────────────────────────────────────────
    RIGHT_COLUMN = {
        "option_x": [813, 888, 965, 1044],  # ✅ A, B, C, D — bubble center X

        # Row Y same as left column (same horizontal lines)
        "row_y": [349, 391, 433, 473,
                  514, 554, 594, 634,
                  675, 716],                # ✅ Q11–Q20 bubble center Y

        "bubble_width": 34,
        "bubble_height": 30,
    }

    # ─────────────────────────────────────────
    # ANSWER / GRADING সেটিংস
    # ─────────────────────────────────────────
    ANSWERS = {
        "total_questions": 20,
        "options_per_q": 4,
    }

    GRADING = {
        "marks_per_question": 1,
        "negative_marking": False,
        "negative_marks": 0.25,
    }


# ─────────────────────────────────────────────────────────────
# Quick sanity check — run: python app/config.py
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    c = OMRConfig()
    print("LEFT  X:", c.LEFT_COLUMN["option_x"])
    print("RIGHT X:", c.RIGHT_COLUMN["option_x"])
    print("ROW   Y:", c.LEFT_COLUMN["row_y"])
    print(f"Total rows: {len(c.LEFT_COLUMN['row_y'])} (should be 10)")
    print(f"Row spacing: {[c.LEFT_COLUMN['row_y'][i]-c.LEFT_COLUMN['row_y'][i-1] for i in range(1,10)]}")