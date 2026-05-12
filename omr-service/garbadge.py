# omr-processor:

# """
# Main OMR Processor
# Calibrated for MCQ Answer Sheet
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
#         """
#         Student ID Extract করুন ID গ্রিড থেকে
#         গ্রিড: 8 কলাম × 10 রো (0-9)
#         """
#         id_cfg = self.config.STUDENT_ID
#         digits = []
        
#         print(f"\n📖 Student ID Extract করছি:")
#         print(f"   Region: x={id_cfg['x']}, y={id_cfg['y']}")
#         print(f"   Grid Size: {id_cfg['num_digits']} columns × {id_cfg['options']} rows")
        
#         # ডিবাগের জন্য ID রিজিয়ন সেভ করুন
#         try:
#             id_region = image[
#                 id_cfg["y"]: id_cfg["y"] + id_cfg["options"] * id_cfg["digit_height"],
#                 id_cfg["x"]: id_cfg["x"] + id_cfg["num_digits"] * id_cfg["digit_width"]
#             ]
#             cv2.imwrite("debug_student_id_region.png", id_region)
#             print(f"   💾 ID region debug image সেভ করা হয়েছে")
#         except Exception as e:
#             print(f"   ⚠️ Debug image সেভ করতে পারেনি: {e}")
        
#         # প্রতিটি কলামে স্ক্যান করুন
#         for col in range(id_cfg["num_digits"]):
#             col_x = id_cfg["x"] + col * id_cfg["digit_width"]
#             fill_scores = []
            
#             print(f"   Column {col+1}: ", end="", flush=True)
            
#             # প্রতিটি রো (0-9) চেক করুন
#             for row in range(id_cfg["options"]):
#                 y_pos = id_cfg["y"] + row * id_cfg["digit_height"]
                
#                 # ROI extract করুন
#                 roi = image[
#                     y_pos: y_pos + id_cfg["digit_height"],
#                     col_x: col_x + id_cfg["digit_width"]
#                 ]
                
#                 if roi.size < 30:
#                     fill_scores.append(0.0)
#                     continue
                
#                 # কালো পিক্সেল গণনা করুন (255 = white/filled in binary)
#                 black_pixels = int(np.sum(roi == 255))
#                 fill_pct = black_pixels / roi.size if roi.size > 0 else 0.0
#                 fill_scores.append(fill_pct)
            
#             # সর্বোচ্চ ফিল পারসেন্ট খুঁজুন
#             if fill_scores:
#                 max_fill = max(fill_scores)
#                 threshold = self.config.THRESHOLDS.get("fill_threshold_pct", 0.15)
                
#                 if max_fill >= threshold:
#                     best_row = fill_scores.index(max_fill)
#                     selected = str(best_row)
#                     print(f"✅ {selected} ({max_fill:.0%})")
#                 else:
#                     selected = "?"
#                     print(f"❌ No clear fill (max: {max_fill:.0%})")
#             else:
#                 selected = "?"
#                 print(f"❌ Empty ROI")
            
#             digits.append(selected)
        
#         student_id = "".join(digits)
#         print(f"\n🎓 Final Student ID: {student_id}\n")
#         return student_id

#     def _extract_answers(self, image: np.ndarray) -> List[Optional[str]]:
#         """
#         সব 20 প্রশ্নের উত্তর Extract করুন
#         Q1-Q10  → LEFT_COLUMN
#         Q11-Q20 → RIGHT_COLUMN
#         """
#         options = ['A', 'B', 'C', 'D']
#         all_answers = [None] * 20

#         # Left Column - Q1 to Q10
#         print("\n📝 LEFT COLUMN (Q1-Q10):")
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

#         # Right Column - Q11 to Q20
#         print("\n📝 RIGHT COLUMN (Q11-Q20):")
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
#         """
#         উত্তর কী অনুযায়ী পরীক্ষার গ্রেড দিন
#         """
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






























# calibrate.py


# """
# OMR Sheet Calibration Tool
# Run this FIRST to find exact coordinates for your OMR sheet

# Usage:
#     python calibrate.py
#     Then select your OMR sheet image
# """

# import cv2
# import numpy as np
# import json
# import os
# from pathlib import Path


# class OMSCalibrator:
#     def __init__(self, image_path):
#         """Initialize calibrator with image"""
#         self.image_path = image_path
#         self.image = cv2.imread(image_path)
        
#         if self.image is None:
#             raise ValueError(f"❌ Could not load image: {image_path}")
        
#         self.original = self.image.copy()
#         self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
#         self.height, self.width = self.image.shape[:2]
        
#         print(f"\n📸 Image Loaded Successfully!")
#         print(f"   Dimensions: {self.width} x {self.height} pixels")
    
#     def preprocess_image(self):
#         """Preprocess image for better detection"""
#         blurred = cv2.GaussianBlur(self.gray, (5, 5), 0)
#         binary = cv2.adaptiveThreshold(
#             blurred, 255, 
#             cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#             cv2.THRESH_BINARY_INV, 15, 3
#         )
#         kernel = np.ones((3, 3), np.uint8)
#         cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
#         cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
#         return cleaned
    
#     def find_all_contours(self):
#         """Find all contours in the image"""
#         processed = self.preprocess_image()
#         contours, _ = cv2.findContours(
#             processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
#         )
#         return contours, processed
    
#     def detect_sheet_boundary(self):
#         """Detect the OMR sheet boundary (largest rectangle)"""
#         contours, _ = self.find_all_contours()
        
#         if not contours:
#             print("❌ No contours found!")
#             return None
        
#         largest_contour = max(contours, key=cv2.contourArea)
#         x, y, w, h = cv2.boundingRect(largest_contour)
        
#         print(f"\n📄 Sheet Boundary Detected:")
#         print(f"   Top-Left: ({x}, {y})")
#         print(f"   Width: {w} pixels, Height: {h} pixels")
        
#         return {"x": x, "y": y, "width": w, "height": h}
    
#     def detect_all_bubbles(self):
#         """Detect all bubble contours in the image"""
#         processed = self.preprocess_image()
#         contours, _ = cv2.findContours(processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
#         bubbles = []
#         bubble_areas = []
        
#         for contour in contours:
#             area = cv2.contourArea(contour)
            
#             # Filter by area (typical bubble size)
#             if 30 < area < 800:
#                 x, y, w, h = cv2.boundingRect(contour)
                
#                 # Check if roughly circular (bubble shape)
#                 aspect_ratio = w / h
#                 if 0.7 < aspect_ratio < 1.3:
#                     bubbles.append({
#                         "x": x, "y": y, "w": w, "h": h,
#                         "area": area,
#                         "center_x": x + w//2,
#                         "center_y": y + h//2
#                     })
#                     bubble_areas.append(area)
        
#         print(f"\n🔵 Bubble Detection:")
#         print(f"   Total bubbles found: {len(bubbles)}")
        
#         if bubble_areas:
#             print(f"   Average bubble area: {np.mean(bubble_areas):.0f} pixels")
        
#         return bubbles
    
#     def detect_id_section(self, bubbles):
#         """Detect Student ID section (usually at the top)"""
#         if not bubbles:
#             print("❌ No bubbles found for ID detection")
#             return None
        
#         # Find the smallest Y coordinate (topmost bubbles)
#         min_y = min(bubble["y"] for bubble in bubbles)
#         max_y = min_y + 200  # ID section height
        
#         # Filter bubbles in the ID section
#         id_bubbles = [b for b in bubbles if min_y <= b["y"] <= max_y]
        
#         if not id_bubbles:
#             print("❌ Could not detect ID section")
#             return None
        
#         # Find the bounding box of ID section
#         min_x = min(b["x"] for b in id_bubbles)
#         max_x = max(b["x"] + b["w"] for b in id_bubbles)
#         min_y_id = min(b["y"] for b in id_bubbles)
#         max_y_id = max(b["y"] + b["h"] for b in id_bubbles)
        
#         # Detect rows and columns
#         y_positions = sorted(set(b["y"] for b in id_bubbles))
#         x_positions = sorted(set(b["x"] for b in id_bubbles))
        
#         print(f"\n🆔 Student ID Section Detected:")
#         print(f"   Location: ({min_x}, {min_y_id}) to ({max_x}, {max_y_id})")
#         print(f"   Columns (digits): {len(x_positions)}")
#         print(f"   Rows (options 0-9): {len(y_positions)}")
        
#         # Calculate digit dimensions
#         digit_width = (max_x - min_x) / len(x_positions) if x_positions else 35
#         digit_height = (max_y_id - min_y_id) / len(y_positions) if y_positions else 20
        
#         return {
#             "x": min_x,
#             "y": min_y_id,
#             "width": max_x - min_x,
#             "height": max_y_id - min_y_id,
#             "num_digits": len(x_positions),
#             "digit_width": int(digit_width),
#             "digit_height": int(digit_height),
#             "options": len(y_positions)
#         }
    
#     def detect_answer_section(self, bubbles, id_section):
#         """Detect answers section (questions 1-20)"""
#         if not bubbles:
#             return None
        
#         # Answer section starts below ID section
#         start_y = id_section["y"] + id_section["height"] + 50 if id_section else 300
        
#         # Filter answer bubbles (below ID section)
#         answer_bubbles = [b for b in bubbles if b["y"] > start_y]
        
#         if not answer_bubbles:
#             print("❌ Could not detect answer section")
#             return None
        
#         # Find bounding box
#         min_x = min(b["x"] for b in answer_bubbles)
#         max_x = max(b["x"] + b["w"] for b in answer_bubbles)
#         min_y = min(b["y"] for b in answer_bubbles)
#         max_y = max(b["y"] + b["h"] for b in answer_bubbles)
        
#         # Group by question (same Y coordinate)
#         questions = {}
#         for bubble in answer_bubbles:
#             y = bubble["y"]
#             if y not in questions:
#                 questions[y] = []
#             questions[y].append(bubble)
        
#         # Sort questions by Y coordinate
#         sorted_questions = sorted(questions.items())
        
#         # Calculate question height
#         if len(sorted_questions) > 1:
#             question_height = sorted_questions[1][0] - sorted_questions[0][0]
#         else:
#             question_height = 45
        
#         print(f"\n📝 Answer Section Detected:")
#         print(f"   Total questions: {len(sorted_questions)}")
#         print(f"   Question height: {question_height} pixels")
        
#         # Detect left and right columns if needed
#         mid_x = (min_x + max_x) // 2
#         left_questions = [q for q in sorted_questions if q[1][0]["x"] < mid_x]
#         right_questions = [q for q in sorted_questions if q[1][0]["x"] > mid_x]
        
#         print(f"   Left column questions: {len(left_questions)}")
#         print(f"   Right column questions: {len(right_questions)}")
        
#         # Get option X positions from first question
#         if sorted_questions:
#             first_q_bubbles = sorted(sorted_questions[0][1], key=lambda b: b["x"])
#             option_x = [b["x"] for b in first_q_bubbles]
#             print(f"   Option X positions: {option_x}")
        
#         # Get row Y positions
#         row_y = [q[0] for q in sorted_questions]
        
#         return {
#             "start_x": min_x,
#             "start_y": min_y,
#             "end_x": max_x,
#             "end_y": max_y,
#             "total_questions": len(sorted_questions),
#             "question_height": question_height,
#             "options_per_q": len(sorted_questions[0][1]) if sorted_questions else 4,
#             "option_x": option_x if sorted_questions else [],
#             "row_y": row_y,
#             "bubble_width": answer_bubbles[0]["w"] if answer_bubbles else 35,
#             "bubble_height": answer_bubbles[0]["h"] if answer_bubbles else 35
#         }
    
#     def generate_configuration(self):
#         """Generate complete configuration file"""
#         print("\n" + "="*60)
#         print("🔧 GENERATING OMR CONFIGURATION")
#         print("="*60)
        
#         # Detect all components
#         bubbles = self.detect_all_bubbles()
#         id_section = self.detect_id_section(bubbles)
#         answer_section = self.detect_answer_section(bubbles, id_section)
        
#         if not answer_section:
#             print("❌ Could not detect answer section!")
#             return None
        
#         # Create configuration
#         config = {
#             "STUDENT_ID": {
#                 "x": id_section["x"] if id_section else 150,
#                 "y": id_section["y"] if id_section else 80,
#                 "num_digits": id_section["num_digits"] if id_section else 10,
#                 "digit_width": id_section["digit_width"] if id_section else 35,
#                 "digit_height": id_section["digit_height"] if id_section else 20,
#                 "options": id_section["options"] if id_section else 10
#             },
#             "LEFT_COLUMN": {
#                 "option_x": [452, 539, 632, 725],  # Calibrate these!
#                 "row_y": answer_section["row_y"][:10] if len(answer_section["row_y"]) >= 10 else answer_section["row_y"],
#                 "bubble_width": answer_section["bubble_width"],
#                 "bubble_height": answer_section["bubble_height"]
#             },
#             "RIGHT_COLUMN": {
#                 "option_x": [999, 1085, 1174, 1269],  # Calibrate these!
#                 "row_y": answer_section["row_y"][10:20] if len(answer_section["row_y"]) >= 20 else answer_section["row_y"],
#                 "bubble_width": answer_section["bubble_width"],
#                 "bubble_height": answer_section["bubble_height"]
#             },
#             "ANSWERS": {
#                 "total_questions": answer_section["total_questions"],
#                 "options_per_q": answer_section["options_per_q"]
#             },
#             "THRESHOLDS": {
#                 "min_black_pixels": 55,
#                 "fill_threshold_pct": 0.18,
#                 "max_black_pixels": 1000,
#                 "fill_ratio": 0.4,
#                 "confidence_threshold": 0.8
#             },
#             "GRADING": {
#                 "marks_per_question": 1,
#                 "negative_marking": False,
#                 "negative_marks": 0
#             }
#         }
        
#         # Save to file
#         with open("omr_configuration.json", "w") as f:
#             json.dump(config, f, indent=2)
        
#         print("\n✅ Configuration saved to 'omr_configuration.json'")
        
#         # Generate Python config
#         self.generate_python_config(config, answer_section)
        
#         return config
    
#     def generate_python_config(self, config, answer_section):
#         """Generate Python config.py file content"""
        
#         # Prepare row_y as properly formatted string
#         left_row_y = config["LEFT_COLUMN"]["row_y"]
#         right_row_y = config["RIGHT_COLUMN"]["row_y"]
        
#         python_code = f'''"""
# Auto-generated OMR Configuration
# Generated by calibrate.py
# """

# class OMRConfig:
#     """OMR Sheet Configuration"""
    
#     # Student ID configuration
#     STUDENT_ID = {{
#         "x": {config["STUDENT_ID"]["x"]},
#         "y": {config["STUDENT_ID"]["y"]},
#         "num_digits": {config["STUDENT_ID"]["num_digits"]},
#         "digit_width": {config["STUDENT_ID"]["digit_width"]},
#         "digit_height": {config["STUDENT_ID"]["digit_height"]},
#         "options": {config["STUDENT_ID"]["options"]}
#     }}
    
#     THRESHOLDS = {{
#         "min_black_pixels": {config["THRESHOLDS"]["min_black_pixels"]},
#         "fill_threshold_pct": {config["THRESHOLDS"]["fill_threshold_pct"]},
#         "max_black_pixels": {config["THRESHOLDS"]["max_black_pixels"]},
#         "fill_ratio": {config["THRESHOLDS"]["fill_ratio"]},
#         "confidence_threshold": {config["THRESHOLDS"]["confidence_threshold"]}
#     }}
    
#     # Left column Q1-Q10
#     LEFT_COLUMN = {{
#         "option_x": [452, 539, 632, 725],
#         "row_y": {left_row_y if left_row_y else [384, 434, 485, 536, 586, 636, 686, 736, 788, 838]},
#         "bubble_width": {config["LEFT_COLUMN"]["bubble_width"]},
#         "bubble_height": {config["LEFT_COLUMN"]["bubble_height"]},
#     }}
    
#     # Right column Q11-Q20
#     RIGHT_COLUMN = {{
#         "option_x": [999, 1085, 1174, 1269],
#         "row_y": {right_row_y if right_row_y else [384, 434, 485, 536, 586, 636, 686, 736, 788, 838]},
#         "bubble_width": {config["RIGHT_COLUMN"]["bubble_width"]},
#         "bubble_height": {config["RIGHT_COLUMN"]["bubble_height"]},
#     }}
    
#     ANSWERS = {{
#         "total_questions": {config["ANSWERS"]["total_questions"]},
#         "options_per_q": {config["ANSWERS"]["options_per_q"]},
#     }}
    
#     GRADING = {{
#         "marks_per_question": {config["GRADING"]["marks_per_question"]},
#         "negative_marking": {config["GRADING"]["negative_marking"]},
#         "negative_marks": {config["GRADING"]["negative_marks"]}
#     }}
# '''
        
#         # Save Python config
#         with open("config_auto.py", "w") as f:
#             f.write(python_code)
        
#         print(f"✅ Python config saved to 'config_auto.py'")
    
#     def visualize_detection(self, output_path="calibrated_output.jpg"):
#         """Create visualization of detected areas"""
#         vis_image = self.original.copy()
        
#         bubbles = self.detect_all_bubbles()
#         id_section = self.detect_id_section(bubbles)
#         answer_section = self.detect_answer_section(bubbles, id_section)
        
#         # Draw ID section (Blue)
#         if id_section:
#             cv2.rectangle(vis_image,
#                          (id_section["x"], id_section["y"]),
#                          (id_section["x"] + id_section["width"], 
#                           id_section["y"] + id_section["height"]),
#                          (255, 0, 0), 2)
#             cv2.putText(vis_image, "Student ID Area", 
#                        (id_section["x"], id_section["y"] - 10),
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
#         # Draw answer section (Red)
#         if answer_section:
#             cv2.rectangle(vis_image,
#                          (answer_section["start_x"], answer_section["start_y"]),
#                          (answer_section["end_x"], answer_section["end_y"]),
#                          (0, 0, 255), 2)
#             cv2.putText(vis_image, "Answers Area", 
#                        (answer_section["start_x"], answer_section["start_y"] - 10),
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
#         # Draw individual bubbles (Yellow dots)
#         for bubble in bubbles[:200]:
#             cv2.circle(vis_image, 
#                       (bubble["center_x"], bubble["center_y"]), 
#                       3, (0, 255, 255), -1)
        
#         # Add information text
#         info_text = [
#             f"Total Bubbles: {len(bubbles)}",
#             f"Image Size: {self.width}x{self.height}",
#             f"Questions: {answer_section['total_questions'] if answer_section else 'N/A'}"
#         ]
        
#         y_offset = 30
#         for text in info_text:
#             cv2.putText(vis_image, text, (10, y_offset),
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
#             y_offset += 25
        
#         # Save visualization
#         cv2.imwrite(output_path, vis_image)
#         print(f"\n📸 Visualization saved: {output_path}")
        
#         return vis_image
    
#     def run_full_calibration(self):
#         """Run complete calibration process"""
#         print("\n" + "="*60)
#         print("🚀 STARTING FULL CALIBRATION")
#         print("="*60)
        
#         config = self.generate_configuration()
        
#         if config:
#             self.visualize_detection()
            
#             print("\n" + "="*60)
#             print("✅ CALIBRATION COMPLETE!")
#             print("="*60)
#             print("\n📁 Files generated:")
#             print("   1. omr_configuration.json - Complete configuration")
#             print("   2. config_auto.py - Python config file")
#             print("   3. calibrated_output.jpg - Visualization image")
#             print("\n📝 Next steps:")
#             print("   1. Copy values from config_auto.py to app/config.py")
#             print("   2. Run 'python test_with_your_sheet.py' to test")
#             print("   3. Start API server with 'uvicorn app.main:app --reload'")
#         else:
#             print("\n❌ Calibration failed! Try manual calibration.")
        
#         return config


# def auto_calibrate(image_path: str):
#     """Quick auto-calibration function"""
#     try:
#         calibrator = OMSCalibrator(image_path)
#         return calibrator.run_full_calibration()
#     except Exception as e:
#         print(f"❌ Error: {str(e)}")
#         return None


# def main():
#     """Main calibration function"""
#     print("="*60)
#     print("🎯 OMR SHEET CALIBRATION TOOL")
#     print("="*60)
    
#     # Ask for image file
#     print("\n📁 Please provide your OMR sheet image:")
#     # default_images = ["Perfect_image3.png", "Perfec_filled.png", "test_images/Perfect_image3.png"]
#     default_images = ["../test_images/Perfect_image3.png"]
    
#     image_path = None
#     for img in default_images:
#         if os.path.exists(img):
#             image_path = img
#             print(f"   Found default image: {image_path}")
#             break
    
#     if not image_path:
#         image_path = input("Enter image path: ").strip()
#         if not os.path.exists(image_path):
#             print(f"❌ File not found: {image_path}")
#             return
    
#     try:
#         calibrator = OMSCalibrator(image_path)
#         calibrator.run_full_calibration()
            
#     except Exception as e:
#         print(f"❌ Error: {str(e)}")
#         import traceback
#         traceback.print_exc()


# if __name__ == "__main__":
#     main()











#  Utilis.py:






# """
# Utility functions for OMR processing
# """

# import cv2
# import numpy as np
# from typing import List, Tuple, Optional

# class OMRUtils:
    
#     @staticmethod
#     def preprocess_image(image: np.ndarray) -> np.ndarray:
#         """Convert image to binary (black and white) for bubble detection"""
#         # Convert to grayscale
#         gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
#         # Apply Gaussian blur to reduce noise
#         blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
#         # Apply adaptive threshold (works better for varying lighting)
#         binary = cv2.adaptiveThreshold(
#             blurred, 
#             255, 
#             cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#             cv2.THRESH_BINARY_INV, 
#             15, 
#             3
#         )
        
#         # Morphological operations to clean up noise
#         kernel = np.ones((3, 3), np.uint8)
#         cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
#         cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
#         return cleaned
    
#     @staticmethod
#     def count_black_pixels(region: np.ndarray) -> int:
#         """Count black pixels in a region (white in thresholded image)"""
#         if region.size == 0:
#             return 0
#         return np.sum(region == 255)
    
#     @staticmethod
#     def detect_bubble(region: np.ndarray, threshold: int = 150) -> Tuple[bool, int]:
#         """Detect if a bubble is filled"""
#         black_pixels = OMRUtils.count_black_pixels(region)
#         is_filled = black_pixels > threshold
#         return is_filled, black_pixels
    
#     @staticmethod
#     def find_contours(image: np.ndarray) -> List:
#         """Find all contours in the image"""
#         contours, _ = cv2.findContours(
#             image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
#         )
#         return contours
    
#     @staticmethod
#     def is_circular(contour, circularity_threshold: float = 0.7) -> bool:
#         """Check if a contour is roughly circular (bubble shape)"""
#         area = cv2.contourArea(contour)
#         perimeter = cv2.arcLength(contour, True)
        
#         if perimeter == 0:
#             return False
        
#         circularity = 4 * np.pi * area / (perimeter * perimeter)
#         return circularity > circularity_threshold
    
#     @staticmethod
#     def correct_perspective(image: np.ndarray) -> np.ndarray:
#         """Auto-correct perspective of skewed OMR sheet"""
#         # Find the largest contour (the OMR sheet)
#         gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#         edges = cv2.Canny(gray, 50, 150)
#         contours = OMRUtils.find_contours(edges)
        
#         if contours:
#             # Get largest contour
#             largest = max(contours, key=cv2.contourArea)
            
#             # Approximate polygon
#             epsilon = 0.02 * cv2.arcLength(largest, True)
#             approx = cv2.approxPolyDP(largest, epsilon, True)
            
#             if len(approx) == 4:
#                 # Apply perspective transform
#                 return OMRUtils.four_point_transform(image, approx.reshape(4, 2))
        
#         return image
    
#     @staticmethod
#     def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
#         """Apply perspective transform to get bird's eye view"""
#         # Rearrange points
#         rect = OMRUtils.order_points(pts)
#         (tl, tr, br, bl) = rect
        
#         # Compute width
#         widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
#         widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
#         maxWidth = max(int(widthA), int(widthB))
        
#         # Compute height
#         heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
#         heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
#         maxHeight = max(int(heightA), int(heightB))
        
#         # Destination points
#         dst = np.array([
#             [0, 0],
#             [maxWidth - 1, 0],
#             [maxWidth - 1, maxHeight - 1],
#             [0, maxHeight - 1]
#         ], dtype="float32")
        
#         # Apply transform
#         M = cv2.getPerspectiveTransform(rect, dst)
#         warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
        
#         return warped
    
#     @staticmethod
#     def order_points(pts: np.ndarray) -> np.ndarray:
#         """Order points in clockwise direction"""
#         rect = np.zeros((4, 2), dtype="float32")
        
#         # Sum and diff to find corners
#         s = pts.sum(axis=1)
#         rect[0] = pts[np.argmin(s)]
#         rect[2] = pts[np.argmax(s)]
        
#         diff = np.diff(pts, axis=1)
#         rect[1] = pts[np.argmin(diff)]
#         rect[3] = pts[np.argmax(diff)]
        
#         return rect
    
#     @staticmethod
#     def visualize_bubbles(image: np.ndarray, bubbles: List, output_path: str):
#         """Draw detected bubbles on image for debugging"""
#         debug_img = image.copy()
        
#         for (x, y, w, h) in bubbles:
#             cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
#             cv2.circle(debug_img, (x + w // 2, y + h // 2), 3, (0, 0, 255), -1)
        
#         cv2.imwrite(output_path, debug_img)
#         print(f"📸 Debug image saved: {output_path}")



# main .py: 










































# """
# FastAPI Server for OMR Processing Service
# """

# from fastapi import FastAPI, UploadFile, File, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse, FileResponse
# from pydantic import BaseModel
# from typing import List, Optional, Dict
# import uvicorn
# import os
# import tempfile

# # from app.omr_processor import OMRProcessor

# # ✅ হওয়া উচিত (যদি app/ ফোল্ডার থেকে রান করেন):
# from omr_processor import OMRProcessor
# from config import OMRConfig

# # Create FastAPI app
# app = FastAPI(
#     title="OMR Processing Service",
#     description="Automatic MCQ answer sheet checking service",
#     version="1.0.0",
#     docs_url="/docs",
#     redoc_url="/redoc"
# )

# # Enable CORS (for API Gateway)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # In production, replace with specific origins
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Initialize OMR Processor
# processor = OMRProcessor()

# # Request/Response Models
# class AnswerKey(BaseModel):
#     answer_key: Dict[str, str]  # {"1": "A", "2": "B", ...}

# class GradeRequest(BaseModel):
#     exam_id: str
#     answer_key: AnswerKey

# class ProcessResponse(BaseModel):
#     success: bool
#     student_id: Optional[str] = None
#     answers: Optional[List[Optional[str]]] = None
#     total_answered: Optional[int] = None
#     total_blank: Optional[int] = None
#     total_questions: Optional[int] = None
#     confidence: Optional[float] = None
#     error: Optional[str] = None

# # API Endpoints
# @app.get("/")
# async def root():
#     """Root endpoint with service information"""
#     return {
#         "service": "OMR Processing Service",
#         "version": "1.0.0",
#         "status": "running",
#         "endpoints": {
#             "health": "GET /health",
#             "process": "POST /process",
#             "process_batch": "POST /process-batch",
#             "grade": "POST /grade",
#             "docs": "GET /docs"
#         }
#     }

# @app.get("/health")
# async def health_check():
#     """Health check endpoint"""
#     return {
#         "status": "healthy",
#         "service": "omr-service",
#         "version": "1.0.0"
#     }

# @app.post("/process", response_model=ProcessResponse)
# async def process_omr_sheet(
#     file: UploadFile = File(...),
#     apply_perspective: bool = False
# ):
#     """
#     Process a single OMR sheet image
    
#     - **file**: OMR sheet image (JPEG/PNG)
#     - **apply_perspective**: Apply perspective correction (default: false)
#     """
#     # Validate file type
#     if not file.content_type in ["image/jpeg", "image/jpg", "image/png"]:
#         return JSONResponse(
#             status_code=400,
#             content={
#                 "success": False,
#                 "error": "Only JPEG/PNG images are allowed"
#             }
#         )
    
#     # Validate file size (max 10MB)
#     file_size = 0
#     try:
#         image_bytes = await file.read()
#         file_size = len(image_bytes)
        
#         if file_size > 10 * 1024 * 1024:  # 10MB
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "success": False,
#                     "error": "File size too large. Maximum 10MB allowed"
#                 }
#             )
        
#         if file_size == 0:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "success": False,
#                     "error": "Empty file"
#                 }
#             )
        
#         # Process the image
#         result = processor.process_image(image_bytes, apply_perspective)
        
#         if result["success"]:
#             return JSONResponse(content=result, status_code=200)
#         else:
#             return JSONResponse(content=result, status_code=400)
            
#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={
#                 "success": False,
#                 "error": f"Server error: {str(e)}"
#             }
#         )

# @app.post("/process-batch")
# async def process_batch(
#     files: List[UploadFile] = File(...),
#     apply_perspective: bool = False
# ):
#     """
#     Process multiple OMR sheets in batch
    
#     - **files**: List of OMR sheet images
#     - **apply_perspective**: Apply perspective correction (default: false)
#     """
#     results = []
    
#     for file in files:
#         try:
#             # Validate file type
#             if not file.content_type in ["image/jpeg", "image/jpg", "image/png"]:
#                 results.append({
#                     "success": False,
#                     "filename": file.filename,
#                     "error": "Invalid file type. Only JPEG/PNG allowed"
#                 })
#                 continue
            
#             # Process image
#             image_bytes = await file.read()
#             result = processor.process_image(image_bytes, apply_perspective)
#             result["filename"] = file.filename
#             results.append(result)
            
#         except Exception as e:
#             results.append({
#                 "success": False,
#                 "filename": file.filename,
#                 "error": str(e)
#             })
    
#     return JSONResponse(content={
#         "success": True,
#         "total_processed": len(results),
#         "results": results
#     })

# @app.post("/grade")
# async def grade_exam(
#     student_id: str,
#     exam_id: str,
#     file: UploadFile = File(...),
#     answer_key: str = None
# ):
#     """
#     Process and grade an OMR sheet
    
#     - **student_id**: Student ID
#     - **exam_id**: Exam ID
#     - **file**: OMR sheet image
#     - **answer_key**: JSON string of answer key
#     """
#     try:
#         # Process the image
#         image_bytes = await file.read()
#         result = processor.process_image(image_bytes)
        
#         if not result["success"]:
#             return JSONResponse(
#                 status_code=400,
#                 content={"success": False, "error": result["error"]}
#             )
        
#         # If answer key provided, grade the exam
#         if answer_key:
#             import json
#             key = json.loads(answer_key)
#             grading_result = processor.grade_exam(result["answers"], key)
            
#             return JSONResponse(content={
#                 "success": True,
#                 "student_id": student_id,
#                 "exam_id": exam_id,
#                 "processing_result": result,
#                 "grading_result": grading_result
#             })
#         else:
#             return JSONResponse(content={
#                 "success": True,
#                 "student_id": student_id,
#                 "exam_id": exam_id,
#                 "processing_result": result
#             })
            
#     except Exception as e:
#         return JSONResponse(
#             status_code=500,
#             content={"success": False, "error": str(e)}
#         )

# @app.get("/config")
# async def get_config():
#     """Get current OMR configuration"""
#     from app.config import OMRConfig
    
#     return {
#         "student_id": OMRConfig.STUDENT_ID,
#         "answers": OMRConfig.ANSWERS,
#         "thresholds": OMRConfig.THRESHOLDS,
#         "grading": OMRConfig.GRADING
#     }

# if __name__ == "__main__":
#     uvicorn.run(
#         "app.main:app",
#         host="0.0.0.0",
#         port=8001,
#         reload=True,
#         log_level="info"
#     )

