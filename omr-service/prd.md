# Product Requirements Document (PRD)
# OMR Service — Automated MCQ Answer Sheet Scanner

**Version:** 1.0  
**Type:** Backend Service (Python + FastAPI)  
**Status:** Phase 1 — Development

---

## 1. What Is This Project?

This is a backend **OMR (Optical Mark Recognition) service** that automatically reads scanned MCQ answer sheets and extracts student answers using computer vision.

Instead of a teacher manually checking 100+ answer sheets, this service:
1. Accepts a scanned answer sheet image
2. Detects which bubbles are filled
3. Returns the student ID and all 20 answers as JSON

Think of it as a **digital answer sheet checker** powered by Python and OpenCV.

---

## 2. The Problem It Solves

| Old Way (Manual) | New Way (This Service) |
|---|---|
| Teacher checks each sheet by hand | Upload image → get answers instantly |
| Slow, error-prone | Fast, consistent, automated |
| No data — just paper | Structured JSON output |
| Cannot scale | Handles bulk processing |

---

## 3. How It Works (Simple Flow)

```
Student fills OMR sheet
        ↓
Sheet is scanned / photographed
        ↓
Image uploaded to API (POST /process)
        ↓
OpenCV detects filled bubbles
        ↓
Returns JSON with Student ID + Answers
        ↓
Compare with answer key → Grade!
```

---

## 4. The OMR Sheet Structure

The answer sheet this service is built for has:

| Section | Details |
|---|---|
| Student ID | 10 digit columns, each with bubbles 1–4 |
| Answer Section | Questions 1 to 20 |
| Options per Question | 4 options — A, B, C, D |
| Bubble Style | Fully filled black circle = selected |

---

## 5. Project File Structure

```
omr-service/
│
├── app/
│   ├── __init__.py          ← Makes app a Python package
│   ├── main.py              ← FastAPI server, all API endpoints
│   ├── config.py            ← Coordinates & thresholds for the OMR sheet
│   ├── omr_processor.py     ← Core logic: image processing & bubble detection
│   ├── utils.py             ← Helper functions
│   └── calibrate.py        ← Tool to find exact bubble coordinates
│
├── test_images/
│   ├── sample_omr.jpg       ← Sample blank sheet
│   └── Perfec_filled.png    ← Sample filled sheet for testing
│
├── requirements.txt         ← All Python dependencies
├── test_omr.py              ← Basic test script
├── test_with_your_sheet.py  ← Test with a real image + grading report
├── Dockerfile               ← For containerized deployment
└── README.md                ← Setup guide
```

---

## 6. What Each File Does

### `app/config.py` — The Settings File
Stores all the pixel coordinates for where bubbles are located on the sheet.

- `STUDENT_ID` — defines x/y position, width, height of the ID bubble area
- `ANSWERS` — defines start position, spacing between questions and options
- `THRESHOLDS` — how many filled pixels count as a "selected" bubble

> ⚠️ These coordinates must be calibrated for your specific sheet. Run `calibrate.py` first.

---

### `app/omr_processor.py` — The Brain
This is the core engine. It runs a 6-step pipeline:

1. **Load image** from uploaded bytes
2. **Preprocess** — grayscale → blur → threshold → clean noise
3. **Find bubbles** — detect circular shapes using contour detection
4. **Extract Student ID** — read which digit bubbles are filled
5. **Extract Answers** — for each of 20 questions, find the filled option (A/B/C/D)
6. **Return result** — success flag, student ID, answers list, confidence score

---

### `app/main.py` — The API Server
A FastAPI server with these endpoints:

| Method | Endpoint | What It Does |
|---|---|---|
| GET | `/` | Service info & available endpoints |
| GET | `/health` | Check if server is running |
| POST | `/process` | Upload one OMR sheet image → get answers |
| POST | `/process-batch` | Upload multiple sheets at once |
| POST | `/calibrate` | Auto-detect sheet boundaries from an image |

---

### `app/calibrate.py` — The Coordinate Finder
Run this **before anything else** if you have a new sheet design.

- **Auto-calibrate** — scans the image to find the sheet boundary
- **Manual calibrate** — click on points in the image to record coordinates
- Saves coordinates to `omr_coordinates.json` which you then paste into `config.py`

---

### `test_with_your_sheet.py` — The Test + Grader
- Feeds `Perfec_filled.png` through the processor
- Prints all detected answers
- If you provide an answer key, it generates a full **grading report** with score, percentage and grade (A+, A, B, C, D, F)

---

## 7. API Input & Output

### Request (POST `/process`)
```
Content-Type: multipart/form-data
Field: file  →  your scanned image (.jpg or .png)
```

### Response (JSON)
```json
{
  "success": true,
  "student_id": "1234567890",
  "answers": ["A", "B", "C", "D", "A", "B", null, "D", ...],
  "total_answered": 18,
  "total_blank": 2,
  "total_questions": 20,
  "confidence": 0.90
}
```

- `null` in answers = blank (not filled)
- `confidence` = percentage of answered questions (0.0 to 1.0)

---

## 8. How Bubble Detection Works (Under the Hood)

```
Original Image
      ↓
Convert to Grayscale
      ↓
Gaussian Blur (remove noise)
      ↓
Adaptive Threshold (black/white only)
      ↓
Morphological Cleanup (fill gaps)
      ↓
Find Contours (all shapes)
      ↓
Filter by area + aspect ratio → bubbles!
      ↓
For each question row → count black pixels per option
      ↓
Option with most black pixels = selected answer
```

---

## 9. Step-by-Step: Running the Project

### Step 1 — Setup Environment
```bash
cd omr-service
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
pip install fastapi uvicorn opencv-python numpy python-multipart
```

### Step 2 — Calibrate Your Sheet
```bash
python app/calibrate.py
# Copy the printed coordinates into app/config.py
```

### Step 3 — Test With Your Image
```bash
# Put Perfec_filled.png in the root folder
python test_with_your_sheet.py
```

### Step 4 — Start the API Server
```bash
uvicorn app.main:app --reload --port 8001
```

### Step 5 — Test via Postman or curl
```bash
curl -X POST http://localhost:8001/process \
  -F "file=@Perfec_filled.png"
```

---

## 10. Configuration Tuning Guide

If detection results are wrong, adjust these values in `config.py`:

| Problem | What to Change | Direction |
|---|---|---|
| Detecting noise as filled | `min_black_pixels` | Increase (e.g. 150 → 250) |
| Missing filled bubbles | `min_black_pixels` | Decrease (e.g. 150 → 80) |
| Wrong question rows detected | `start_y` and `question_height` | Re-calibrate |
| Wrong option columns | `start_x` and `option_spacing` | Re-calibrate |
| Aspect ratio filtering too strict | `aspect_ratio` range in `_find_bubbles` | Widen (e.g. 0.6 to 1.4) |

---

## 11. Phase Roadmap

### ✅ Phase 1 — Python OMR Service (Current)
- FastAPI server with `/process` endpoint
- OpenCV-based bubble detection
- Student ID + 20 question answers
- Calibration tool
- Grading report generator

### 🔜 Phase 2 — API Gateway Integration
- Route requests through an API Gateway
- Add authentication (API keys)
- Rate limiting
- Request logging

### 🔜 Phase 3 — Production Features
- Batch processing (multiple sheets at once)
- Perspective correction for skewed/rotated images
- Database storage of results
- Web dashboard for viewing results
- Docker deployment

---

## 12. Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | Web API framework |
| `uvicorn` | ASGI server to run FastAPI |
| `opencv-python` | Image processing & bubble detection |
| `numpy` | Array operations on pixel data |
| `python-multipart` | Handle file uploads in FastAPI |

---

## 13. Known Limitations (Phase 1)

- Coordinates in `config.py` are hardcoded — must be re-calibrated for different sheet sizes or scan resolutions
- No perspective correction yet — sheet must be reasonably straight
- Student ID detection is basic — works best with high-contrast, clean scans
- No database — results are only returned in the API response, not stored

---

## 14. Success Criteria

The service is working correctly when:

- Server starts without errors on port 8001
- `GET /health` returns `{"status": "healthy"}`
- `POST /process` with `Perfec_filled.png` returns `"success": true`
- Detected answers match what was actually filled on the sheet
- Confidence score is above 80% for clean scans