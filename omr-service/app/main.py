
# ////////////            test file ::



"""FastAPI backend for the fixed-layout 20-question OMR sheet."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

try:
    from app.omr_processor import OMRProcessor
except ImportError:
    from omr_processor import OMRProcessor


ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}
MAX_FILE_BYTES = 10 * 1024 * 1024

app = FastAPI(
    title="OMR Processing Service",
    description="Reads Student ID and 20 MCQ answers from the configured OMR sheet.",
    version="5.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

processor = OMRProcessor()


def _error(message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": message},
    )


async def _read_image(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Only JPEG and PNG images are allowed")

    data = await file.read()
    if not data:
        raise ValueError("Uploaded file is empty")
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("File size exceeds the 10 MB limit")
    return data


async def _process_upload(file: UploadFile, debug: bool = False) -> Dict[str, Any]:
    data = await _read_image(file)
    # OpenCV processing is CPU-bound; do not block FastAPI's event loop.
    return await run_in_threadpool(processor.process_image, data, True, debug)


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "service": "OMR Processing Service",
        "version": "5.0.0",
        "status": "running",
        "sheet": "8-digit Student ID + 20 MCQ answers",
        "endpoints": {
            "health": "GET /health",
            "process": "POST /process",
            "process_handwritten": "POST /process-handwritten",
            "process_batch": "POST /process-batch",
            "grade": "POST /grade",
            "docs": "GET /docs",
        },
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy", "version": "5.0.0"}


@app.post("/process")
async def process_omr(
    file: UploadFile = File(...),
    debug: bool = False,
) -> JSONResponse:
    try:
        result = await _process_upload(file, debug=debug)
        return JSONResponse(status_code=200 if result.get("success") else 422, content=result)
    except ValueError as exc:
        return _error(str(exc), 400)
    except Exception as exc:  # defensive API boundary
        return _error(f"Server error: {exc}", 500)


@app.post("/process-handwritten")
async def process_handwritten(
    file: UploadFile = File(...),
    debug: bool = False,
) -> JSONResponse:
    """Backward-compatible alias of /process."""
    return await process_omr(file=file, debug=debug)


@app.post("/process-batch")
async def process_batch(
    files: List[UploadFile] = File(...),
    debug: bool = False,
) -> JSONResponse:
    results: List[Dict[str, Any]] = []
    for file in files:
        try:
            result = await _process_upload(file, debug=debug)
            result["filename"] = file.filename
        except ValueError as exc:
            result = {
                "success": False,
                "filename": file.filename,
                "error": str(exc),
            }
        except Exception as exc:
            result = {
                "success": False,
                "filename": file.filename,
                "error": f"Server error: {exc}",
            }
        results.append(result)

    return JSONResponse(
        content={
            "success": all(item.get("success") for item in results),
            "total_processed": len(results),
            "results": results,
        }
    )


@app.post("/grade")
async def grade_omr(
    file: UploadFile = File(...),
    answer_key: str = Form(...),
    student_id: Optional[str] = Form(None),
    exam_id: Optional[str] = Form(None),
    debug: bool = False,
) -> JSONResponse:
    """Process one sheet and compare answers with a JSON answer key.

    Example answer_key value:
    {"1":"A","2":"B",...,"20":"D"}
    """
    try:
        parsed_key = json.loads(answer_key)
        if not isinstance(parsed_key, dict):
            raise ValueError("answer_key must be a JSON object")

        normalized_key: Dict[str, str] = {}
        for question, answer in parsed_key.items():
            value = str(answer).upper()
            if value not in {"A", "B", "C", "D"}:
                raise ValueError(f"Invalid answer for question {question}: {answer}")
            normalized_key[str(question)] = value

        result = await _process_upload(file, debug=debug)
        if not result.get("success"):
            return JSONResponse(status_code=422, content=result)

        grading = processor.grade_exam(result["answers"], normalized_key)
        return JSONResponse(
            content={
                "success": True,
                "student_id": student_id or result.get("student_id"),
                "detected_student_id": result.get("student_id"),
                "exam_id": exam_id,
                "processing_result": result,
                "grading_result": grading,
            }
        )
    except json.JSONDecodeError:
        return _error("answer_key is not valid JSON", 400)
    except ValueError as exc:
        return _error(str(exc), 400)
    except Exception as exc:
        return _error(f"Server error: {exc}", 500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)