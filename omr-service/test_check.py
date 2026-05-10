import cv2
import numpy as np
from app.omr_processor import OMRProcessor
from app.config import OMRConfig

def draw_student_id_boxes(image, cfg):
    debug = image.copy()
    id_cfg = cfg.STUDENT_ID

    for col in range(id_cfg["num_digits"]):
        col_x = id_cfg["x"] + col * id_cfg["digit_width"]
        for row in range(id_cfg["options"]):
            y_pos = id_cfg["y"] + row * id_cfg["digit_height"]
            cv2.rectangle(
                debug,
                (col_x, y_pos),
                (col_x + id_cfg["digit_width"], y_pos + id_cfg["digit_height"]),
                (0, 255, 0), 1
            )
            cv2.putText(
                debug, str(row),
                (col_x + 2, y_pos + 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1
            )

    cv2.imwrite("debug_student_id_grid.png", debug)
    print("✅ debug_student_id_grid.png saved")


def draw_answer_boxes(image, cfg):
    debug = image.copy()
    options = ['A', 'B', 'C', 'D']

    for q_idx, y_pos in enumerate(cfg.LEFT_COLUMN["row_y"]):
        for opt_i, x_pos in enumerate(cfg.LEFT_COLUMN["option_x"]):
            cv2.rectangle(
                debug,
                (x_pos, y_pos),
                (x_pos + cfg.LEFT_COLUMN["bubble_width"], y_pos + cfg.LEFT_COLUMN["bubble_height"]),
                (0, 0, 255), 1
            )
            cv2.putText(
                debug, f"Q{q_idx+1}{options[opt_i]}",
                (x_pos + 2, y_pos + 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1
            )

    for q_idx, y_pos in enumerate(cfg.RIGHT_COLUMN["row_y"]):
        for opt_i, x_pos in enumerate(cfg.RIGHT_COLUMN["option_x"]):
            cv2.rectangle(
                debug,
                (x_pos, y_pos),
                (x_pos + cfg.RIGHT_COLUMN["bubble_width"], y_pos + cfg.RIGHT_COLUMN["bubble_height"]),
                (255, 0, 0), 1
            )
            cv2.putText(
                debug, f"Q{q_idx+11}{options[opt_i]}",
                (x_pos + 2, y_pos + 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1
            )

    cv2.imwrite("debug_answer_grid.png", debug)
    print("✅ debug_answer_grid.png saved")


def run_full_check(image_path):
    print(f"\n📸 Loading: {image_path}")
    image = cv2.imread(image_path)

    if image is None:
        print("❌ Image load failed!")
        return

    print(f"   Size: {image.shape[1]} x {image.shape[0]} px")

    cfg = OMRConfig

    draw_student_id_boxes(image, cfg)
    draw_answer_boxes(image, cfg)

    processor = OMRProcessor()
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    result = processor.process_image(image_bytes)

    print("\n" + "="*50)
    print("📋 RESULT SUMMARY")
    print("="*50)
    print(f"Student ID   : {result.get('student_id')}")
    print(f"Total Answered: {result.get('total_answered')} / {result.get('total_questions')}")
    print(f"Answers:")
    for i, ans in enumerate(result.get('answers', [])):
        print(f"   Q{i+1:2d} → {ans or '---'}")
    print("="*50)


if __name__ == "__main__":
    run_full_check("test_images/Perfect_filled.png")