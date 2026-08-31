import os
import tempfile
import json
import time
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from extractframes import extractFrames
from database import SessionLocal, get_db
from models import VideoTask, AnalysisSummary, VideoSegment
from pydantic import BaseModel
from crawler import crawl_and_record
import shutil
from urllib.parse import urlparse
import asyncio

CRAWLER_STATES = {}  # task_id -> {"status": "running" | "waiting_for_otp", "otp_code": None, "event": asyncio.Event()}

app = FastAPI(title="Video Intel Dashboard API")

# Mount the outputs directory so Streamlit can fetch the images via URL
os.makedirs("outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

def process_video_background(task_id: int, file_path: str):
    """Background task to process the video and store results in DB."""
    db = SessionLocal()
    task = db.query(VideoTask).filter(VideoTask.id == task_id).first()
    if not task:
        db.close()
        return

    start_time_process = time.time()
    
    def update_progress(progress: float):
        task.progress = progress
        db.commit()

    try:
        # Pass the task_id as a string to match folder generation expectations
        extractFrames(
            videoPath=file_path, 
            progress_callback=update_progress, 
            video_name=str(task_id)
        )
        
        # After extraction, read the JSON files and store in the DB
        output_dir = Path(f"outputs/{task_id}")
        
        def load_json_safe(filename):
            try:
                with open(output_dir / filename, "r") as f:
                    return json.load(f)
            except:
                return None
                
        def load_text_safe(filename):
            try:
                with open(output_dir / filename, "r") as f:
                    return f.read()
            except:
                return None

        # Build composite metadata object to store loose files
        metadata_dict = load_json_safe("metadata.json") or {}
        metadata_dict["final_summary"] = load_json_safe("final_summary.json")
        metadata_dict["betting_transaction_attribution"] = load_json_safe("betting_transaction_attribution.json")
        metadata_dict["final_summary_txt"] = load_text_safe("final_summary.txt")
        metadata_dict["betting_evidence"] = load_json_safe("betting_segment_evidence.json")

        segments_data = load_json_safe("segment_verdicts.json") or []
        
        # Aggregate keyword hits across all segments to avoid DB schema changes
        all_banking_hits = set()
        all_crypto_hits = set()
        for seg in segments_data:
            for hit in seg.get("banking_hits", []):
                all_banking_hits.add(hit)
            for hit in seg.get("crypto_hits", []):
                all_crypto_hits.add(hit)
                
        metadata_dict["aggregated_banking_hits"] = list(all_banking_hits)
        metadata_dict["aggregated_crypto_hits"] = list(all_crypto_hits)

        # 1. Create AnalysisSummary
        summary = AnalysisSummary(
            task_id=task_id,
            final_verdict_report_txt=load_text_safe("final_verdict_report.txt"),
            betting_segment_scores=load_json_safe("betting_segment_scores.json"),
            crypto_betting_attribution=load_json_safe("crypto_betting_attribution.json"),
            metadata_json=metadata_dict
        )
        db.add(summary)
        
        # 2. Create VideoSegments
        if segments_data:
            for seg in segments_data:
                db_seg = VideoSegment(
                    task_id=task_id,
                    segment_index=seg.get("segment_index", 0),
                    start_time=seg.get("start_time", 0.0),
                    end_time=seg.get("end_time", 0.0),
                    qr_detected=seg.get("qr_detected", False),
                    banking_context=seg.get("banking_context", 0.0),
                    crypto_context=seg.get("crypto_context", 0.0),
                    transaction_likely=seg.get("transaction_likely", 0.0),
                    proof_frame_path=seg.get("proof_frame", "")
                )
                db.add(db_seg)

        task.status = "complete"
        task.progress = 1.0
        task.completed_at = datetime.now(timezone.utc)
        task.processing_time_seconds = time.time() - start_time_process
        
        db.commit()
    except Exception as e:
        task.status = "error"
        task.error_message = str(e)
        db.commit()
    finally:
        db.close()


@app.post("/analyze")
async def analyze_video(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Uploads a video, creates a DB task, and starts background analysis."""
    # Save uploaded file to the permanent uploads directory immediately
    # We must first create the DB task to get its ID for the filename
    new_task = VideoTask(
        original_filename=file.filename,
        status="processing",
        progress=0.0
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    file_path = f"uploads/{new_task.id}_{file.filename}"
    with open(file_path, 'wb') as f:
        f.write(await file.read())
        
    # Update the DB task with the actual saved filename
    new_task.original_filename = os.path.basename(file_path)
    db.commit()
        
    background_tasks.add_task(process_video_background, new_task.id, file_path)
    
    # Return string task_id to maintain frontend compatibility
    return {"task_id": str(new_task.id)}


class CrawlRequest(BaseModel):
    url: str
    duration: int = 30

@app.post("/crawl")
async def start_crawl_analysis(
    req: CrawlRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """
    Crawls a URL autonomously, records the screen as a video, and processes it.
    """
    parsed_url = urlparse(req.url)
    domain = parsed_url.netloc.replace("www.", "") or "unknown_domain"
    clean_domain = "".join(c for c in domain if c.isalnum() or c in ".-_")
    
    # 1. Create DB Task immediately
    new_task = VideoTask(
        original_filename=f"{clean_domain}.webm",
        status="processing",
        progress=0.0
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Initialize crawler state
    CRAWLER_STATES[new_task.id] = {
        "status": "running",
        "otp_code": None,
        "event": asyncio.Event()
    }

    # 2. Define background sequence
    async def run_crawl_sequence(task_id: int, url: str, duration: int, clean_domain: str):
        async def request_otp_from_user():
            if task_id in CRAWLER_STATES:
                CRAWLER_STATES[task_id]["status"] = "waiting_for_otp"
                await CRAWLER_STATES[task_id]["event"].wait()
                otp = CRAWLER_STATES[task_id]["otp_code"]
                CRAWLER_STATES[task_id]["event"].clear() # Reset for next time if needed
                return otp
            return None

        try:
            # Pass task_id so crawler can update state if needed
            video_path = await crawl_and_record(url, duration=duration, task_id=task_id, otp_callback=request_otp_from_user)
            
            dest_path = f"uploads/{task_id}_{clean_domain}.webm"
            shutil.move(video_path, dest_path)
            
            # Update DB with final filename
            db_session = SessionLocal()
            task = db_session.query(VideoTask).filter(VideoTask.id == task_id).first()
            if task:
                task.original_filename = os.path.basename(dest_path)
                db_session.commit()
            db_session.close()

            # Clean up crawler state
            CRAWLER_STATES.pop(task_id, None)

            # 3. Start Video Processing Background Task
            process_video_background(task_id, dest_path)
            
        except Exception as e:
            db_session = SessionLocal()
            task = db_session.query(VideoTask).filter(VideoTask.id == task_id).first()
            if task:
                task.status = "error"
                task.error_message = f"Crawler failed: {str(e)}"
                db_session.commit()
            db_session.close()
            CRAWLER_STATES.pop(task_id, None)

    # Launch sequence
    background_tasks.add_task(run_crawl_sequence, new_task.id, req.url, req.duration, clean_domain)

    return {"task_id": str(new_task.id), "message": "Crawling started in background"}



@app.get("/status/{task_id}")
def get_status(task_id: str, db: Session = Depends(get_db)):
    """Returns the current progress and status of a task from the database."""
    try:
        task_id_int = int(task_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "Invalid task ID format"})
        
    task = db.query(VideoTask).filter(VideoTask.id == task_id_int).first()
    if not task:
        return JSONResponse(status_code=404, content={"detail": "Task not found"})
        
    crawler_state = CRAWLER_STATES.get(task_id_int, {})
        
    return {
        "status": task.status,
        "crawler_state": crawler_state.get("status"),
        "progress": task.progress,
        "original_filename": task.original_filename,
        "error_message": task.error_message,
        "processing_time_seconds": task.processing_time_seconds
    }

class OTPRequest(BaseModel):
    otp: str

@app.post("/submit_otp/{task_id}")
def submit_otp(task_id: int, req: OTPRequest):
    if task_id in CRAWLER_STATES:
        CRAWLER_STATES[task_id]["otp_code"] = req.otp
        CRAWLER_STATES[task_id]["status"] = "running"
        CRAWLER_STATES[task_id]["event"].set()
        return {"success": True}
    return JSONResponse(status_code=404, content={"detail": "Crawler not waiting for OTP or not found"})


@app.get("/analyses")
def list_analyses(db: Session = Depends(get_db)):
    """Lists all completed analyses from the database."""
    completed_tasks = db.query(VideoTask).filter(VideoTask.status == "complete").all()
    # Return list of string task IDs to match frontend expectation
    return [str(task.id) for task in completed_tasks]


@app.get("/analyses_detailed")
def list_analyses_detailed(db: Session = Depends(get_db)):
    """Lists all analyses with detailed status for the React sidebar."""
    tasks = db.query(VideoTask).order_by(VideoTask.id.desc()).all()
    return [
        {
            "id": str(task.id),
            "video_name": task.original_filename or f"Task {task.id}",
            "status": task.status,
            "progress": task.progress or 0.0
        }
        for task in tasks
    ]


@app.get("/analyses/{task_id}/summary")
def get_analysis_summary(task_id: str, db: Session = Depends(get_db)):
    """Fetches the JSON and text summaries for a specific analysis from PostgreSQL."""
    try:
        task_id_int = int(task_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "Invalid task ID format"})
        
    task = db.query(VideoTask).filter(VideoTask.id == task_id_int).first()
    if not task or task.status != "complete":
        return JSONResponse(status_code=404, content={"detail": "Analysis not found or not completed"})
        
    summary = db.query(AnalysisSummary).filter(AnalysisSummary.task_id == task_id_int).first()
    segments = db.query(VideoSegment).filter(VideoSegment.task_id == task_id_int).order_by(VideoSegment.segment_index).all()
    
    # Reconstruct the expected JSON shape for the Streamlit dashboard
    segment_verdicts = []
    for s in segments:
        segment_verdicts.append({
            "segment_index": s.segment_index,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "qr_detected": s.qr_detected,
            "banking_context": s.banking_context,
            "crypto_context": s.crypto_context,
            "transaction_likely": s.transaction_likely,
            "proof_frame": s.proof_frame_path
        })
        
    meta_dict = summary.metadata_json if summary and summary.metadata_json else {}
        
    return {
        "original_filename": task.original_filename,
        "segment_verdicts": segment_verdicts,
        "final_summary": meta_dict.get("final_summary"),
        "betting_segment_scores": summary.betting_segment_scores if summary else None,
        "betting_transaction_attribution": meta_dict.get("betting_transaction_attribution"),
        "crypto_betting_attribution": summary.crypto_betting_attribution if summary else None,
        "final_summary_txt": meta_dict.get("final_summary_txt", ""),
        "final_verdict_report_txt": summary.final_verdict_report_txt if summary else "",
        "metadata": meta_dict
    }

