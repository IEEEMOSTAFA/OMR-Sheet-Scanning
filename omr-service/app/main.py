"""
FastAPI Server for OMR Processing Service
Handwritten MCQ Answer Sheet Detection Support Added
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import tempfile
import cv2
import numpy as np
import json
import base64
from io import BytesIO

# ✅ Local imports (app/ ফোল্ডার থেকে রান করলে):
from omr_processor import OMRProcessor
from config import OMRConfig

# ─────────────────────────────────────────────
# FastAPI App Initialization
# ─────────────────────────────────────────────
app = FastAPI(
    title="OMR Processing Service",
    description="Automatic MCQ answer sheet checking service (Handwritten Support)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OMR Processor initialize
processor = OMRProcessor()


# ─────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────
class AnswerKey(BaseModel):
    answer_key: Dict[str, str]  # {"1": "A", "2": "B", ...}

class GradeRequest(BaseModel):
    exam_id: str
    answer_key: AnswerKey

class ProcessResponse(BaseModel):
    success: bool
    student_id: Optional[str] = None
    answers: Optional[List[Optional[str]]] = None
    total_answered: Optional[int] = None
    total_blank: Optional[int] = None
    total_questions: Optional[int] = None
    confidence: Optional[float] = None
    error: Optional[str] = None


# ─────────────────────────────────────────────
# 🔧 CORE: Handwritten OMR Detection Engine
# ─────────────────────────────────────────────

class HandwrittenOMRDetector:
    """
    Handwritten MCQ Answer Sheet এর জন্য specially designed detector।
    
    কাজ করে:
    1. Image preprocess করে (grayscale, blur, threshold)
    2. Bubble/circle গুলো detect করে
    3. কোন bubble filled সেটা বের করে
    4. প্রতিটি question এর answer (A/B/C/D) determine করে
    """

    def __init__(self, num_questions: int = 20, num_choices: int = 4):
        self.num_questions = num_questions
        self.num_choices = num_choices
        self.choices = ["A", "B", "C", "D"]

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Image কে detect করার উপযোগী করে তোলে।
        Steps:
        - Grayscale convert
        - Gaussian blur (noise কমায়)
        - Adaptive threshold (আলোর variation handle করে)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Gaussian blur দিয়ে noise কমাই
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Adaptive threshold — হাতে লেখা sheet এ আলো সমান থাকে না,
        # তাই adaptive use করি (fixed threshold কাজ করে না ভালো)
        thresh = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=15,
            C=4
        )
        return thresh

    def find_bubbles(self, thresh: np.ndarray) -> List[tuple]:
        """
        Threshold image থেকে সব bubble (circle) খুঁজে বের করে।
        HoughCircles ব্যবহার করে circular bubble detect করা হয়।
        """
        # HoughCircles: circle detect করার সবচেয়ে ভালো method
        circles = cv2.HoughCircles(
            thresh,
            cv2.HOUGH_GRADIENT,
            dp=1.2,          # accumulator resolution ratio
            minDist=20,      # দুটো circle এর minimum distance
            param1=50,       # Canny edge upper threshold
            param2=18,       # accumulator threshold (কমালে বেশি circle ধরে)
            minRadius=8,     # minimum bubble radius (pixel)
            maxRadius=22     # maximum bubble radius (pixel)
        )

        if circles is None:
            return []

        circles = np.round(circles[0, :]).astype("int")
        return [(x, y, r) for x, y, r in circles]

    def is_bubble_filled(
        self,
        thresh: np.ndarray,
        cx: int,
        cy: int,
        radius: int,
        fill_ratio_threshold: float = 0.45
    ) -> bool:
        """
        একটি bubble filled কিনা তা নির্ধারণ করে।
        
        কিভাবে কাজ করে:
        - Bubble এর ভেতরে circular mask বানাই
        - সেই mask এ কতটুকু white pixel আছে দেখি
        - যদি 45%+ pixel সাদা হয় → filled bubble
        
        Note: threshold image এ filled bubble = white (bright) দেখায়
        কারণ THRESH_BINARY_INV use করেছি
        """
        mask = np.zeros(thresh.shape, dtype="uint8")
        cv2.circle(mask, (cx, cy), radius - 3, 255, -1)  # -1 = filled circle

        masked_region = cv2.bitwise_and(thresh, thresh, mask=mask)
        total_pixels = cv2.countNonZero(mask)
        filled_pixels = cv2.countNonZero(masked_region)

        if total_pixels == 0:
            return False

        ratio = filled_pixels / total_pixels
        return ratio >= fill_ratio_threshold

    def group_bubbles_into_questions(
        self,
        bubbles: List[tuple],
        image_width: int,
        image_height: int
    ) -> Dict[int, List[tuple]]:
        """
        Detect করা bubbles গুলোকে question অনুযায়ী group করে।
        
        Strategy:
        - Sheet কে left/right দুই column এ ভাগ করি
        - Left: Q1-Q10, Right: Q11-Q20
        - Y position অনুযায়ী sort করে question number assign করি
        - প্রতিটি question এ 4টি bubble (A,B,C,D)
        """
        if not bubbles:
            return {}

        mid_x = image_width // 2

        # Left column (Q1-Q10) এবং Right column (Q11-Q20) আলাদা করি
        left_bubbles = [(x, y, r) for x, y, r in bubbles if x < mid_x]
        right_bubbles = [(x, y, r) for x, y, r in bubbles if x >= mid_x]

        questions = {}

        def assign_questions(bubble_list: List[tuple], q_start: int, q_end: int):
            """
            একটি column এর bubbles কে questions এ assign করে।
            Y coordinate অনুযায়ী sort করে rows তৈরি করে।
            """
            if not bubble_list:
                return

            # Y অনুযায়ী sort
            sorted_by_y = sorted(bubble_list, key=lambda b: b[1])

            # Row clustering: কাছাকাছি Y value এর bubbles একই row এ
            rows = []
            current_row = [sorted_by_y[0]]
            row_threshold = 18  # pixel tolerance

            for bubble in sorted_by_y[1:]:
                if abs(bubble[1] - current_row[0][1]) <= row_threshold:
                    current_row.append(bubble)
                else:
                    rows.append(current_row)
                    current_row = [bubble]
            rows.append(current_row)

            # প্রতিটি row কে একটি question এ map করি
            expected_q_count = q_end - q_start + 1
            
            # শুধু valid rows নিই (যেগুলোতে 2-4 bubbles আছে)
            valid_rows = [row for row in rows if 2 <= len(row) <= 4]
            
            for i, row in enumerate(valid_rows):
                if i >= expected_q_count:
                    break
                q_num = q_start + i
                # X অনুযায়ী sort করে A,B,C,D order নিশ্চিত করি
                questions[q_num] = sorted(row, key=lambda b: b[0])

        assign_questions(left_bubbles, 1, 10)
        assign_questions(right_bubbles, 11, 20)

        return questions

    def detect_answers(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Main detection function।
        Image bytes নিয়ে সব process করে answers return করে।
        
        Returns:
            {
                "success": True/False,
                "answers": {"1": "A", "2": "B", ...},
                "raw_answers": ["A", "B", ...],  # index = question number - 1
                "confidence": 0.0-1.0,
                "debug_info": {...}
            }
        """
        try:
            # Bytes থেকে image load করি
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return {"success": False, "error": "Image decode করা যায়নি"}

            h, w = image.shape[:2]

            # ── Step 1: Preprocess ──
            thresh = self.preprocess_image(image)

            # ── Step 2: Bubble খোঁজো ──
            bubbles = self.find_bubbles(thresh)

            if len(bubbles) < self.num_questions:
                # Fallback: threshold adjust করে আবার চেষ্টা
                bubbles = self._fallback_bubble_detection(thresh)

            # ── Step 3: Questions এ group করো ──
            question_groups = self.group_bubbles_into_questions(bubbles, w, h)

            # ── Step 4: প্রতিটি question এর answer বের করো ──
            answers_dict: Dict[str, Optional[str]] = {}
            raw_answers: List[Optional[str]] = []
            filled_count = 0

            for q_num in range(1, self.num_questions + 1):
                if q_num not in question_groups:
                    answers_dict[str(q_num)] = None
                    raw_answers.append(None)
                    continue

                row_bubbles = question_groups[q_num]
                selected_answer = None
                max_fill_ratio = 0.0

                for idx, (cx, cy, r) in enumerate(row_bubbles):
                    if idx >= len(self.choices):
                        break

                    # Fill ratio calculate করি
                    mask = np.zeros(thresh.shape, dtype="uint8")
                    cv2.circle(mask, (cx, cy), r - 3, 255, -1)
                    total_px = cv2.countNonZero(mask)
                    masked = cv2.bitwise_and(thresh, thresh, mask=mask)
                    fill_px = cv2.countNonZero(masked)

                    if total_px > 0:
                        ratio = fill_px / total_px
                        if ratio > max_fill_ratio:
                            max_fill_ratio = ratio
                            if ratio >= 0.45:  # threshold
                                selected_answer = self.choices[idx]

                answers_dict[str(q_num)] = selected_answer
                raw_answers.append(selected_answer)
                if selected_answer:
                    filled_count += 1

            # Confidence: কতটা প্রশ্নের bubble ভালোভাবে detect হয়েছে
            detected_q = len(question_groups)
            confidence = round(detected_q / self.num_questions, 2)

            return {
                "success": True,
                "answers": answers_dict,
                "raw_answers": raw_answers,
                "total_questions": self.num_questions,
                "total_answered": filled_count,
                "total_blank": self.num_questions - filled_count,
                "confidence": confidence,
                "debug_info": {
                    "total_bubbles_found": len(bubbles),
                    "questions_detected": detected_q,
                    "image_size": f"{w}x{h}"
                }
            }

        except Exception as e:
            return {"success": False, "error": f"Detection error: {str(e)}"}

    def _fallback_bubble_detection(self, thresh: np.ndarray) -> List[tuple]:
        """
        HoughCircles কাজ না করলে contour-based fallback।
        কিছু হাতে লেখা sheet এ bubble perfect circle না হওয়ায় এটা দরকার।
        """
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        bubbles = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 150 < area < 1500:  # bubble size range
                perimeter = cv2.arcLength(cnt, True)
                if perimeter == 0:
                    continue
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                if circularity > 0.5:  # circular shape
                    (x, y), radius = cv2.minEnclosingCircle(cnt)
                    bubbles.append((int(x), int(y), int(radius)))
        return bubbles

    def grade_answers(
        self,
        detected_answers: Dict[str, Optional[str]],
        answer_key: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Detected answers কে answer key এর সাথে compare করে grade দেয়।
        """
        correct = 0
        wrong = 0
        blank = 0
        details = []

        for q_num_str, correct_ans in answer_key.items():
            student_ans = detected_answers.get(q_num_str)

            if student_ans is None:
                status = "blank"
                blank += 1
            elif student_ans.upper() == correct_ans.upper():
                status = "correct"
                correct += 1
            else:
                status = "wrong"
                wrong += 1

            details.append({
                "question": q_num_str,
                "student_answer": student_ans,
                "correct_answer": correct_ans,
                "status": status
            })

        total = len(answer_key)
        score = round((correct / total) * 100, 2) if total > 0 else 0.0

        return {
            "correct": correct,
            "wrong": wrong,
            "blank": blank,
            "total": total,
            "score_percent": score,
            "details": details
        }


# ─────────────────────────────────────────────
# Detector instance (global, reuse করা হবে)
# ─────────────────────────────────────────────
omr_detector = HandwrittenOMRDetector(num_questions=20, num_choices=4)


# ─────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OMR Processing Service",
        "version": "2.0.0",
        "handwritten_support": True,
        "status": "running",
        "endpoints": {
            "health": "GET /health",
            "process": "POST /process",
            "process_handwritten": "POST /process-handwritten",  # ✅ NEW
            "process_batch": "POST /process-batch",
            "grade": "POST /grade",
            "grade_handwritten": "POST /grade-handwritten",      # ✅ NEW
            "docs": "GET /docs"
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "omr-service",
        "version": "2.0.0",
        "handwritten_support": True
    }


# ✅ NEW ENDPOINT: Handwritten OMR Process
@app.post("/process-handwritten")
async def process_handwritten_omr(
    file: UploadFile = File(...),
    num_questions: int = 20,
    debug: bool = False
):
    """
    হাতে লেখা MCQ answer sheet process করে।
    
    - **file**: OMR sheet এর image (JPEG/PNG)
    - **num_questions**: মোট প্রশ্ন সংখ্যা (default: 20)
    - **debug**: True হলে extra debug info দেবে
    
    Returns detected answers, confidence score, blank count।
    """
    # File type validate
    if file.content_type not in ["image/jpeg", "image/jpg", "image/png"]:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "শুধুমাত্র JPEG/PNG image allowed"}
        )

    try:
        image_bytes = await file.read()

        if len(image_bytes) == 0:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Empty file পাঠানো হয়েছে"}
            )

        if len(image_bytes) > 10 * 1024 * 1024:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "File size 10MB এর বেশি"}
            )

        # Detector এ question count update করি (যদি ভিন্ন হয়)
        detector = HandwrittenOMRDetector(
            num_questions=num_questions,
            num_choices=4
        )

        result = detector.detect_answers(image_bytes)

        if not result["success"]:
            return JSONResponse(status_code=400, content=result)

        # Debug info না চাইলে remove করি
        if not debug:
            result.pop("debug_info", None)

        return JSONResponse(content=result)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Server error: {str(e)}"}
        )


# ✅ NEW ENDPOINT: Handwritten OMR Grade
@app.post("/grade-handwritten")
async def grade_handwritten_omr(
    file: UploadFile = File(...),
    student_id: str = "unknown",
    exam_id: str = "exam_001",
    answer_key: str = None,  # JSON string: '{"1":"A","2":"B",...}'
    num_questions: int = 20
):
    """
    হাতে লেখা OMR sheet process করে এবং grade দেয়।
    
    - **file**: OMR sheet image
    - **student_id**: Student এর ID
    - **exam_id**: Exam ID
    - **answer_key**: JSON format এ correct answers: '{"1":"A","2":"B"}'
    - **num_questions**: মোট প্রশ্ন সংখ্যা
    """
    if file.content_type not in ["image/jpeg", "image/jpg", "image/png"]:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "শুধুমাত্র JPEG/PNG allowed"}
        )

    try:
        image_bytes = await file.read()

        detector = HandwrittenOMRDetector(
            num_questions=num_questions,
            num_choices=4
        )

        # ── Step 1: Detect answers ──
        detection_result = detector.detect_answers(image_bytes)

        if not detection_result["success"]:
            return JSONResponse(status_code=400, content=detection_result)

        response_data = {
            "success": True,
            "student_id": student_id,
            "exam_id": exam_id,
            "detected_answers": detection_result["answers"],
            "total_questions": detection_result["total_questions"],
            "total_answered": detection_result["total_answered"],
            "total_blank": detection_result["total_blank"],
            "confidence": detection_result["confidence"],
        }

        # ── Step 2: Grade যদি answer key দেওয়া হয় ──
        if answer_key:
            key_dict = json.loads(answer_key)
            grading = detector.grade_answers(detection_result["answers"], key_dict)
            response_data["grading"] = grading

        return JSONResponse(content=response_data)

    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "answer_key JSON format সঠিক নয়। Example: '{\"1\":\"A\",\"2\":\"B\"}'"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Server error: {str(e)}"}
        )


# ─────────────────────────────────────────────
# পুরনো Endpoints (Backward Compatibility রক্ষার জন্য)
# ─────────────────────────────────────────────

@app.post("/process", response_model=ProcessResponse)
async def process_omr_sheet(
    file: UploadFile = File(...),
    apply_perspective: bool = False
):
    """
    পুরনো /process endpoint (backward compatible)।
    নতুন কাজের জন্য /process-handwritten ব্যবহার করুন।
    """
    if file.content_type not in ["image/jpeg", "image/jpg", "image/png"]:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Only JPEG/PNG images are allowed"}
        )

    try:
        image_bytes = await file.read()

        if len(image_bytes) > 10 * 1024 * 1024:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "File size too large. Maximum 10MB allowed"}
            )

        if len(image_bytes) == 0:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Empty file"}
            )

        # পুরনো processor দিয়ে try করি, fail হলে নতুন detector দিয়ে
        try:
            result = processor.process_image(image_bytes, apply_perspective)
        except Exception:
            # Fallback to new handwritten detector
            result = omr_detector.detect_answers(image_bytes)
            if result["success"]:
                # পুরনো format এ convert করি
                raw_answers = result.get("raw_answers", [])
                result = {
                    "success": True,
                    "answers": raw_answers,
                    "total_answered": result.get("total_answered", 0),
                    "total_blank": result.get("total_blank", 0),
                    "total_questions": result.get("total_questions", 20),
                    "confidence": result.get("confidence", 0.0)
                }

        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            return JSONResponse(content=result, status_code=400)

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Server error: {str(e)}"}
        )


@app.post("/process-batch")
async def process_batch(
    files: List[UploadFile] = File(...),
    apply_perspective: bool = False
):
    """
    একসাথে অনেক OMR sheet process করে।
    """
    results = []

    for file in files:
        try:
            if file.content_type not in ["image/jpeg", "image/jpg", "image/png"]:
                results.append({
                    "success": False,
                    "filename": file.filename,
                    "error": "Invalid file type. Only JPEG/PNG allowed"
                })
                continue

            image_bytes = await file.read()

            # নতুন handwritten detector ব্যবহার করি
            result = omr_detector.detect_answers(image_bytes)
            result["filename"] = file.filename
            results.append(result)

        except Exception as e:
            results.append({
                "success": False,
                "filename": file.filename,
                "error": str(e)
            })

    return JSONResponse(content={
        "success": True,
        "total_processed": len(results),
        "results": results
    })


@app.post("/grade")
async def grade_exam(
    student_id: str,
    exam_id: str,
    file: UploadFile = File(...),
    answer_key: str = None
):
    """
    পুরনো /grade endpoint (backward compatible)।
    """
    try:
        image_bytes = await file.read()

        # নতুন detector দিয়ে process করি
        result = omr_detector.detect_answers(image_bytes)

        if not result["success"]:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": result.get("error", "Unknown error")}
            )

        if answer_key:
            key = json.loads(answer_key)
            grading_result = omr_detector.grade_answers(result["answers"], key)

            return JSONResponse(content={
                "success": True,
                "student_id": student_id,
                "exam_id": exam_id,
                "processing_result": result,
                "grading_result": grading_result
            })
        else:
            return JSONResponse(content={
                "success": True,
                "student_id": student_id,
                "exam_id": exam_id,
                "processing_result": result
            })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/config")
async def get_config():
    """Current OMR configuration দেখায়"""
    return {
        "student_id": OMRConfig.STUDENT_ID,
        "answers": OMRConfig.ANSWERS,
        "thresholds": OMRConfig.THRESHOLDS,
        "grading": OMRConfig.GRADING,
        "handwritten_detector": {
            "num_questions": omr_detector.num_questions,
            "num_choices": omr_detector.num_choices,
            "fill_ratio_threshold": 0.45,
            "bubble_min_radius": 8,
            "bubble_max_radius": 22
        }
    }


# ─────────────────────────────────────────────
# Run Server
# ─────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )



