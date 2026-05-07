import cv2
import numpy as np
from app.omr_processor import OMRProcessor

def create_test_image():
    """Create a test image with bubbles"""
    image = np.ones((800, 600, 3), dtype=np.uint8) * 255
    
    # Draw test bubbles
    cv2.rectangle(image, (100, 50), (400, 130), (0, 0, 0), 2)
    
    for i in range(20):
        y = 200 + i * 50
        cv2.rectangle(image, (100, y), (500, y+40), (0, 0, 0), 2)
        options_x = [150, 200, 250, 300]
        for x in options_x:
            cv2.circle(image, (x+15, y+20), 10, (0, 0, 0), 2)
    
    cv2.imwrite("test_image.jpg", image)
    print("✅ Test image created: test_image.jpg")
    return image

def test_processor():
    print("=" * 50)
    print("Testing OMR Processor...")
    print("=" * 50)
    
    # Create test image
    test_image = create_test_image()
    
    # Convert to bytes
    _, img_encoded = cv2.imencode('.jpg', test_image)
    image_bytes = img_encoded.tobytes()
    
    # Process
    processor = OMRProcessor()
    result = processor.process_image(image_bytes)
    
    print("\n📊 Results:")
    print(f"Success: {result.get('success')}")
    print(f"Student ID: {result.get('student_id')}")
    print(f"Total Questions: {result.get('total_questions')}")
    print(f"Answered: {result.get('total_answered')}")
    
    return result

if __name__ == "__main__":
    test_processor()
    print("\n✅ Testing complete!")