# 🔵 OMR Service — Automated MCQ Answer Sheet Scanner

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python" />
  <img src="https://img.shields.io/badge/FastAPI-0.104.1-009688?style=flat-square&logo=fastapi" />
  <img src="https://img.shields.io/badge/OpenCV-4.8.1-5C3EE8?style=flat-square&logo=opencv" />
  <img src="https://img.shields.io/badge/Status-Phase%201%20Active-brightgreen?style=flat-square" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" />
</p>

A production-ready **Optical Mark Recognition (OMR)** backend service that automatically reads scanned MCQ answer sheets using computer vision. Upload a photo or scan of a filled answer sheet — get structured JSON with the student ID and all 20 answers in milliseconds.

---

## 📋 Table of Contents

- [What It Does](#-what-it-does)
- [How It Works](#-how-it-works)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Calibration (Required First Step)](#-calibration-required-first-step)
- [Running Tests](#-running-tests)
- [Starting the API Server](#-starting-the-api-server)
- [API Reference](#-api-reference)
- [Configuration Tuning](#-configuration-tuning)
- [Docker Deployment](#-docker-deployment)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)

---

## 🎯 What It Does

| Without This Service | With This Service |
|---|---|
| Teacher checks each sheet by hand | Upload image → get answers in JSON instantly |
| Slow and error-prone | Fast, consistent, automated |
| No data, just paper | Structured output ready for databases |
| Cannot scale | Handles bulk processing via API |

**Answer Sheet Specs Supported:**
- Student ID: 10-digit columns, bubbles 1–4 per digit
- Questions: 1 to 20
- Options per question: A, B, C, D
- Bubble style: Fully filled black circle = selected

---

## ⚙️ How It Works

```
Student fills OMR sheet
        ↓
Sheet is scanned / photographed
        ↓
Image uploaded to API  →  POST /process
        ↓
OpenCV pipeline: grayscale → blur → threshold → contour detection
        ↓
Bubbles detected and classified per question
        ↓
Returns JSON  →  { student_id, answers[], confidence }
        ↓
Compare with answer key  →  Grade!
```

---

## 📁 Project Structure

```
omr-service/
│
├── app/
│   ├── __init__.py          ← Makes app a Python package
│   ├── main.py              ← FastAPI server & all API endpoints
│   ├── config.py            ← Pixel coordinates & detection thresholds
│   ├── omr_processor.py     ← Core CV pipeline: image → answers
│   ├── utils.py             ← Helper functions
│   └── calibrate.py         ← Tool to find exact bubble coordinates
│
├── test_images/
│   ├── sample_omr.jpg       ← Sample blank sheet
│   └── Perfec_filled.png    ← Sample filled sheet for testing
│
├── requirements.txt         ← Python dependencies
├── test_omr.py              ← Basic smoke test
├── test_with_your_sheet.py  ← Full test + grading report
├── Dockerfile               ← Container deployment
└── README.md                ← This file
```

---

## 🛠️ Prerequisites

Make sure these are installed on your system before you start:

| Tool | Minimum Version | Check Command |
|---|---|---|
| Python | 3.9+ | `python --version` |
| pip | Latest | `pip --version` |
| Git | Any | `git --version` |

> **Windows users:** Use [Python.org installer](https://www.python.org/downloads/) and check "Add Python to PATH" during install.

---

## 📦 Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/your-username/omr-service.git
cd omr-service
```

### Step 2 — Create a virtual environment

```bash
# macOS / Linux
python -m venv venv
source venv/bin/activate

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

You should see `(venv)` appear in your terminal prompt — that means it worked.

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

**`requirements.txt` contents:**

```
fastapi==0.104.1
uvicorn==0.24.0
opencv-python==4.8.1.78
numpy==1.24.3
python-multipart==0.0.6
```

### Step 4 — Verify installation

```bash
python -c "import cv2, numpy, fastapi; print('✅ All dependencies installed successfully')"
```

---

## 🎯 Calibration (Required First Step)

> ⚠️ **Do this before running any tests.** Calibration maps pixel coordinates on your specific sheet design. If you skip this, bubble detection will be wrong.

Calibration only needs to be done **once per sheet design**. If you change the sheet layout or scan resolution, recalibrate.

```bash
python app/calibrate.py
```

This will:
1. Scan your sheet image and auto-detect boundaries
2. Print the pixel coordinates to the console
3. Save them to `omr_coordinates.json`

After calibration, copy the output coordinates into `app/config.py`.

**For a new or custom sheet**, run manual calibration (click-to-mark mode):

```bash
python app/calibrate.py --manual
```

---

## 🧪 Running Tests

### Basic test — with the included sample image

Place your filled OMR sheet image in the `test_images/` folder, then run:

```bash
python test_with_your_sheet.py
```

**Expected output:**

```
============================================================
  Testing: ./test_images/Written_Img_1.png
============================================================
  File size: 245.3 KB

============================================================
  PROCESSING RESULT
============================================================
  Success     : True
  Student ID  : 1234567890
  Image Type  : written
  Answered    : 20/20
  Blank       : 0
  Confidence  : 95.0%

  📝 Detected Answers:
  ----------------------------------------
    Q 1: A                Q11: C
    Q 2: B                Q12: D
    Q 3: C                Q13: A
    ...
```

---

### Test with a custom image

```bash
python test_with_your_sheet.py --image path/to/your/sheet.png
```

---

### Debug mode — visualize what the scanner sees

This saves a `debug_answers.png` file showing which bubbles were detected:

```bash
python test_with_your_sheet.py --debug
```

Open `debug_answers.png` after running — it shows:
- Green circles = detected filled bubbles
- Red circles = detected empty bubbles
- Yellow boxes = question regions

This is the **most useful tool** for diagnosing wrong detections.

```bash
# Debug mode on a specific image
python test_with_your_sheet.py --image test_images/Written_Img_1.png --debug
```

---

### Test with a custom answer key

Pass your answer key as a JSON string to get a grading report:

```bash
python test_with_your_sheet.py --key '{"1":"A","2":"B","3":"C","4":"D","5":"A","6":"B","7":"C","8":"D","9":"A","10":"B","11":"C","12":"D","13":"A","14":"B","15":"C","16":"B","17":"D","18":"C","19":"B","20":"A"}'
```

**Grading report output:**

```
============================================================
  GRADING REPORT
============================================================
  Student ID : 1234567890

  Q#    Student    Key        Status
  ----------------------------------------
  1     A          A          ✓ Correct
  2     B          B          ✓ Correct
  3     C          C          ✓ Correct
  ...

  ========================================

  Correct    : 18/20
  Wrong      : 2
  Blank      : 0
  Score      : 90.0%
  Grade      : A+
```

---

### All test command options

| Command | What It Does |
|---|---|
| `python test_with_your_sheet.py` | Run with default sample image |
| `python test_with_your_sheet.py --image PATH` | Test with your own image |
| `python test_with_your_sheet.py --debug` | Save debug visualization |
| `python test_with_your_sheet.py --key '{...}'` | Test + full grading report |
| `python test_with_your_sheet.py --image PATH --debug --key '{...}'` | All options combined |

---

## 🚀 Starting the API Server

```bash
uvicorn app.main:app --reload --port 8001
```

You should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

Open your browser and visit:
- **API Docs (Swagger UI):** http://localhost:8001/docs
- **Health Check:** http://localhost:8001/health
- **Service Info:** http://localhost:8001/

> Remove `--reload` in production (it's for development hot-reloading only).

---

## 📡 API Reference

### `GET /health`

Check if the service is running.

**Response:**
```json
{ "status": "healthy" }
```

---

### `POST /process`

Upload a single OMR sheet image and get answers.

**Request:**
```
Content-Type: multipart/form-data
Field: file  →  your image (.jpg or .png)
```

**cURL example:**
```bash
curl -X POST http://localhost:8001/process \
  -F "file=@test_images/Perfec_filled.png"
```

**Response:**
```json
{
  "success": true,
  "student_id": "1234567890",
  "answers": ["A", "B", "C", "D", "A", "B", null, "D", "A", "B",
              "C", "D", "A", "B", "C", "B", "D", "C", "B", "A"],
  "total_answered": 19,
  "total_blank": 1,
  "total_questions": 20,
  "confidence": 0.95
}
```

> `null` in answers = that question was left blank.
> `confidence` = ratio of answered questions (0.0 to 1.0).

---

### `POST /process-batch`

Upload multiple sheets at once.

**cURL example:**
```bash
curl -X POST http://localhost:8001/process-batch \
  -F "files=@sheet1.png" \
  -F "files=@sheet2.png"
```

---

### `POST /calibrate`

Auto-detect sheet boundaries from an uploaded image.

```bash
curl -X POST http://localhost:8001/calibrate \
  -F "file=@blank_sheet.png"
```

---

## 🔧 Configuration Tuning

Edit `app/config.py` to adjust detection behavior.

| Problem | Setting to Change | Direction |
|---|---|---|
| Noise detected as filled bubble | `min_black_pixels` | Increase (e.g. 150 → 250) |
| Filled bubbles not detected | `min_black_pixels` | Decrease (e.g. 150 → 80) |
| Wrong question rows | `start_y`, `question_height` | Re-calibrate |
| Wrong option columns | `start_x`, `option_spacing` | Re-calibrate |
| Aspect ratio too strict | `aspect_ratio` range | Widen (e.g. 0.6 → 1.4) |

---

## 🐳 Docker Deployment

### Build and run

```bash
# Build the image
docker build -t omr-service .

# Run the container
docker run -p 8001:8001 omr-service
```

### Run with a custom test image volume

```bash
docker run -p 8001:8001 \
  -v $(pwd)/test_images:/app/test_images \
  omr-service
```

The service will be available at `http://localhost:8001`.

---

## 🩺 Troubleshooting

### Import error when running test script

```
❌ Import failed: No module named 'omr_processor'
```

**Fix:** Run from the project root, not from inside `app/`:

```bash
# ✅ Correct
cd omr-service
python test_with_your_sheet.py

# ❌ Wrong
cd omr-service/app
python test_with_your_sheet.py
```

---

### OpenCV installation fails on Linux

```bash
sudo apt-get update
sudo apt-get install -y libglib2.0-0 libsm6 libxrender1 libxext6
pip install opencv-python-headless==4.8.1.78
```

> Use `opencv-python-headless` instead of `opencv-python` on headless servers (no display).

---

### Low confidence score (below 80%)

1. Run `--debug` mode and inspect `debug_answers.png`
2. Check lighting — even, no shadows
3. Check alignment — sheet should be straight, not rotated more than ~5°
4. Increase scan resolution if using a scanner
5. Adjust `min_black_pixels` in `config.py`

---

### Server won't start — port already in use

```bash
# Find what's using port 8001
lsof -i :8001       # macOS / Linux
netstat -ano | findstr :8001   # Windows

# Use a different port
uvicorn app.main:app --reload --port 8002
```

---

## 🗺️ Roadmap

### ✅ Phase 1 — Core OMR Service (Current)
- FastAPI server with `/process` endpoint
- OpenCV bubble detection pipeline
- Student ID + 20-question answer extraction
- Calibration tool
- Grading report generator with A+/F scale

### 🔜 Phase 2 — API Gateway & Auth
- API key authentication
- Rate limiting per key
- Request/response logging
- API Gateway integration

### 🔜 Phase 3 — Production
- Perspective correction for skewed/rotated sheets
- Database storage of results
- Web dashboard for viewing and exporting results
- Batch processing endpoint
- Docker Compose with database

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

<p align="center">Built with ❤️ using Python, FastAPI, and OpenCV</p>