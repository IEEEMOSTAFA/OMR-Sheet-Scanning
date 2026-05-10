"""
Main OMR Processor
Calibrated for MCQ Answer Sheet
Left column: Q1-Q10 | Right column: Q11-Q20
"""

import cv2
import numpy as np
from typing import Dict, List, Optional
from app.config import OMRConfig
from app.utils import OMRUtils


class OMRProcessor:
    def __init__(self):
        self.config = OMRConfig
        self.utils = OMRUtils
        print("=" * 55)
        print("OMR Processor Initialized")
        print(f"   Total Questions : {self.config.ANSWERS['total_questions']}")
        print(f"   Left col  (Q1-10) : {self.config.LEFT_COLUMN['option_x']}")
        print(f"   Right col (Q11-20): {self.config.RIGHT_COLUMN['option_x']}")
        print("=" * 55)

    def process_image(self, image_bytes: bytes, apply_perspective: bool = False) -> Dict:
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return {"success": False, "error": "Invalid image format or corrupted file"}

            print(f"\nImage: {image.shape[1]} x {image.shape[0]} px")

            if apply_perspective:
                image = self.utils.correct_perspective(image)

            processed = self.utils.preprocess_image(image)
            print("Preprocessed")

            student_id = self._extract_student_id(processed)
            print(f"Student ID: {student_id}")

            answers = self._extract_answers(processed)

            answered = sum(1 for a in answers if a is not None)
            blank = self.config.ANSWERS["total_questions"] - answered

            print(f"Answered: {answered}/{self.config.ANSWERS['total_questions']}")

            return {
                "success": True,
                "student_id": student_id,
                "answers": answers,
                "total_answered": answered,
                "total_blank": blank,
                "total_questions": self.config.ANSWERS["total_questions"],
                "confidence": round(answered / self.config.ANSWERS["total_questions"], 2)
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def _extract_student_id(self, image: np.ndarray) -> str:
        """
        Student ID Extract করুন ID গ্রিড থেকে
        গ্রিড: 8 কলাম × 10 রো (0-9)
        """
        id_cfg = self.config.STUDENT_ID
        digits = []
        
        print(f"\n📖 Student ID Extract করছি:")
        print(f"   Region: x={id_cfg['x']}, y={id_cfg['y']}")
        print(f"   Grid Size: {id_cfg['num_digits']} columns × {id_cfg['options']} rows")
        
        # ডিবাগের জন্য ID রিজিয়ন সেভ করুন
        try:
            id_region = image[
                id_cfg["y"]: id_cfg["y"] + id_cfg["options"] * id_cfg["digit_height"],
                id_cfg["x"]: id_cfg["x"] + id_cfg["num_digits"] * id_cfg["digit_width"]
            ]
            cv2.imwrite("debug_student_id_region.png", id_region)
            print(f"   💾 ID region debug image সেভ করা হয়েছে")
        except Exception as e:
            print(f"   ⚠️ Debug image সেভ করতে পারেনি: {e}")
        
        # প্রতিটি কলামে স্ক্যান করুন
        for col in range(id_cfg["num_digits"]):
            col_x = id_cfg["x"] + col * id_cfg["digit_width"]
            fill_scores = []
            
            print(f"   Column {col+1}: ", end="", flush=True)
            
            # প্রতিটি রো (0-9) চেক করুন
            for row in range(id_cfg["options"]):
                y_pos = id_cfg["y"] + row * id_cfg["digit_height"]
                
                # ROI extract করুন
                roi = image[
                    y_pos: y_pos + id_cfg["digit_height"],
                    col_x: col_x + id_cfg["digit_width"]
                ]
                
                if roi.size < 30:
                    fill_scores.append(0.0)
                    continue
                
                # কালো পিক্সেল গণনা করুন (255 = white/filled in binary)
                black_pixels = int(np.sum(roi == 255))
                fill_pct = black_pixels / roi.size if roi.size > 0 else 0.0
                fill_scores.append(fill_pct)
            
            # সর্বোচ্চ ফিল পারসেন্ট খুঁজুন
            if fill_scores:
                max_fill = max(fill_scores)
                threshold = self.config.THRESHOLDS.get("fill_threshold_pct", 0.15)
                
                if max_fill >= threshold:
                    best_row = fill_scores.index(max_fill)
                    selected = str(best_row)
                    print(f"✅ {selected} ({max_fill:.0%})")
                else:
                    selected = "?"
                    print(f"❌ No clear fill (max: {max_fill:.0%})")
            else:
                selected = "?"
                print(f"❌ Empty ROI")
            
            digits.append(selected)
        
        student_id = "".join(digits)
        print(f"\n🎓 Final Student ID: {student_id}\n")
        return student_id

    def _extract_answers(self, image: np.ndarray) -> List[Optional[str]]:
        """
        সব 20 প্রশ্নের উত্তর Extract করুন
        Q1-Q10  → LEFT_COLUMN
        Q11-Q20 → RIGHT_COLUMN
        """
        options = ['A', 'B', 'C', 'D']
        all_answers = [None] * 20

        # Left Column - Q1 to Q10
        print("\n📝 LEFT COLUMN (Q1-Q10):")
        left = self.config.LEFT_COLUMN
        for q_idx, y_pos in enumerate(left["row_y"]):
            q_num = q_idx + 1
            max_px = 0
            selected = None

            for opt_i, x_pos in enumerate(left["option_x"]):
                roi = image[
                    y_pos: y_pos + left["bubble_height"],
                    x_pos: x_pos + left["bubble_width"]
                ]
                if roi.size > 0:
                    px = int(np.sum(roi == 255))
                    if px > max_px and px > self.config.THRESHOLDS["min_black_pixels"]:
                        max_px = px
                        selected = options[opt_i]

            all_answers[q_num - 1] = selected
            print(f"   Q{q_num:2d}: {selected or '---'} (px={max_px})")

        # Right Column - Q11 to Q20
        print("\n📝 RIGHT COLUMN (Q11-Q20):")
        right = self.config.RIGHT_COLUMN
        for q_idx, y_pos in enumerate(right["row_y"]):
            q_num = q_idx + 11
            max_px = 0
            selected = None

            for opt_i, x_pos in enumerate(right["option_x"]):
                roi = image[
                    y_pos: y_pos + right["bubble_height"],
                    x_pos: x_pos + right["bubble_width"]
                ]
                if roi.size > 0:
                    px = int(np.sum(roi == 255))
                    if px > max_px and px > self.config.THRESHOLDS["min_black_pixels"]:
                        max_px = px
                        selected = options[opt_i]

            all_answers[q_num - 1] = selected
            print(f"   Q{q_num:2d}: {selected or '---'} (px={max_px})")

        return all_answers

    def grade_exam(self, student_answers: List, answer_key: Dict) -> Dict:
        """
        উত্তর কী অনুযায়ী পরীক্ষার গ্রেড দিন
        """
        correct = 0
        wrong = 0
        blank = 0
        details = []

        for i, student_ans in enumerate(student_answers):
            q_num = str(i + 1)
            correct_ans = answer_key.get(q_num)

            if student_ans is None:
                blank += 1
                details.append({"question": i + 1, "student": None,
                                 "correct": correct_ans, "status": "blank"})
            elif student_ans == correct_ans:
                correct += 1
                details.append({"question": i + 1, "student": student_ans,
                                 "correct": correct_ans, "status": "correct"})
            else:
                wrong += 1
                details.append({"question": i + 1, "student": student_ans,
                                 "correct": correct_ans, "status": "wrong"})

        total_q = len(answer_key)
        percentage = (correct / total_q * 100) if total_q > 0 else 0

        if percentage >= 80:   grade = "A+"
        elif percentage >= 70: grade = "A"
        elif percentage >= 60: grade = "A-"
        elif percentage >= 50: grade = "B"
        elif percentage >= 40: grade = "C"
        elif percentage >= 33: grade = "D"
        else:                  grade = "F"

        return {
            "correct": correct,
            "wrong": wrong,
            "blank": blank,
            "total": total_q,
            "percentage": round(percentage, 1),
            "grade": grade,
            "details": details
        }

















      
      
      


# """
# Main OMR Processor
# Calibrated for MCQ Answer Sheet (1698 x 926 px)
# Left column: Q1-Q10 | Right column: Q11-Q20
# """

# import cv2
# import numpy as np
# from typing import Dict, List, Optional
# from app.config import OMRConfig
# from app.utils import OMRUtils


# class OMRProcessor:
#     def __init__(self):
#         self.config = OMRConfig
#         self.utils = OMRUtils
#         print("=" * 55)
#         print("OMR Processor Initialized")
#         print(f"   Total Questions : {self.config.ANSWERS['total_questions']}")
#         print(f"   Left col  (Q1-10) : {self.config.LEFT_COLUMN['option_x']}")
#         print(f"   Right col (Q11-20): {self.config.RIGHT_COLUMN['option_x']}")
#         print("=" * 55)

#     def process_image(self, image_bytes: bytes, apply_perspective: bool = False) -> Dict:
#         try:
#             nparr = np.frombuffer(image_bytes, np.uint8)
#             image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

#             if image is None:
#                 return {"success": False, "error": "Invalid image format or corrupted file"}

#             print(f"\nImage: {image.shape[1]} x {image.shape[0]} px")

#             if apply_perspective:
#                 image = self.utils.correct_perspective(image)

#             processed = self.utils.preprocess_image(image)
#             print("Preprocessed")

#             student_id = self._extract_student_id(processed)
#             print(f"Student ID: {student_id}")

#             answers = self._extract_answers(processed)

#             answered = sum(1 for a in answers if a is not None)
#             blank = self.config.ANSWERS["total_questions"] - answered

#             print(f"Answered: {answered}/{self.config.ANSWERS['total_questions']}")

#             return {
#                 "success": True,
#                 "student_id": student_id,
#                 "answers": answers,
#                 "total_answered": answered,
#                 "total_blank": blank,
#                 "total_questions": self.config.ANSWERS["total_questions"],
#                 "confidence": round(answered / self.config.ANSWERS["total_questions"], 2)
#             }

#         except Exception as e:
#             import traceback
#             traceback.print_exc()
#             return {"success": False, "error": str(e)}

  
    
    
#     def _extract_student_id(self, image: np.ndarray) -> str:
 
#      id_cfg = self.config.STUDENT_ID
#     digits = []
    
#     print(f"\n📖 Extracting Student ID from region: x={id_cfg['x']}, y={id_cfg['y']}")
    
#     # ডিবাগের জন্য ID রিজিয়ন সেভ করুন
#     id_region = image[
#         id_cfg["y"]: id_cfg["y"] + id_cfg["options"] * id_cfg["digit_height"],
#         id_cfg["x"]: id_cfg["x"] + id_cfg["num_digits"] * id_cfg["digit_width"]
#     ]
#     cv2.imwrite("debug_student_id_region.png", id_region)
#     print(f"   💾 Saved ID region debug image")
    
#     for col in range(id_cfg["num_digits"]):
#         col_x = id_cfg["x"] + col * id_cfg["digit_width"]
#         fill_scores = []
        
#         print(f"   Column {col+1}: ", end="")
        
#         for row in range(id_cfg["options"]):
#             y_pos = id_cfg["y"] + row * id_cfg["digit_height"]
#             roi = image[
#                 y_pos: y_pos + id_cfg["digit_height"],
#                 col_x: col_x + id_cfg["digit_width"]
#             ]
            
#             if roi.size < 50:
#                 fill_scores.append(0.0)
#                 continue
                
#             black_pixels = int(np.sum(roi == 255))
#             fill_pct = black_pixels / roi.size
#             fill_scores.append(fill_pct)
            
#             # ডিবাগ:哪个 রো ফিল্ড হয়েছে দেখুন
#             if fill_pct > 0.15:
#                 print(f" row{row}({fill_pct:.0%}) ", end="")
        
#         max_fill = max(fill_scores) if fill_scores else 0.0
#         threshold = self.config.THRESHOLDS.get("fill_threshold_pct", 0.17)
        
#         if max_fill >= threshold:
#             best_row = fill_scores.index(max_fill)
#             selected = str(best_row)
#             print(f"✅ -> Digit: {selected}")
#         else:
#             selected = "?"
#             print(f"❌ -> No fill detected")
            
#         digits.append(selected)
    
#     student_id = "".join(digits)
#     print(f"\n🎓 Final Student ID: {student_id}")
#     return student_id


#     def _extract_answers(self, image: np.ndarray) -> List[Optional[str]]:
#         options = ['A', 'B', 'C', 'D']
#         all_answers = [None] * 20

#         left = self.config.LEFT_COLUMN
#         for q_idx, y_pos in enumerate(left["row_y"]):
#             q_num = q_idx + 1
#             max_px = 0
#             selected = None

#             for opt_i, x_pos in enumerate(left["option_x"]):
#                 roi = image[
#                     y_pos: y_pos + left["bubble_height"],
#                     x_pos: x_pos + left["bubble_width"]
#                 ]
#                 if roi.size > 0:
#                     px = int(np.sum(roi == 255))
#                     if px > max_px and px > self.config.THRESHOLDS["min_black_pixels"]:
#                         max_px = px
#                         selected = options[opt_i]

#             all_answers[q_num - 1] = selected
#             print(f"   Q{q_num:2d}: {selected or '---'} (px={max_px})")

#         right = self.config.RIGHT_COLUMN
#         for q_idx, y_pos in enumerate(right["row_y"]):
#             q_num = q_idx + 11
#             max_px = 0
#             selected = None

#             for opt_i, x_pos in enumerate(right["option_x"]):
#                 roi = image[
#                     y_pos: y_pos + right["bubble_height"],
#                     x_pos: x_pos + right["bubble_width"]
#                 ]
#                 if roi.size > 0:
#                     px = int(np.sum(roi == 255))
#                     if px > max_px and px > self.config.THRESHOLDS["min_black_pixels"]:
#                         max_px = px
#                         selected = options[opt_i]

#             all_answers[q_num - 1] = selected
#             print(f"   Q{q_num:2d}: {selected or '---'} (px={max_px})")

#         return all_answers

#     def grade_exam(self, student_answers: List, answer_key: Dict) -> Dict:
#         correct = 0
#         wrong = 0
#         blank = 0
#         details = []

#         for i, student_ans in enumerate(student_answers):
#             q_num = str(i + 1)
#             correct_ans = answer_key.get(q_num)

#             if student_ans is None:
#                 blank += 1
#                 details.append({"question": i + 1, "student": None,
#                                  "correct": correct_ans, "status": "blank"})
#             elif student_ans == correct_ans:
#                 correct += 1
#                 details.append({"question": i + 1, "student": student_ans,
#                                  "correct": correct_ans, "status": "correct"})
#             else:
#                 wrong += 1
#                 details.append({"question": i + 1, "student": student_ans,
#                                  "correct": correct_ans, "status": "wrong"})

#         total_q = len(answer_key)
#         percentage = (correct / total_q * 100) if total_q > 0 else 0

#         if percentage >= 80:   grade = "A+"
#         elif percentage >= 70: grade = "A"
#         elif percentage >= 60: grade = "A-"
#         elif percentage >= 50: grade = "B"
#         elif percentage >= 40: grade = "C"
#         elif percentage >= 33: grade = "D"
#         else:                  grade = "F"

#         return {
#             "correct": correct,
#             "wrong": wrong,
#             "blank": blank,
#             "total": total_q,
#             "percentage": round(percentage, 1),
#             "grade": grade,
#             "details": details
#         }      
   