import cv2
import numpy as np


class PerspectiveCorrector:
    def __init__(self, image_path):
        self.image_path = image_path
        self.image = cv2.imread(image_path)

        if self.image is None:
            raise ValueError(f"Cannot load image: {image_path}")

        self.original = self.image.copy()

    def resize_image(self, height=1000):
        """Resize image while keeping aspect ratio"""

        ratio = self.image.shape[0] / height

        width = int(self.image.shape[1] / ratio)

        resized = cv2.resize(self.image, (width, height))

        return resized, ratio

    def preprocess(self, image):
        """Preprocess image for edge detection"""

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        edged = cv2.Canny(blurred, 75, 200)

        return edged

    def find_document_contour(self, edged):
        """Find biggest 4-point contour"""

        contours, _ = cv2.findContours(
            edged,
            cv2.RETR_LIST,
            cv2.CHAIN_APPROX_SIMPLE
        )

        contours = sorted(
            contours,
            key=cv2.contourArea,
            reverse=True
        )[:10]

        for contour in contours:

            perimeter = cv2.arcLength(contour, True)

            approx = cv2.approxPolyDP(
                contour,
                0.02 * perimeter,
                True
            )

            if len(approx) == 4:
                return approx

        return None

    def order_points(self, pts):
        """Order points: top-left, top-right, bottom-right, bottom-left"""

        rect = np.zeros((4, 2), dtype="float32")

        s = pts.sum(axis=1)

        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)

        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        return rect

    def four_point_transform(self, image, pts):
        """Apply perspective transform"""

        rect = self.order_points(pts)

        (tl, tr, br, bl) = rect

        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)

        maxWidth = max(int(widthA), int(widthB))

        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)

        maxHeight = max(int(heightA), int(heightB))

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")

        matrix = cv2.getPerspectiveTransform(rect, dst)

        warped = cv2.warpPerspective(
            image,
            matrix,
            (maxWidth, maxHeight)
        )

        return warped

    def correct_perspective(self, output_path="corrected_omr.jpg"):
        """Main correction pipeline"""

        resized, ratio = self.resize_image()

        edged = self.preprocess(resized)

        contour = self.find_document_contour(edged)

        if contour is None:
            raise ValueError("Could not detect OMR sheet boundary")

        contour = contour.reshape(4, 2) * ratio

        warped = self.four_point_transform(
            self.original,
            contour
        )

        cv2.imwrite(output_path, warped)

        print(f"✅ Perspective corrected image saved: {output_path}")

        return warped


if __name__ == "__main__":

    # image_path = "../test_images/Perfect_image3.png"
    image_path = "./test_images/Perfect_image3.png"

    corrector = PerspectiveCorrector(image_path)

    corrected = corrector.correct_perspective()