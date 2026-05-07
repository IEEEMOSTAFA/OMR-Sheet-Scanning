"""
OMR Sheet Configuration
Adjust these coordinates based on your actual OMR sheet
"""

class OMRConfig:
    """Configuration for OMR sheet detection"""
    
    # Image preprocessing settings
    PREPROCESS = {
        "blur_kernel": (5, 5),          # Gaussian blur kernel size
        "threshold_block_size": 15,      # Adaptive threshold block size
        "threshold_constant": 3,         # Constant subtracted from mean
        "min_bubble_area": 50,           # Minimum area to consider as bubble
        "max_bubble_area": 500           # Maximum area for single bubble
    }
    
    # Student ID configuration (Top section of OMR sheet)
    STUDENT_ID = {
        "x": 150,           # X coordinate (horizontal position)
        "y": 80,            # Y coordinate (vertical position)
        "width": 400,       # Width of ID area
        "height": 60,       # Height of ID area
        "num_digits": 10,   # Number of digits in student ID
        "digit_width": 35,  # Width of each digit column
        "digit_height": 35, # Height of each digit bubble
        "options": 4        # Options per digit (1,2,3,4)
    }
    
    # Answers configuration (Middle section with questions 1-20)
    ANSWERS = {
        "start_x": 150,              # Starting X for first option (A)
        "start_y": 200,              # Starting Y for question 1
        "question_height": 45,       # Vertical gap between questions
        "total_questions": 20,       # Total number of questions
        "options_per_q": 4,          # Options: A, B, C, D
        "option_width": 30,          # Width of each option bubble
        "option_height": 30,         # Height of each option bubble
        "option_spacing": 50         # Horizontal gap between options
    }
    
    # Bubble detection thresholds
    THRESHOLDS = {
        "min_black_pixels": 150,     # Minimum black pixels to consider filled
        "max_black_pixels": 800,     # Maximum expected for one bubble
        "fill_ratio": 0.7,           # 70% filled means selected
        "confidence_threshold": 0.8   # 80% confidence needed
    }
    
    # Grading settings
    GRADING = {
        "marks_per_question": 1,      # Each question carries 1 mark
        "negative_marking": False,    # No negative marking
        "negative_marks": 0           # If negative marking, value here
    }
    
    @classmethod
    def get_answer_position(cls, question_num: int):
        """Calculate Y position for a specific question"""
        y = cls.ANSWERS["start_y"] + (question_num - 1) * cls.ANSWERS["question_height"]
        return y
    
    @classmethod
    def get_option_position(cls, option_index: int):
        """Calculate X position for a specific option"""
        x = cls.ANSWERS["start_x"] + option_index * cls.ANSWERS["option_spacing"]
        return x









# import cv2
# import numpy as np

# class OMRConfig:
#     """Specific configuration for your MCQ answer sheet"""
    
#     # Image preprocessing settings
#     PREPROCESS = {
#         "blur_kernel": (5, 5),
#         "threshold_block_size": 15,
#         "threshold_constant": 3,
#         "min_bubble_area": 50,  # Minimum area to consider as bubble
#         "max_bubble_area": 500   # Maximum area for single bubble
#     }
    
#     # Student ID configuration (ID Number section)
#     STUDENT_ID = {
#         "x": 150,           # Starting X position of ID area
#         "y": 80,            # Starting Y position of ID area
#         "width": 400,       # Width of entire ID area
#         "height": 60,       # Height of ID area
#         "num_digits": 10,   # Your sheet has 10 digit ID (1-10 columns)
#         "digit_width": 35,  # Width per digit column
#         "digit_height": 35, # Height per digit bubble
#         "options": 4        # Each digit column has bubbles 1,2,3,4? Actually your sheet shows ● ■ etc
#     }
    
#     # Answers configuration (Questions 1-20)
#     ANSWERS = {
#         "start_x": 150,     # Starting X for answers (leftmost option)
#         "start_y": 200,     # Starting Y for question 1
#         "question_height": 45,  # Vertical gap between questions
#         "total_questions": 20,
#         "options_per_q": 4,     # A, B, C, D
#         "option_width": 30,     # Width of each option bubble
#         "option_height": 30,    # Height of each option bubble
#         "option_spacing": 50    # Horizontal gap between options
#     }
    
#     # Bubble detection thresholds
#     THRESHOLDS = {
#         "min_black_pixels": 150,    # Minimum black pixels to consider filled
#         "max_black_pixels": 800,    # Maximum for single bubble
#         "fill_ratio": 0.7,          # 70% filled means selected
#         "confidence_threshold": 0.8  # 80% confidence needed
#     }
    
#     # These coordinates need to be adjusted based on your actual scanned image
#     # You'll need to find exact coordinates by running debug script