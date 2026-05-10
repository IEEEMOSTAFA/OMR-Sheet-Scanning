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
    
    def preprocess_image(self):
        """Preprocess image for better detection"""
        blurred = cv2.GaussianBlur(self.gray, (5, 5), 0)
        binary = cv2.adaptiveThreshold(
            blurred, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 15, 3
        )
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
        
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        print(f"\n📄 Sheet Boundary Detected:")
        print(f"   Top-Left: ({x}, {y})")
        print(f"   Width: {w} pixels, Height: {h} pixels")
        
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
        
        return bubbles
    
    def detect_id_section(self, bubbles):
        """Detect Student ID section (usually at the top)"""
        if not bubbles:
            print("❌ No bubbles found for ID detection")
            return None
        
        # Find the smallest Y coordinate (topmost bubbles)
        min_y = min(bubble["y"] for bubble in bubbles)
        max_y = min_y + 200  # ID section height
        
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
        print(f"   Columns (digits): {len(x_positions)}")
        print(f"   Rows (options 0-9): {len(y_positions)}")
        
        # Calculate digit dimensions
        digit_width = (max_x - min_x) / len(x_positions) if x_positions else 35
        digit_height = (max_y_id - min_y_id) / len(y_positions) if y_positions else 20
        
        return {
            "x": min_x,
            "y": min_y_id,
            "width": max_x - min_x,
            "height": max_y_id - min_y_id,
            "num_digits": len(x_positions),
            "digit_width": int(digit_width),
            "digit_height": int(digit_height),
            "options": len(y_positions)
        }
    
    def detect_answer_section(self, bubbles, id_section):
        """Detect answers section (questions 1-20)"""
        if not bubbles:
            return None
        
        # Answer section starts below ID section
        start_y = id_section["y"] + id_section["height"] + 50 if id_section else 300
        
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
        
        print(f"\n📝 Answer Section Detected:")
        print(f"   Total questions: {len(sorted_questions)}")
        print(f"   Question height: {question_height} pixels")
        
        # Detect left and right columns if needed
        mid_x = (min_x + max_x) // 2
        left_questions = [q for q in sorted_questions if q[1][0]["x"] < mid_x]
        right_questions = [q for q in sorted_questions if q[1][0]["x"] > mid_x]
        
        print(f"   Left column questions: {len(left_questions)}")
        print(f"   Right column questions: {len(right_questions)}")
        
        # Get option X positions from first question
        if sorted_questions:
            first_q_bubbles = sorted(sorted_questions[0][1], key=lambda b: b["x"])
            option_x = [b["x"] for b in first_q_bubbles]
            print(f"   Option X positions: {option_x}")
        
        # Get row Y positions
        row_y = [q[0] for q in sorted_questions]
        
        return {
            "start_x": min_x,
            "start_y": min_y,
            "end_x": max_x,
            "end_y": max_y,
            "total_questions": len(sorted_questions),
            "question_height": question_height,
            "options_per_q": len(sorted_questions[0][1]) if sorted_questions else 4,
            "option_x": option_x if sorted_questions else [],
            "row_y": row_y,
            "bubble_width": answer_bubbles[0]["w"] if answer_bubbles else 35,
            "bubble_height": answer_bubbles[0]["h"] if answer_bubbles else 35
        }
    
    def generate_configuration(self):
        """Generate complete configuration file"""
        print("\n" + "="*60)
        print("🔧 GENERATING OMR CONFIGURATION")
        print("="*60)
        
        # Detect all components
        bubbles = self.detect_all_bubbles()
        id_section = self.detect_id_section(bubbles)
        answer_section = self.detect_answer_section(bubbles, id_section)
        
        if not answer_section:
            print("❌ Could not detect answer section!")
            return None
        
        # Create configuration
        config = {
            "STUDENT_ID": {
                "x": id_section["x"] if id_section else 150,
                "y": id_section["y"] if id_section else 80,
                "num_digits": id_section["num_digits"] if id_section else 10,
                "digit_width": id_section["digit_width"] if id_section else 35,
                "digit_height": id_section["digit_height"] if id_section else 20,
                "options": id_section["options"] if id_section else 10
            },
            "LEFT_COLUMN": {
                "option_x": [452, 539, 632, 725],  # Calibrate these!
                "row_y": answer_section["row_y"][:10] if len(answer_section["row_y"]) >= 10 else answer_section["row_y"],
                "bubble_width": answer_section["bubble_width"],
                "bubble_height": answer_section["bubble_height"]
            },
            "RIGHT_COLUMN": {
                "option_x": [999, 1085, 1174, 1269],  # Calibrate these!
                "row_y": answer_section["row_y"][10:20] if len(answer_section["row_y"]) >= 20 else answer_section["row_y"],
                "bubble_width": answer_section["bubble_width"],
                "bubble_height": answer_section["bubble_height"]
            },
            "ANSWERS": {
                "total_questions": answer_section["total_questions"],
                "options_per_q": answer_section["options_per_q"]
            },
            "THRESHOLDS": {
                "min_black_pixels": 55,
                "fill_threshold_pct": 0.18,
                "max_black_pixels": 1000,
                "fill_ratio": 0.4,
                "confidence_threshold": 0.8
            },
            "GRADING": {
                "marks_per_question": 1,
                "negative_marking": False,
                "negative_marks": 0
            }
        }
        
        # Save to file
        with open("omr_configuration.json", "w") as f:
            json.dump(config, f, indent=2)
        
        print("\n✅ Configuration saved to 'omr_configuration.json'")
        
        # Generate Python config
        self.generate_python_config(config, answer_section)
        
        return config
    
    def generate_python_config(self, config, answer_section):
        """Generate Python config.py file content"""
        
        # Prepare row_y as properly formatted string
        left_row_y = config["LEFT_COLUMN"]["row_y"]
        right_row_y = config["RIGHT_COLUMN"]["row_y"]
        
        python_code = f'''"""
Auto-generated OMR Configuration
Generated by calibrate.py
"""

class OMRConfig:
    """OMR Sheet Configuration"""
    
    # Student ID configuration
    STUDENT_ID = {{
        "x": {config["STUDENT_ID"]["x"]},
        "y": {config["STUDENT_ID"]["y"]},
        "num_digits": {config["STUDENT_ID"]["num_digits"]},
        "digit_width": {config["STUDENT_ID"]["digit_width"]},
        "digit_height": {config["STUDENT_ID"]["digit_height"]},
        "options": {config["STUDENT_ID"]["options"]}
    }}
    
    THRESHOLDS = {{
        "min_black_pixels": {config["THRESHOLDS"]["min_black_pixels"]},
        "fill_threshold_pct": {config["THRESHOLDS"]["fill_threshold_pct"]},
        "max_black_pixels": {config["THRESHOLDS"]["max_black_pixels"]},
        "fill_ratio": {config["THRESHOLDS"]["fill_ratio"]},
        "confidence_threshold": {config["THRESHOLDS"]["confidence_threshold"]}
    }}
    
    # Left column Q1-Q10
    LEFT_COLUMN = {{
        "option_x": [452, 539, 632, 725],
        "row_y": {left_row_y if left_row_y else [384, 434, 485, 536, 586, 636, 686, 736, 788, 838]},
        "bubble_width": {config["LEFT_COLUMN"]["bubble_width"]},
        "bubble_height": {config["LEFT_COLUMN"]["bubble_height"]},
    }}
    
    # Right column Q11-Q20
    RIGHT_COLUMN = {{
        "option_x": [999, 1085, 1174, 1269],
        "row_y": {right_row_y if right_row_y else [384, 434, 485, 536, 586, 636, 686, 736, 788, 838]},
        "bubble_width": {config["RIGHT_COLUMN"]["bubble_width"]},
        "bubble_height": {config["RIGHT_COLUMN"]["bubble_height"]},
    }}
    
    ANSWERS = {{
        "total_questions": {config["ANSWERS"]["total_questions"]},
        "options_per_q": {config["ANSWERS"]["options_per_q"]},
    }}
    
    GRADING = {{
        "marks_per_question": {config["GRADING"]["marks_per_question"]},
        "negative_marking": {config["GRADING"]["negative_marking"]},
        "negative_marks": {config["GRADING"]["negative_marks"]}
    }}
'''
        
        # Save Python config
        with open("config_auto.py", "w") as f:
            f.write(python_code)
        
        print(f"✅ Python config saved to 'config_auto.py'")
    
    def visualize_detection(self, output_path="calibrated_output.jpg"):
        """Create visualization of detected areas"""
        vis_image = self.original.copy()
        
        bubbles = self.detect_all_bubbles()
        id_section = self.detect_id_section(bubbles)
        answer_section = self.detect_answer_section(bubbles, id_section)
        
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
        for bubble in bubbles[:200]:
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
    
    def run_full_calibration(self):
        """Run complete calibration process"""
        print("\n" + "="*60)
        print("🚀 STARTING FULL CALIBRATION")
        print("="*60)
        
        config = self.generate_configuration()
        
        if config:
            self.visualize_detection()
            
            print("\n" + "="*60)
            print("✅ CALIBRATION COMPLETE!")
            print("="*60)
            print("\n📁 Files generated:")
            print("   1. omr_configuration.json - Complete configuration")
            print("   2. config_auto.py - Python config file")
            print("   3. calibrated_output.jpg - Visualization image")
            print("\n📝 Next steps:")
            print("   1. Copy values from config_auto.py to app/config.py")
            print("   2. Run 'python test_with_your_sheet.py' to test")
            print("   3. Start API server with 'uvicorn app.main:app --reload'")
        else:
            print("\n❌ Calibration failed! Try manual calibration.")
        
        return config


def auto_calibrate(image_path: str):
    """Quick auto-calibration function"""
    try:
        calibrator = OMSCalibrator(image_path)
        return calibrator.run_full_calibration()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


def main():
    """Main calibration function"""
    print("="*60)
    print("🎯 OMR SHEET CALIBRATION TOOL")
    print("="*60)
    
    # Ask for image file
    print("\n📁 Please provide your OMR sheet image:")
    # default_images = ["Perfect_image3.png", "Perfec_filled.png", "test_images/Perfect_image3.png"]
    default_images = ["../test_images/Perfect_image3.png"]
    
    image_path = None
    for img in default_images:
        if os.path.exists(img):
            image_path = img
            print(f"   Found default image: {image_path}")
            break
    
    if not image_path:
        image_path = input("Enter image path: ").strip()
        if not os.path.exists(image_path):
            print(f"❌ File not found: {image_path}")
            return
    
    try:
        calibrator = OMSCalibrator(image_path)
        calibrator.run_full_calibration()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()