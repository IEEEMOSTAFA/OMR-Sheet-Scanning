"""
OMR Sheet Calibration Tool
Run this FIRST to find exact coordinates for your OMR sheet

Usage:
    python calibrate.py
    Then select your OMR sheet image
"""

import cv2
import numpy as np
import json
import os
from pathlib import Path

class OMSCalibrator:
    def __init__(self, image_path):
        """Initialize calibrator with image"""
        self.image_path = image_path
        self.image = cv2.imread(image_path)
        
        if self.image is None:
            raise ValueError(f"❌ Could not load image: {image_path}")
        
        self.original = self.image.copy()
        self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        self.height, self.width = self.image.shape[:2]
        
        print(f"\n📸 Image Loaded Successfully!")
        print(f"   Dimensions: {self.width} x {self.height} pixels")
        print(f"   Channels: {self.image.shape[2]}")
    
    def preprocess_image(self):
        """Preprocess image for better detection"""
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(self.gray, (5, 5), 0)
        
        # Apply adaptive threshold
        binary = cv2.adaptiveThreshold(
            blurred, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 15, 3
        )
        
        # Morphological operations
        kernel = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
        return cleaned
    
    def find_all_contours(self):
        """Find all contours in the image"""
        processed = self.preprocess_image()
        contours, _ = cv2.findContours(
            processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        return contours, processed
    
    def detect_sheet_boundary(self):
        """Detect the OMR sheet boundary (largest rectangle)"""
        contours, _ = self.find_all_contours()
        
        if not contours:
            print("❌ No contours found!")
            return None
        
        # Find largest contour by area
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        print(f"\n📄 Sheet Boundary Detected:")
        print(f"   Top-Left: ({x}, {y})")
        print(f"   Bottom-Right: ({x + w}, {y + h})")
        print(f"   Width: {w} pixels")
        print(f"   Height: {h} pixels")
        
        return {"x": x, "y": y, "width": w, "height": h}
    
    def detect_all_bubbles(self):
        """Detect all bubble contours in the image"""
        processed = self.preprocess_image()
        contours, _ = cv2.findContours(processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        bubbles = []
        bubble_areas = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by area (typical bubble size)
            if 30 < area < 800:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Check if roughly circular (bubble shape)
                aspect_ratio = w / h
                if 0.7 < aspect_ratio < 1.3:
                    bubbles.append({
                        "x": x, "y": y, "w": w, "h": h,
                        "area": area,
                        "center_x": x + w//2,
                        "center_y": y + h//2
                    })
                    bubble_areas.append(area)
        
        print(f"\n🔵 Bubble Detection:")
        print(f"   Total bubbles found: {len(bubbles)}")
        
        if bubble_areas:
            print(f"   Average bubble area: {np.mean(bubble_areas):.0f} pixels")
            print(f"   Min bubble area: {min(bubble_areas):.0f} pixels")
            print(f"   Max bubble area: {max(bubble_areas):.0f} pixels")
        
        return bubbles
    
    def detect_id_section(self, bubbles):
        """Detect Student ID section (usually at the top)"""
        if not bubbles:
            return None
        
        # Find the smallest Y coordinate (topmost bubbles)
        min_y = min(bubble["y"] for bubble in bubbles)
        max_y = min_y + 100  # ID section height (adjust as needed)
        
        # Filter bubbles in the ID section
        id_bubbles = [b for b in bubbles if min_y <= b["y"] <= max_y]
        
        if not id_bubbles:
            print("❌ Could not detect ID section")
            return None
        
        # Find the bounding box of ID section
        min_x = min(b["x"] for b in id_bubbles)
        max_x = max(b["x"] + b["w"] for b in id_bubbles)
        min_y_id = min(b["y"] for b in id_bubbles)
        max_y_id = max(b["y"] + b["h"] for b in id_bubbles)
        
        # Detect rows and columns
        y_positions = sorted(set(b["y"] for b in id_bubbles))
        x_positions = sorted(set(b["x"] for b in id_bubbles))
        
        print(f"\n🆔 Student ID Section Detected:")
        print(f"   Location: ({min_x}, {min_y_id}) to ({max_x}, {max_y_id})")
        print(f"   Width: {max_x - min_x} pixels")
        print(f"   Height: {max_y_id - min_y_id} pixels")
        print(f"   Rows: {len(y_positions)} (digits per column)")
        print(f"   Columns: {len(x_positions)} (number of digits)")
        
        # Calculate digit dimensions
        if len(x_positions) > 1:
            digit_spacing = (max_x - min_x) / len(x_positions)
        else:
            digit_spacing = 35
        
        if len(y_positions) > 1:
            digit_height = (max_y_id - min_y_id) / len(y_positions)
        else:
            digit_height = 35
        
        return {
            "x": min_x,
            "y": min_y_id,
            "width": max_x - min_x,
            "height": max_y_id - min_y_id,
            "num_digits": len(x_positions),
            "digit_width": int(digit_spacing),
            "digit_height": int(digit_height),
            "options": len(y_positions)
        }
    
    def detect_answer_section(self, bubbles, id_section):
        """Detect answers section (questions 1-20)"""
        if not bubbles or not id_section:
            return None
        
        # Answer section starts below ID section
        start_y = id_section["y"] + id_section["height"] + 20
        
        # Filter answer bubbles (below ID section)
        answer_bubbles = [b for b in bubbles if b["y"] > start_y]
        
        if not answer_bubbles:
            print("❌ Could not detect answer section")
            return None
        
        # Find bounding box
        min_x = min(b["x"] for b in answer_bubbles)
        max_x = max(b["x"] + b["w"] for b in answer_bubbles)
        min_y = min(b["y"] for b in answer_bubbles)
        max_y = max(b["y"] + b["h"] for b in answer_bubbles)
        
        # Group by question (same Y coordinate)
        questions = {}
        for bubble in answer_bubbles:
            y = bubble["y"]
            if y not in questions:
                questions[y] = []
            questions[y].append(bubble)
        
        # Sort questions by Y coordinate
        sorted_questions = sorted(questions.items())
        
        # Calculate question height
        if len(sorted_questions) > 1:
            question_height = sorted_questions[1][0] - sorted_questions[0][0]
        else:
            question_height = 45
        
        # Calculate option spacing
        if sorted_questions and len(sorted_questions[0][1]) > 1:
            options = sorted(sorted_questions[0][1], key=lambda b: b["x"])
            if len(options) > 1:
                option_spacing = options[1]["x"] - options[0]["x"]
            else:
                option_spacing = 50
        else:
            option_spacing = 50
        
        print(f"\n📝 Answer Section Detected:")
        print(f"   Location: ({min_x}, {min_y}) to ({max_x}, {max_y})")
        print(f"   Total questions: {len(sorted_questions)}")
        print(f"   Question height: {question_height} pixels")
        print(f"   Option spacing: {option_spacing} pixels")
        print(f"   Options per question: {len(sorted_questions[0][1]) if sorted_questions else 4}")
        
        return {
            "start_x": min_x,
            "start_y": min_y,
            "end_x": max_x,
            "end_y": max_y,
            "width": max_x - min_x,
            "height": max_y - min_y,
            "total_questions": len(sorted_questions),
            "question_height": question_height,
            "option_spacing": option_spacing,
            "options_per_q": len(sorted_questions[0][1]) if sorted_questions else 4,
            "option_width": answer_bubbles[0]["w"] if answer_bubbles else 30,
            "option_height": answer_bubbles[0]["h"] if answer_bubbles else 30
        }
    
    def detect_thresholds(self, bubbles):
        """Calculate optimal threshold values based on bubble sizes"""
        if not bubbles:
            return {"min_black_pixels": 150, "max_black_pixels": 800}
        
        areas = [b["area"] for b in bubbles]
        
        # Calculate statistics
        mean_area = np.mean(areas)
        std_area = np.std(areas)
        
        min_area = mean_area * 0.5  # 50% of mean
        max_area = mean_area * 1.5  # 150% of mean
        
        print(f"\n🎯 Threshold Recommendations:")
        print(f"   Min black pixels: {int(min_area)}")
        print(f"   Max black pixels: {int(max_area)}")
        print(f"   Mean bubble area: {mean_area:.0f} pixels")
        
        return {
            "min_black_pixels": int(min_area),
            "max_black_pixels": int(max_area),
            "fill_ratio": 0.7,
            "confidence_threshold": 0.8,
            "mean_bubble_area": float(mean_area)
        }
    
    def generate_configuration(self):
        """Generate complete configuration file"""
        print("\n" + "="*60)
        print("🔧 GENERATING OMR CONFIGURATION")
        print("="*60)
        
        # Detect all components
        sheet = self.detect_sheet_boundary()
        bubbles = self.detect_all_bubbles()
        id_section = self.detect_id_section(bubbles)
        answer_section = self.detect_answer_section(bubbles, id_section)
        thresholds = self.detect_thresholds(bubbles)
        
        # Create configuration
        config = {
            "PREPROCESS": {
                "blur_kernel": [5, 5],
                "threshold_block_size": 15,
                "threshold_constant": 3,
                "min_bubble_area": thresholds["min_black_pixels"] // 2,
                "max_bubble_area": thresholds["max_black_pixels"] * 2
            },
            "STUDENT_ID": {
                "x": id_section["x"] if id_section else 150,
                "y": id_section["y"] if id_section else 80,
                "width": id_section["width"] if id_section else 400,
                "height": id_section["height"] if id_section else 60,
                "num_digits": id_section["num_digits"] if id_section else 10,
                "digit_width": id_section["digit_width"] if id_section else 35,
                "digit_height": id_section["digit_height"] if id_section else 35,
                "options": id_section["options"] if id_section else 4
            },
            "ANSWERS": {
                "start_x": answer_section["start_x"] if answer_section else 150,
                "start_y": answer_section["start_y"] if answer_section else 200,
                "question_height": answer_section["question_height"] if answer_section else 45,
                "total_questions": answer_section["total_questions"] if answer_section else 20,
                "options_per_q": answer_section["options_per_q"] if answer_section else 4,
                "option_width": answer_section["option_width"] if answer_section else 30,
                "option_height": answer_section["option_height"] if answer_section else 30,
                "option_spacing": answer_section["option_spacing"] if answer_section else 50
            },
            "THRESHOLDS": thresholds,
            "GRADING": {
                "marks_per_question": 1,
                "negative_marking": False,
                "negative_marks": 0
            }
        }
        
        # Save to file
        with open("omr_configuration.json", "w") as f:
            json.dump(config, f, indent=2)
        
        print("\n" + "="*60)
        print("✅ CONFIGURATION SAVED!")
        print("="*60)
        print(f"   File: omr_configuration.json")
        
        # Also generate Python config code
        self.generate_python_config(config)
        
        return config
    
    def generate_python_config(self, config):
        """Generate Python config.py file content"""
        python_code = f'''"""
Auto-generated OMR Configuration
Generated by calibrate.py
"""

class OMRConfig:
    """OMR Sheet Configuration"""
    
    # Image preprocessing settings
    PREPROCESS = {{
        "blur_kernel": {config["PREPROCESS"]["blur_kernel"]},
        "threshold_block_size": {config["PREPROCESS"]["threshold_block_size"]},
        "threshold_constant": {config["PREPROCESS"]["threshold_constant"]},
        "min_bubble_area": {config["PREPROCESS"]["min_bubble_area"]},
        "max_bubble_area": {config["PREPROCESS"]["max_bubble_area"]}
    }}
    
    # Student ID configuration
    STUDENT_ID = {{
        "x": {config["STUDENT_ID"]["x"]},
        "y": {config["STUDENT_ID"]["y"]},
        "width": {config["STUDENT_ID"]["width"]},
        "height": {config["STUDENT_ID"]["height"]},
        "num_digits": {config["STUDENT_ID"]["num_digits"]},
        "digit_width": {config["STUDENT_ID"]["digit_width"]},
        "digit_height": {config["STUDENT_ID"]["digit_height"]},
        "options": {config["STUDENT_ID"]["options"]}
    }}
    
    # Answers configuration
    ANSWERS = {{
        "start_x": {config["ANSWERS"]["start_x"]},
        "start_y": {config["ANSWERS"]["start_y"]},
        "question_height": {config["ANSWERS"]["question_height"]},
        "total_questions": {config["ANSWERS"]["total_questions"]},
        "options_per_q": {config["ANSWERS"]["options_per_q"]},
        "option_width": {config["ANSWERS"]["option_width"]},
        "option_height": {config["ANSWERS"]["option_height"]},
        "option_spacing": {config["ANSWERS"]["option_spacing"]}
    }}
    
    # Bubble detection thresholds
    THRESHOLDS = {{
        "min_black_pixels": {config["THRESHOLDS"]["min_black_pixels"]},
        "max_black_pixels": {config["THRESHOLDS"]["max_black_pixels"]},
        "fill_ratio": {config["THRESHOLDS"]["fill_ratio"]},
        "confidence_threshold": {config["THRESHOLDS"]["confidence_threshold"]}
    }}
    
    # Grading settings
    GRADING = {{
        "marks_per_question": {config["GRADING"]["marks_per_question"]},
        "negative_marking": {config["GRADING"]["negative_marking"]},
        "negative_marks": {config["GRADING"]["negative_marks"]}
    }}
    
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
'''
        
        # Save Python config
        with open("config_auto.py", "w") as f:
            f.write(python_code)
        
        print(f"   Python config: config_auto.py")
    
    def visualize_detection(self, output_path="calibrated_output.jpg"):
        """Create visualization of detected areas"""
        # Create a copy for drawing
        vis_image = self.original.copy()
        
        # Detect components
        sheet = self.detect_sheet_boundary()
        bubbles = self.detect_all_bubbles()
        id_section = self.detect_id_section(bubbles)
        answer_section = self.detect_answer_section(bubbles, id_section)
        
        # Draw sheet boundary (Green)
        if sheet:
            cv2.rectangle(vis_image, 
                         (sheet["x"], sheet["y"]),
                         (sheet["x"] + sheet["width"], sheet["y"] + sheet["height"]),
                         (0, 255, 0), 3)
            cv2.putText(vis_image, "Sheet Boundary", (sheet["x"], sheet["y"] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Draw ID section (Blue)
        if id_section:
            cv2.rectangle(vis_image,
                         (id_section["x"], id_section["y"]),
                         (id_section["x"] + id_section["width"], 
                          id_section["y"] + id_section["height"]),
                         (255, 0, 0), 2)
            cv2.putText(vis_image, "Student ID Area", 
                       (id_section["x"], id_section["y"] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        # Draw answer section (Red)
        if answer_section:
            cv2.rectangle(vis_image,
                         (answer_section["start_x"], answer_section["start_y"]),
                         (answer_section["end_x"], answer_section["end_y"]),
                         (0, 0, 255), 2)
            cv2.putText(vis_image, "Answers Area", 
                       (answer_section["start_x"], answer_section["start_y"] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Draw individual bubbles (Yellow dots)
        for bubble in bubbles[:100]:  # Limit for performance
            cv2.circle(vis_image, 
                      (bubble["center_x"], bubble["center_y"]), 
                      3, (0, 255, 255), -1)
        
        # Add information text
        info_text = [
            f"Total Bubbles: {len(bubbles)}",
            f"Image Size: {self.width}x{self.height}",
            f"Questions: {answer_section['total_questions'] if answer_section else 'N/A'}"
        ]
        
        y_offset = 30
        for text in info_text:
            cv2.putText(vis_image, text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += 25
        
        # Save visualization
        cv2.imwrite(output_path, vis_image)
        print(f"\n📸 Visualization saved: {output_path}")
        
        return vis_image
    
    def interactive_calibration(self):
        """Interactive calibration with mouse clicks"""
        print("\n" + "="*60)
        print("🖱️ INTERACTIVE CALIBRATION MODE")
        print("="*60)
        print("\nInstructions:")
        print("1. Click on the TOP-LEFT corner of Student ID area")
        print("2. Click on the BOTTOM-RIGHT corner of Student ID area")
        print("3. Click on the FIRST QUESTION's 'A' option")
        print("4. Click on the LAST QUESTION's 'D' option")
        print("5. Press 'q' to quit")
        print("6. Press 'c' to capture coordinates")
        
        points = []
        
        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                points.append((x, y))
                print(f"   Point {len(points)}: ({x}, {y})")
                
                # Draw point
                cv2.circle(param, (x, y), 5, (0, 255, 0), -1)
                cv2.putText(param, f"{len(points)}", (x+10, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.imshow("Interactive Calibration", param)
        
        # Create window
        window_name = "Interactive Calibration"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, mouse_callback, self.original)
        
        while True:
            cv2.imshow(window_name, self.original)
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('c') and len(points) >= 4:
                # Generate config from points
                config = self.generate_config_from_points(points)
                print("\n✅ Configuration generated from your clicks!")
                break
        
        cv2.destroyAllWindows()
        return points
    
    def generate_config_from_points(self, points):
        """Generate configuration from manually clicked points"""
        if len(points) < 4:
            print("❌ Need at least 4 points!")
            return None
        
        # ID section (points 0 and 1)
        id_x, id_y = points[0]
        id_width = points[1][0] - points[0][0]
        id_height = points[1][1] - points[0][1]
        
        # Answer section (points 2 and 3)
        ans_start_x, ans_start_y = points[2]
        ans_end_x, ans_end_y = points[3]
        
        config = {
            "STUDENT_ID": {
                "x": id_x, "y": id_y,
                "width": id_width, "height": id_height,
                "num_digits": 10, "digit_width": id_width // 10,
                "digit_height": id_height // 4, "options": 4
            },
            "ANSWERS": {
                "start_x": ans_start_x, "start_y": ans_start_y,
                "end_x": ans_end_x, "end_y": ans_end_y,
                "total_questions": 20, "options_per_q": 4,
                "question_height": (ans_end_y - ans_start_y) // 20,
                "option_width": 30, "option_height": 30,
                "option_spacing": (ans_end_x - ans_start_x) // 4
            }
        }
        
        # Save config
        with open("manual_config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        print("\n✅ Manual configuration saved to 'manual_config.json'")
        return config
    
    def run_full_calibration(self):
        """Run complete calibration process"""
        print("\n" + "="*60)
        print("🚀 STARTING FULL CALIBRATION")
        print("="*60)
        
        # Auto detection
        config = self.generate_configuration()
        
        # Visualization
        self.visualize_detection()
        
        print("\n" + "="*60)
        print("✅ CALIBRATION COMPLETE!")
        print("="*60)
        print("\nFiles generated:")
        print("   1. omr_configuration.json - Complete configuration")
        print("   2. config_auto.py - Python config file")
        print("   3. calibrated_output.jpg - Visualization image")
        print("\n📝 Next steps:")
        print("   1. Copy values from config_auto.py to app/config.py")
        print("   2. Run 'python test_omr.py' to test")
        print("   3. Start API server with 'uvicorn app.main:app --reload'")
        
        return config


def main():
    """Main calibration function"""
    print("="*60)
    print("🎯 OMR SHEET CALIBRATION TOOL")
    print("="*60)
    
    # Ask for image file
    print("\nPlease provide your OMR sheet image:")
    print("1. Enter file path (or)")
    print("2. Use default 'Perfec_filled.png'")
    
    choice = input("\nEnter choice (1/2): ").strip()
    
    if choice == "1":
        image_path = input("Enter image path: ").strip()
        if not os.path.exists(image_path):
            print(f"❌ File not found: {image_path}")
            return
    else:
        image_path = "Perfec_filled.png"
        if not os.path.exists(image_path):
            print(f"❌ Default image not found: {image_path}")
            print("Please place your OMR sheet image as 'Perfec_filled.png'")
            return
    
    try:
        # Create calibrator
        calibrator = OMSCalibrator(image_path)
        
        # Choose calibration mode
        print("\nCalibration Mode:")
        print("1. Automatic (Recommended)")
        print("2. Interactive (Manual click)")
        
        mode = input("Enter choice (1/2): ").strip()
        
        if mode == "2":
            calibrator.interactive_calibration()
        else:
            calibrator.run_full_calibration()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()




























# """
# Run this script FIRST to find exact coordinates of your OMR sheet
# This will help you configure the correct values
# """

# import cv2
# import numpy as np
# import json

# def calibrate_omr_sheet(image_path: str):
#     """Interactive calibration tool for OMR sheet"""
    
#     # Load image
#     image = cv2.imread(image_path)
#     if image is None:
#         print(f"❌ Could not load image: {image_path}")
#         return
    
#     print("=" * 60)
#     print("OMR Sheet Calibration Tool")
#     print("=" * 60)
#     print(f"Image size: {image.shape}")
    
#     # Display image
#     cv2.imshow("OMR Sheet - Click on points", image)
#     cv2.setMouseCallback("OMR Sheet - Click on points", click_event, image)
    
#     print("\nInstructions:")
#     print("1. Click on the TOP-LEFT of Student ID area")
#     print("2. Click on the BOTTOM-RIGHT of Student ID area")
#     print("3. Click on the FIRST QUESTION's A option")
#     print("4. Click on the FIRST QUESTION's D option")
#     print("5. Press 'q' to quit")
    
#     points = []
    
#     cv2.waitKey(0)
#     cv2.destroyAllWindows()
    
#     # Save coordinates
#     if points:
#         with open("omr_coordinates.json", "w") as f:
#             json.dump(points, f, indent=2)
#         print(f"\n✅ Coordinates saved to omr_coordinates.json")
#         print("\nUse these values in config.py:")
#         print(f'STUDENT_ID = {{"x": {points[0][0]}, "y": {points[0][1]}, ...}}')
#         print(f'ANSWERS = {{"start_x": {points[2][0]}, "start_y": {points[2][1]}, ...}}')

# def click_event(event, x, y, flags, param):
#     """Mouse callback for calibration"""
#     if event == cv2.EVENT_LBUTTONDOWN:
#         print(f"Clicked at: ({x}, {y})")
#         points.append((x, y))
        
#         # Draw point on image
#         cv2.circle(param, (x, y), 5, (0, 255, 0), -1)
#         cv2.putText(param, f"({x},{y})", (x+10, y-10), 
#                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
#         cv2.imshow("OMR Sheet - Click on points", param)

# def auto_calibrate(image_path: str):
#     """Automatic calibration using contour detection"""
    
#     image = cv2.imread(image_path)
#     gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
#     # Find largest rectangle (the OMR sheet)
#     edges = cv2.Canny(gray, 50, 150)
#     contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
#     if contours:
#         largest_contour = max(contours, key=cv2.contourArea)
#         x, y, w, h = cv2.boundingRect(largest_contour)
        
#         print(f"\n📐 Auto-detected sheet boundaries:")
#         print(f"Top-left: ({x}, {y})")
#         print(f"Bottom-right: ({x+w}, {y+h})")
#         print(f"Width: {w}, Height: {h}")
        
#         # Estimated answer region (adjust based on your sheet)
#         answer_start_y = y + int(h * 0.35)  # ~35% from top
#         answer_height = int(h * 0.55)       # ~55% of sheet
        
#         print(f"\n📝 Suggested Answer Region:")
#         print(f"start_y: {answer_start_y}")
#         print(f"question_height: {answer_height // 20}")  # Divide among 20 questions
        
#         return {
#             "sheet": {"x": x, "y": y, "w": w, "h": h},
#             "answer_start_y": answer_start_y,
#             "question_height": answer_height // 20
#         }
    
#     return None

# if __name__ == "__main__":
#     # First try auto-calibration
#     print("Auto-calibrating...")
#     result = auto_calibrate("Perfec_filled.png")
    
#     # Then manual calibration if needed
#     print("\n" + "="*60)
#     print("For manual calibration, run this script with:")
#     print("calibrate_omr_sheet('your_image.jpg')")