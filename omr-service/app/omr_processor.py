"""
Main OMR Processor - Detects bubbles and extracts answers
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from app.config import OMRConfig
from app.utils import OMRUtils

class OMRProcessor:
    def __init__(self):
        self.config = OMRConfig
        self.utils = OMRUtils
        print("=" * 50)
        print("✅ OMR Processor Initialized")
        print(f"   Total Questions: {self.config.ANSWERS['total_questions']}")
        print(f"   Student ID Digits: {self.config.STUDENT_ID['num_digits']}")
        print("=" * 50)
    
    def process_image(self, image_bytes: bytes, apply_perspective: bool = False) -> Dict:
        """
        Main OMR processing pipeline
        
        Args:
            image_bytes: Raw image file bytes
            apply_perspective: Whether to correct perspective distortion
        
        Returns:
            Dictionary with processing results
        """
        try:
            # Step 1: Decode image from bytes
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return {"success": False, "error": "Invalid image format or corrupted file"}
            
            print(f"\n📸 Image Info:")
            print(f"   Dimensions: {image.shape[1]} x {image.shape[0]} pixels")
            print(f"   Channels: {image.shape[2]}")
            
            # Step 2: Apply perspective correction (optional)
            if apply_perspective:
                print("   Applying perspective correction...")
                image = self.utils.correct_perspective(image)
            
            # Step 3: Preprocess image
            processed = self.utils.preprocess_image(image)
            print("✅ Image preprocessed successfully")
            
            # Step 4: Find all bubbles
            bubbles = self._find_all_bubbles(processed)
            print(f"✅ Found {len(bubbles)} potential bubbles")
            
            # Step 5: Extract Student ID
            student_id = self._extract_student_id(processed, bubbles)
            print(f"✅ Student ID: {student_id}")
            
            # Step 6: Extract Answers
            answers = self._extract_answers(processed, bubbles)
            
            # Step 7: Calculate statistics
            answered_count = sum(1 for a in answers if a is not None)
            blank_count = self.config.ANSWERS["total_questions"] - answered_count
            
            print(f"✅ Answers extracted: {answered_count}/{self.config.ANSWERS['total_questions']} answered")
            
            return {
                "success": True,
                "student_id": student_id,
                "answers": answers,
                "total_answered": answered_count,
                "total_blank": blank_count,
                "total_questions": self.config.ANSWERS["total_questions"],
                "confidence": answered_count / self.config.ANSWERS["total_questions"]
            }
            
        except Exception as e:
            print(f"❌ Error in process_image: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def _find_all_bubbles(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Find all bubble contours in the image"""
        contours = self.utils.find_contours(image)
        bubbles = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by area (bubble size)
            min_area = self.config.PREPROCESS["min_bubble_area"]
            max_area = self.config.PREPROCESS["max_bubble_area"]
            
            if min_area < area < max_area:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Check if roughly circular
                aspect_ratio = w / h
                if 0.7 < aspect_ratio < 1.3:
                    bubbles.append((x, y, w, h))
        
        return bubbles
    
    def _extract_student_id(self, image: np.ndarray, bubbles: List) -> str:
        """Extract student ID from bubble sheet"""
        id_config = self.config.STUDENT_ID
        digits = []
        
        # Extract ID region
        id_region = image[
            id_config["y"]:id_config["y"] + id_config["height"],
            id_config["x"]:id_config["x"] + id_config["width"]
        ]
        
        # For each digit column
        for col in range(id_config["num_digits"]):
            col_x = id_config["x"] + col * id_config["digit_width"]
            max_intensity = 0
            selected_digit = 0
            
            # Check each option in this column
            for row in range(id_config["options"]):
                y_pos = id_config["y"] + row * id_config["digit_height"]
                
                # Extract bubble region
                bubble_roi = image[
                    y_pos:y_pos + id_config["digit_height"],
                    col_x:col_x + id_config["digit_width"]
                ]
                
                if bubble_roi.size > 0:
                    intensity = np.sum(bubble_roi == 255)
                    
                    if intensity > max_intensity and intensity > self.config.THRESHOLDS["min_black_pixels"]:
                        max_intensity = intensity
                        selected_digit = row + 1  # Digits 1-4
            
            digits.append(str(selected_digit))
        
        # Join digits to form complete ID
        student_id = "".join(digits)
        
        # Validate ID (should have correct length)
        if len(student_id) != id_config["num_digits"]:
            print(f"⚠️ Warning: Expected {id_config['num_digits']} digits, got {len(student_id)}")
        
        return student_id
    
    def _extract_answers(self, image: np.ndarray, bubbles: List) -> List[Optional[str]]:
        """Extract answers for all questions"""
        answers = []
        answers_config = self.config.ANSWERS
        options = ['A', 'B', 'C', 'D']
        
        for q_num in range(1, answers_config["total_questions"] + 1):
            # Calculate Y position for this question
            y = answers_config["start_y"] + (q_num - 1) * answers_config["question_height"]
            
            # Check each option bubble
            max_pixels = 0
            selected_option = None
            
            for opt_idx, option in enumerate(options):
                x = answers_config["start_x"] + opt_idx * answers_config["option_spacing"]
                
                # Extract bubble region
                bubble_roi = image[
                    y:y + answers_config["option_height"],
                    x:x + answers_config["option_width"]
                ]
                
                if bubble_roi.size > 0:
                    # Count black pixels (filled area)
                    black_pixels = np.sum(bubble_roi == 255)
                    
                    # Check if this option is selected
                    min_threshold = self.config.THRESHOLDS["min_black_pixels"]
                    
                    if black_pixels > max_pixels and black_pixels > min_threshold:
                        max_pixels = black_pixels
                        selected_option = option
            
            answers.append(selected_option)
        
        return answers
    
    def grade_exam(self, student_answers: List, answer_key: Dict) -> Dict:
        """
        Grade the exam by comparing with answer key
        
        Args:
            student_answers: List of student's answers
            answer_key: Dictionary with question numbers as keys and answers as values
        
        Returns:
            Grading results with score, percentage, and detailed breakdown
        """
        total_questions = len(answer_key)
        correct = 0
        wrong = 0
        blank = 0
        detailed_results = []
        
        for q_num in range(1, total_questions + 1):
            q_str = str(q_num)
            student_ans = student_answers[q_num - 1] if q_num - 1 < len(student_answers) else None
            correct_ans = answer_key.get(q_str)
            
            if student_ans is None:
                blank += 1
                status = "blank"
                is_correct = False
            elif student_ans == correct_ans:
                correct += 1
                status = "correct"
                is_correct = True
            else:
                wrong += 1
                status = "wrong"
                is_correct = False
            
            detailed_results.append({
                "question": q_num,
                "student_answer": student_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "status": status
            })
        
        # Calculate score
        marks_per_q = self.config.GRADING["marks_per_question"]
        total_score = correct * marks_per_q
        
        # Apply negative marking if enabled
        if self.config.GRADING["negative_marking"]:
            total_score -= wrong * self.config.GRADING["negative_marks"]
        
        percentage = (total_score / (total_questions * marks_per_q)) * 100
        
        # Determine grade
        if percentage >= 80:
            grade = "A+"
        elif percentage >= 70:
            grade = "A"
        elif percentage >= 60:
            grade = "A-"
        elif percentage >= 50:
            grade = "B"
        elif percentage >= 40:
            grade = "C"
        elif percentage >= 33:
            grade = "D"
        else:
            grade = "F"
        
        return {
            "total_questions": total_questions,
            "correct": correct,
            "wrong": wrong,
            "blank": blank,
            "score": total_score,
            "total_marks": total_questions * marks_per_q,
            "percentage": round(percentage, 2),
            "grade": grade,
            "detailed_results": detailed_results
        }
    
    def debug_save_intermediate(self, image: np.ndarray, filename: str):
        """Save intermediate image for debugging"""
        cv2.imwrite(filename, image)
        print(f"📸 Debug image saved: {filename}")





















# import cv2
# import numpy as np
# from typing import Dict, List, Optional, Tuple
# from app.config import OMRConfig
# import math

# class OMRProcessor:
#     def __init__(self):
#         self.config = OMRConfig
#         print("✅ OMR Processor Initialized for MCQ Sheet")
        
#     def process_image(self, image_bytes: bytes) -> Dict:
#         """Main OMR processing pipeline"""
#         try:
#             # Step 1: Load image
#             nparr = np.frombuffer(image_bytes, np.uint8)
#             image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
#             if image is None:
#                 return {"success": False, "error": "Invalid image format"}
            
#             print(f"✅ Image loaded: {image.shape}")
            
#             # Step 2: Preprocess
#             processed, original = self._preprocess_image(image)
#             print("✅ Image preprocessed")
            
#             # Step 3: Find bubbles (contour detection)
#             bubbles = self._find_bubbles(processed)
#             print(f"✅ Found {len(bubbles)} potential bubbles")
            
#             # Step 4: Extract Student ID
#             student_id = self._extract_student_id(processed, bubbles)
#             print(f"✅ Student ID: {student_id}")
            
#             # Step 5: Extract Answers
#             answers = self._extract_answers(processed, bubbles)
#             print(f"✅ Answers extracted: {answers[:5]}...")
            
#             # Step 6: Calculate statistics
#             answered = sum(1 for a in answers if a is not None)
#             blank = self.config.ANSWERS["total_questions"] - answered
            
#             return {
#                 "success": True,
#                 "student_id": student_id,
#                 "answers": answers,
#                 "total_answered": answered,
#                 "total_blank": blank,
#                 "total_questions": self.config.ANSWERS["total_questions"],
#                 "confidence": self._calculate_confidence(answers)
#             }
            
#         except Exception as e:
#             print(f"❌ Error: {str(e)}")
#             import traceback
#             traceback.print_exc()
#             return {"success": False, "error": str(e)}
    
#     def _preprocess_image(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
#         """Advanced preprocessing for better bubble detection"""
#         # Convert to grayscale
#         gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
#         # Apply Gaussian blur to reduce noise
#         blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
#         # Apply adaptive threshold
#         binary = cv2.adaptiveThreshold(
#             blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#             cv2.THRESH_BINARY_INV, 15, 3
#         )
        
#         # Morphological operations to clean up
#         kernel = np.ones((3, 3), np.uint8)
#         cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
#         cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
#         return cleaned, image
    
#     def _find_bubbles(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
#         """Find all bubble contours in the image"""
#         # Find contours
#         contours, _ = cv2.findContours(
#             image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
#         )
        
#         bubbles = []
        
#         for contour in contours:
#             area = cv2.contourArea(contour)
            
#             # Filter by area (bubble size)
#             if self.config.PREPROCESS["min_bubble_area"] < area < self.config.PREPROCESS["max_bubble_area"]:
#                 # Get bounding rectangle
#                 x, y, w, h = cv2.boundingRect(contour)
                
#                 # Check if it's roughly circular (bubble shape)
#                 aspect_ratio = w / h
#                 if 0.7 < aspect_ratio < 1.3:
#                     bubbles.append((x, y, w, h))
        
#         return bubbles
    
#     def _extract_student_id(self, image: np.ndarray, bubbles: List) -> str:
#         """Extract 10-digit student ID"""
#         # For your sheet, ID is in top section
#         id_config = self.config.STUDENT_ID
        
#         # Define ID region
#         id_region = image[
#             id_config["y"]:id_config["y"] + id_config["height"],
#             id_config["x"]:id_config["x"] + id_config["width"]
#         ]
        
#         # Method 1: Detect filled bubbles in ID area
#         digits = []
        
#         for col in range(id_config["num_digits"]):
#             # For each digit column, find which bubble is filled
#             col_x = id_config["x"] + col * id_config["digit_width"]
            
#             # Check bubbles in this column
#             max_intensity = 0
#             selected_digit = 0
            
#             for row in range(id_config["options"]):  # Each column has 4 options (1,2,3,4)
#                 y_pos = id_config["y"] + row * id_config["digit_height"]
                
#                 # Extract this bubble region
#                 bubble_roi = image[
#                     y_pos:y_pos + id_config["digit_height"],
#                     col_x:col_x + id_config["digit_width"]
#                 ]
                
#                 if bubble_roi.size > 0:
#                     # Count white pixels (filled bubbles)
#                     intensity = np.sum(bubble_roi == 255)
                    
#                     if intensity > max_intensity and intensity > self.config.THRESHOLDS["min_black_pixels"]:
#                         max_intensity = intensity
#                         selected_digit = row + 1  # 1-4 range
            
#             digits.append(str(selected_digit))
        
#         # For demo, return a sample ID
#         # In production, you'll detect actual bubbles
#         return "".join(digits) if digits else "1234567890"
    
#     def _extract_answers(self, image: np.ndarray, bubbles: List) -> List[Optional[str]]:
#         """Extract answers for 20 questions"""
#         answers = []
#         answers_config = self.config.ANSWERS
#         options = ['A', 'B', 'C', 'D']
        
#         for q_num in range(1, answers_config["total_questions"] + 1):
#             # Calculate position for this question
#             y = answers_config["start_y"] + (q_num - 1) * answers_config["question_height"]
            
#             # Check each option bubble
#             max_pixels = 0
#             selected_option = None
            
#             for opt_idx, option in enumerate(options):
#                 x = answers_config["start_x"] + opt_idx * answers_config["option_spacing"]
                
#                 # Extract bubble region
#                 bubble_roi = image[
#                     y:y + answers_config["option_height"],
#                     x:x + answers_config["option_width"]
#                 ]
                
#                 if bubble_roi.size > 0:
#                     # Count black pixels (filled)
#                     black_pixels = np.sum(bubble_roi == 255)
                    
#                     if black_pixels > max_pixels and black_pixels > self.config.THRESHOLDS["min_black_pixels"]:
#                         max_pixels = black_pixels
#                         selected_option = option
            
#             answers.append(selected_option)
        
#         return answers
    
#     def _calculate_confidence(self, answers: List) -> float:
#         """Calculate confidence score of detection"""
#         answered = sum(1 for a in answers if a is not None)
#         return answered / self.config.ANSWERS["total_questions"]
    
#     def debug_draw_bubbles(self, image: np.ndarray, bubbles: List, output_path: str):
#         """Draw detected bubbles for debugging"""
#         debug_img = image.copy()
        
#         for (x, y, w, h) in bubbles:
#             cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
#             cv2.circle(debug_img, (x+w//2, y+h//2), 3, (0, 0, 255), -1)
        
#         cv2.imwrite(output_path, debug_img)
#         print(f"📸 Debug image saved: {output_path}")