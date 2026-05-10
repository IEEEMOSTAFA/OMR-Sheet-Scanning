"""
সহজ টেস্ট ফাইল - আপনার OMR শীট চেক করার জন্য
"""

import cv2
import numpy as np
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import OMRConfig
from app.omr_processor import OMRProcessor
from app.utils import OMRUtils

def test_omr_sheet(image_path):
    """একটি ইমেজ টেস্ট করুন"""
    
    print("\n" + "="*60)
    print("📝 OMR শীট টেস্ট শুরু")
    print("="*60)
    
    # ইমেজ পড়ুন
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    # প্রসেসর তৈরি করুন
    processor = OMRProcessor()
    
    # প্রসেস করুন
    result = processor.process_image(image_bytes)
    
    if result['success']:
        print("\n✅ সফলভাবে প্রসেস সম্পন্ন!")
        print(f"🎓 ছাত্র ID: {result['student_id']}")
        print(f"📊 মোট প্রশ্ন: {result['total_questions']}")
        print(f"✏️ উত্তর দেওয়া: {result['total_answered']}")
        print(f"⬜ ফাঁকা: {result['total_blank']}")
        
        print("\n📋 উত্তর তালিকা:")
        print("-"*30)
        for i, ans in enumerate(result['answers'], 1):
            status = ans if ans else "BLANK"
            print(f"প্রশ্ন {i:2d}: {status}")
        
        # ইমেজ ডিবাগ সেভ করলে দেখুন
        if os.path.exists("debug_student_id_region.png"):
            print("\n🔍 ডিবাগ ইমেজ সেভ হয়েছে: debug_student_id_region.png")
            print("   ফাইলটি খুলে দেখুন ID সঠিকভাবে ডিটেক্ট হয়েছে কিনা")
            
        return result
    else:
        print(f"\n❌ প্রসেস ফেল হয়েছে: {result.get('error')}")
        return None

def test_with_different_thresholds(image_path):
    """বিভিন্ন থ্রেশহোল্ড দিয়ে টেস্ট করে সঠিক মান বের করুন"""
    
    print("\n" + "="*60)
    print("🔧 থ্রেশহোল্ড ক্যালিব্রেশন টেস্ট")
    print("="*60)
    
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # প্রিপ্রসেস
    utils = OMRUtils()
    processed = utils.preprocess_image(image)
    
    # ID রিজিয়ন চেক করুন
    id_cfg = OMRConfig.STUDENT_ID
    id_region = processed[
        id_cfg["y"]:id_cfg["y"] + id_cfg["options"] * id_cfg["digit_height"],
        id_cfg["x"]:id_cfg["x"] + id_cfg["num_digits"] * id_cfg["digit_width"]
    ]
    
    cv2.imwrite("debug_id_region_raw.png", id_region)
    print("✓ ID রিজিয়ন সেভ হয়েছে: debug_id_region_raw.png")
    print("  ইমেজটি খুলে দেখুন - ডার্ক স্পটগুলো স্পষ্ট কিনা")
    
    # প্রতিটি কলামের ফিল পার্সেন্টেজ চেক
    print("\n📊 ID কলাম বিশ্লেষণ:")
    print("Col | 0   1   2   3   4   5   6   7   8   9  | Selected")
    print("-"*55)
    
    for col in range(id_cfg["num_digits"]):
        col_x = id_cfg["x"] + col * id_cfg["digit_width"]
        fills = []
        
        for row in range(10):
            y = id_cfg["y"] + row * id_cfg["digit_height"]
            roi = processed[y:y+id_cfg["digit_height"], col_x:col_x+id_cfg["digit_width"]]
            if roi.size > 0:
                fill_pct = np.sum(roi == 255) / roi.size
                fills.append(fill_pct)
            else:
                fills.append(0)
        
        max_fill = max(fills)
        selected = fills.index(max_fill) if max_fill > 0.12 else '?'
        
        # প্রিন্ট বার
        bar = ""
        for f in fills:
            if f > 0.12:
                bar += f"■ "
            else:
                bar += f"□ "
        
        print(f"{col+1:2d}  | {bar}| {selected}")
    
    return True

if __name__ == "__main__":
    # আপনার ইমেজ পাথ দিন
    IMAGE_PATH = "Perfect_image3.png"  # অথবা ফুল পাথ দিন
    
    if not os.path.exists(IMAGE_PATH):
        print(f"❌ ইমেজ পাওয়া যায়নি: {IMAGE_PATH}")
        print("\n👉 সঠিক পাথ দিন, যেমন:")
        print("   IMAGE_PATH = 'test_images/Perfect_image3.png'")
        print("   অথবা ফুল পাথ: 'C:/Users/.../Perfect_image3.png'")
        sys.exit(1)
    
    # টেস্ট 1: থ্রেশহোল্ড ক্যালিব্রেশন
    test_with_different_thresholds(IMAGE_PATH)
    
    # টেস্ট 2: ফুল প্রসেসিং
    result = test_omr_sheet(IMAGE_PATH)
    
    # যদি রেজাল্ট থাকে এবং উত্তর কী দেয়া থাকে
    if result and result['success']:
        print("\n" + "="*60)
        print("🎯 গ्रेडিং (যদি উত্তর কী থাকে)")
        print("="*60)
        
        # স্যাম্পল উত্তর কী
        answer_key = {
            "1": "A", "2": "B", "3": "C", "4": "D", "5": "A",
            "6": "B", "7": "C", "8": "D", "9": "A", "10": "B",
            "11": "C", "12": "D", "13": "A", "14": "B", "15": "C",
            "16": "D", "17": "A", "18": "B", "19": "C", "20": "D"
        }
        
        grade_result = processor.grade_exam(result['answers'], answer_key)
        print(f"\n✓ সঠিক: {grade_result['correct']}")
        print(f"✗ ভুল: {grade_result['wrong']}")
        print(f"⬜ ফাঁকা: {grade_result['blank']}")
        print(f"📊 পার্সেন্টেজ: {grade_result['percentage']}%")
        print(f"🏆 গ্রেড: {grade_result['grade']}")