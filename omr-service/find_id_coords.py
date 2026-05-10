# save as: find_id_coords.py
import cv2
import numpy as np

img = cv2.imread("test_images/Perfect_filled.png")
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
_, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

# ID এলাকা crop করে save করুন (visual check এর জন্য)
# বিভিন্ন y value test করুন
for y_start in [125, 140, 155, 165, 175]:
    region = binary[y_start:y_start+200, 855:855+380]
    cv2.imwrite(f"id_y{y_start}.png", region)
    print(f"Saved id_y{y_start}.png — check which one shows bubbles clearly")