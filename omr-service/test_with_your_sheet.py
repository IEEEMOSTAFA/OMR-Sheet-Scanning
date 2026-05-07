"""
Test the OMR processor with your actual OMR sheet image
"""

import cv2
import numpy as np
from app.omr_processor import OMRProcessor
import json

def test_with_your_sheet(image_path: str):
    """Test OMR processing with your actual sheet"""
    
    print("=" * 60)
    print(f"Testing with: {image_path}")
    print("=" * 60)
    
    # Read image
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    # Create processor
    processor = OMRProcessor()
    
    # Process
    result = processor.process_image(image_bytes)
    
    # Display results
    print("\n📊 Results:")
    print("-" * 40)
    print(f"Success: {result.get('success')}")
    
    if result.get('success'):
        print(f"Student ID: {result.get('student_id')}")
        print(f"Total Questions: {result.get('total_questions')}")
        print(f"Answered: {result.get('total_answered')}")
        print(f"Blank: {result.get('total_blank')}")
        print(f"Confidence: {result.get('confidence', 0)*100:.1f}%")
        
        print("\n📝 Answers:")
        answers = result.get('answers', [])
        for i, ans in enumerate(answers, 1):
            if ans:
                print(f"Q{i:2d}: {ans}")
            else:
                print(f"Q{i:2d}: --- (Blank)")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def generate_sample_report(exam_key: dict, results: dict):
    """Generate a sample report comparing with answer key"""
    
    print("\n" + "=" * 60)
    print("GRADING REPORT")
    print("=" * 60)
    
    if not results.get('success'):
        print("Cannot generate report - processing failed")
        return
    
    answers = results.get('answers', [])
    total = 0
    
    print(f"\nStudent ID: {results.get('student_id')}")
    print("\nQ# | Student | Key | Status")
    print("-" * 35)
    
    for i, (q_num, correct_ans) in enumerate(exam_key.items(), 1):
        student_ans = answers[i-1] if i-1 < len(answers) else None
        is_correct = student_ans == correct_ans
        
        if is_correct:
            total += 1
            status = "✓ Correct"
        elif student_ans is None:
            status = "○ Blank"
        else:
            status = "✗ Wrong"
        
        print(f"{i:2d}  | {student_ans or '-':7} | {correct_ans:3} | {status}")
    
    print("-" * 35)
    print(f"\nTotal Score: {total}/{len(exam_key)}")
    print(f"Percentage: {(total/len(exam_key))*100:.1f}%")
    
    # Grade
    percentage = (total/len(exam_key))*100
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
    
    print(f"Grade: {grade}")

if __name__ == "__main__":
    # Test with your OMR sheet
    image_file = "Perfec_filled.png"  # Your uploaded file name
    
    result = test_with_your_sheet(image_file)
    
    # If you have an answer key, generate report
    sample_answer_key = {
        "1": "A", "2": "B", "3": "C", "4": "D", "5": "A",
        "6": "B", "7": "C", "8": "D", "9": "A", "10": "B",
        "11": "C", "12": "D", "13": "A", "14": "B", "15": "C",
        "16": "D", "17": "A", "18": "B", "19": "C", "20": "D"
    }
    
    generate_sample_report(sample_answer_key, result)