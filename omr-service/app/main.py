"""
FastAPI Server for OMR Processing Service
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import os
import tempfile

# from app.omr_processor import OMRProcessor

# ✅ হওয়া উচিত (যদি app/ ফোল্ডার থেকে রান করেন):
from omr_processor import OMRProcessor
from config import OMRConfig

# Create FastAPI app
app = FastAPI(
    title="OMR Processing Service",
    description="Automatic MCQ answer sheet checking service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS (for API Gateway)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OMR Processor
processor = OMRProcessor()

# Request/Response Models
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

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "OMR Processing Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "GET /health",
            "process": "POST /process",
            "process_batch": "POST /process-batch",
            "grade": "POST /grade",
            "docs": "GET /docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "omr-service",
        "version": "1.0.0"
    }

@app.post("/process", response_model=ProcessResponse)
async def process_omr_sheet(
    file: UploadFile = File(...),
    apply_perspective: bool = False
):
    """
    Process a single OMR sheet image
    
    - **file**: OMR sheet image (JPEG/PNG)
    - **apply_perspective**: Apply perspective correction (default: false)
    """
    # Validate file type
    if not file.content_type in ["image/jpeg", "image/jpg", "image/png"]:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Only JPEG/PNG images are allowed"
            }
        )
    
    # Validate file size (max 10MB)
    file_size = 0
    try:
        image_bytes = await file.read()
        file_size = len(image_bytes)
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "File size too large. Maximum 10MB allowed"
                }
            )
        
        if file_size == 0:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Empty file"
                }
            )
        
        # Process the image
        result = processor.process_image(image_bytes, apply_perspective)
        
        if result["success"]:
            return JSONResponse(content=result, status_code=200)
        else:
            return JSONResponse(content=result, status_code=400)
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Server error: {str(e)}"
            }
        )

@app.post("/process-batch")
async def process_batch(
    files: List[UploadFile] = File(...),
    apply_perspective: bool = False
):
    """
    Process multiple OMR sheets in batch
    
    - **files**: List of OMR sheet images
    - **apply_perspective**: Apply perspective correction (default: false)
    """
    results = []
    
    for file in files:
        try:
            # Validate file type
            if not file.content_type in ["image/jpeg", "image/jpg", "image/png"]:
                results.append({
                    "success": False,
                    "filename": file.filename,
                    "error": "Invalid file type. Only JPEG/PNG allowed"
                })
                continue
            
            # Process image
            image_bytes = await file.read()
            result = processor.process_image(image_bytes, apply_perspective)
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
    Process and grade an OMR sheet
    
    - **student_id**: Student ID
    - **exam_id**: Exam ID
    - **file**: OMR sheet image
    - **answer_key**: JSON string of answer key
    """
    try:
        # Process the image
        image_bytes = await file.read()
        result = processor.process_image(image_bytes)
        
        if not result["success"]:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": result["error"]}
            )
        
        # If answer key provided, grade the exam
        if answer_key:
            import json
            key = json.loads(answer_key)
            grading_result = processor.grade_exam(result["answers"], key)
            
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
    """Get current OMR configuration"""
    from app.config import OMRConfig
    
    return {
        "student_id": OMRConfig.STUDENT_ID,
        "answers": OMRConfig.ANSWERS,
        "thresholds": OMRConfig.THRESHOLDS,
        "grading": OMRConfig.GRADING
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )

