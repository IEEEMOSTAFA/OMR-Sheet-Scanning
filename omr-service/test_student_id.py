









# test_student_id.py
"""
Comprehensive Student ID Detection Test
"""

import cv2
import numpy as np
from app.omr_processor import OMRProcessor
from app.config import OMRConfig
import json

def test_id_detection(image_path: str):
    """Test only Student ID detection with detailed output"""
    
    print("=" * 70)
    print("🎯 STUDENT ID DETECTION TEST")
    print("=" * 70)
    
    # Load image
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    # Create processor
    processor = OMRProcessor()
    
    # Process
    result = processor.process_image(image_bytes)
    
    print("\n" + "=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    
    if result.get('success'):
        print(f"\n✅ Processing Successful!")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📝 Student ID: {result.get('student_id')}")
        print(f"📊 Total Questions: {result.get('total_questions')}")
        print(f"✅ Answered: {result.get('total_answered')}")
        print(f"⬜ Blank: {result.get('total_blank')}")
        print(f"🎯 Confidence: {result.get('confidence', 0)*100:.1f}%")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # Show answers
        answers = result.get('answers', [])
        print("\n📝 Answers Details:")
        print("-" * 50)
        
        # Show in groups of 5 for readability
        for i in range(0, 20, 5):
            q_range = f"Q{i+1}-{i+5}"
            ans_group = answers[i:i+5]
            ans_str = "  ".join([str(a) if a else '?' for a in ans_group])
            print(f"  {q_range}: {ans_str}")
        
        return result
    else:
        print(f"\n❌ Processing Failed!")
        print(f"Error: {result.get('error')}")
        return None

def debug_id_region(image_path: str):
    """Debug: Show exactly what the ID detection sees"""
    
    print("\n" + "=" * 70)
    print("🔍 ID REGION DEBUG")
    print("=" * 70)
    
    # Load image
    nparr = np.frombuffer(open(image_path, 'rb').read(), np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Preprocess
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY_INV)
    
    # Get ID config
    id_cfg = OMRConfig.STUDENT_ID
    
    print(f"\n📐 ID Configuration:")
    print(f"   X: {id_cfg['x']}")
    print(f"   Y: {id_cfg['y']}")
    print(f"   Width: {id_cfg['width']}")
    print(f"   Height: {id_cfg['height']}")
    print(f"   Digits: {id_cfg['num_digits']}")
    print(f"   Digit Width: {id_cfg['digit_width']}")
    print(f"   Digit Height: {id_cfg['digit_height']}")
    print(f"   Options: {id_cfg['options']}")
    
    # Extract ID region
    id_region = binary[id_cfg['y']:id_cfg['y']+id_cfg['height'], 
                       id_cfg['x']:id_cfg['x']+id_cfg['width']]
    
    # Save ID region for visual inspection
    cv2.imwrite('debug_id_region_extracted.png', id_region)
    print(f"\n📸 Saved ID region to: debug_id_region_extracted.png")
    
    # Analyze each digit column
    print("\n🔍 Digit-by-Digit Analysis:")
    print("-" * 60)
    
    for col in range(id_cfg["num_digits"]):
        col_x = id_cfg["x"] + col * id_cfg["digit_width"]
        print(f"\nDigit {col+1} (X={col_x}):")
        
        max_pixels = 0
        selected_digit = "?"
        
        for row in range(id_cfg["options"]):
            y_pos = id_cfg["y"] + row * id_cfg["digit_height"]
            roi = binary[
                y_pos: y_pos + id_cfg["digit_height"],
                col_x: col_x + id_cfg["digit_width"]
            ]
            
            if roi.size > 0:
                black_pixels = np.sum(roi == 255)
                fill_percentage = (black_pixels / roi.size) * 100
                
                # Show filled bubbles (more than 30% filled)
                if fill_percentage > 30:
                    print(f"   Row {row}: ███ {black_pixels:4d} pixels ({fill_percentage:.0f}% filled)")
                else:
                    print(f"   Row {row}: ░░░ {black_pixels:4d} pixels ({fill_percentage:.0f}% filled)")
                
                if black_pixels > max_pixels and black_pixels > OMRConfig.THRESHOLDS["min_black_pixels"]:
                    max_pixels = black_pixels
                    selected_digit = str(row)
        
        print(f"   └─ ✅ SELECTED: {selected_digit}")
    
    # Draw detected ID area on original image
    debug_img = image.copy()
    cv2.rectangle(debug_img, 
                  (id_cfg['x'], id_cfg['y']), 
                  (id_cfg['x']+id_cfg['width'], id_cfg['y']+id_cfg['height']),
                  (0, 255, 0), 3)
    
    cv2.imwrite('debug_id_area_marked.jpg', debug_img)
    print(f"\n📸 Saved marked ID area to: debug_id_area_marked.jpg")
    print("   Green rectangle shows the scanned ID region")

def compare_with_expected(result, expected_id: str = None):
    """Compare detected ID with expected value"""
    
    if not result or not result.get('success'):
        print("\n❌ Cannot compare - no valid result")
        return
    
    detected_id = result.get('student_id')
    
    if expected_id:
        print("\n" + "=" * 70)
        print("✅ ID VERIFICATION")
        print("=" * 70)
        print(f"Detected ID: {detected_id}")
        print(f"Expected ID: {expected_id}")
        
        if detected_id == expected_id:
            print("\n🎉 PERFECT! Student ID detected correctly!")
        else:
            print("\n⚠️ Student ID mismatch!")
            print(f"   Detected: {detected_id}")
            print(f"   Expected: {expected_id}")
            
            # Find differences
            max_len = max(len(detected_id), len(expected_id))
            print(f"\n   Comparison:")
            for i in range(max_len):
                det = detected_id[i] if i < len(detected_id) else '-'
                exp = expected_id[i] if i < len(expected_id) else '-'
                match = "✓" if det == exp else "✗"
                print(f"   Digit {i+1}: {det} vs {exp} {match}")

if __name__ == "__main__":
    # Test image path
    image_path = "test_images/Perfect_filled.png"
    
    # Run tests
    print("🚀 Starting Student ID Verification Suite\n")
    
    # 1. Test detection
    result = test_id_detection(image_path)
    
    # 2. Debug the ID region
    debug_id_region(image_path)
    
    # 3. Compare with expected ID (if known)
    # Replace with your actual student ID from the sheet
    EXPECTED_STUDENT_ID = "1234567890"  # ← CHANGE THIS to your actual ID
    compare_with_expected(result, EXPECTED_STUDENT_ID)
    
    print("\n" + "=" * 70)
    print("📝 SUMMARY")
    print("=" * 70)
    print("""
    If Student ID is CORRECT:
        ✅ Great! Your config is working perfectly!
        
    If Student ID is STILL WRONG:
        1. Check 'debug_id_area_marked.jpg' - is the green box around the ID bubbles?
        2. Check 'debug_id_region_extracted.png' - can you see the bubbles clearly?
        3. Adjust coordinates in config.py based on what you see
    
    If Student ID shows '?' or '66676776':
        - Threshold too high: Reduce 'min_black_pixels' in config.py
        - Wrong coordinates: Update STUDENT_ID x, y values
    """)