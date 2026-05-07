"""
Utility functions for OMR processing
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional

class OMRUtils:
    
    @staticmethod
    def preprocess_image(image: np.ndarray) -> np.ndarray:
        """Convert image to binary (black and white) for bubble detection"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply adaptive threshold (works better for varying lighting)
        binary = cv2.adaptiveThreshold(
            blurred, 
            255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 
            15, 
            3
        )
        
        # Morphological operations to clean up noise
        kernel = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
        return cleaned
    
    @staticmethod
    def count_black_pixels(region: np.ndarray) -> int:
        """Count black pixels in a region (white in thresholded image)"""
        if region.size == 0:
            return 0
        return np.sum(region == 255)
    
    @staticmethod
    def detect_bubble(region: np.ndarray, threshold: int = 150) -> Tuple[bool, int]:
        """Detect if a bubble is filled"""
        black_pixels = OMRUtils.count_black_pixels(region)
        is_filled = black_pixels > threshold
        return is_filled, black_pixels
    
    @staticmethod
    def find_contours(image: np.ndarray) -> List:
        """Find all contours in the image"""
        contours, _ = cv2.findContours(
            image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        return contours
    
    @staticmethod
    def is_circular(contour, circularity_threshold: float = 0.7) -> bool:
        """Check if a contour is roughly circular (bubble shape)"""
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        
        if perimeter == 0:
            return False
        
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        return circularity > circularity_threshold
    
    @staticmethod
    def correct_perspective(image: np.ndarray) -> np.ndarray:
        """Auto-correct perspective of skewed OMR sheet"""
        # Find the largest contour (the OMR sheet)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours = OMRUtils.find_contours(edges)
        
        if contours:
            # Get largest contour
            largest = max(contours, key=cv2.contourArea)
            
            # Approximate polygon
            epsilon = 0.02 * cv2.arcLength(largest, True)
            approx = cv2.approxPolyDP(largest, epsilon, True)
            
            if len(approx) == 4:
                # Apply perspective transform
                return OMRUtils.four_point_transform(image, approx.reshape(4, 2))
        
        return image
    
    @staticmethod
    def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
        """Apply perspective transform to get bird's eye view"""
        # Rearrange points
        rect = OMRUtils.order_points(pts)
        (tl, tr, br, bl) = rect
        
        # Compute width
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        
        # Compute height
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        
        # Destination points
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")
        
        # Apply transform
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
        
        return warped
    
    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        """Order points in clockwise direction"""
        rect = np.zeros((4, 2), dtype="float32")
        
        # Sum and diff to find corners
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        return rect
    
    @staticmethod
    def visualize_bubbles(image: np.ndarray, bubbles: List, output_path: str):
        """Draw detected bubbles on image for debugging"""
        debug_img = image.copy()
        
        for (x, y, w, h) in bubbles:
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(debug_img, (x + w // 2, y + h // 2), 3, (0, 0, 255), -1)
        
        cv2.imwrite(output_path, debug_img)
        print(f"📸 Debug image saved: {output_path}")