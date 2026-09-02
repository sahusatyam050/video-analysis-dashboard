from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from database import Base, engine

# Helper to support SQLite fallback (SQLite doesn't have JSONB)
# In production with Postgres, JSONB is significantly faster and more powerful.
def get_json_type():
    if engine.name == 'postgresql':
        return JSONB
    return JSON

JSON_TYPE = get_json_type()

class VideoTask(Base):
    __tablename__ = "video_tasks"

    # Table 1: Core video tracking
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    original_filename = Column(String, nullable=False)
    video_length_seconds = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending, processing, completed, error
    progress = Column(Float, nullable=False, default=0.0)
    processing_time_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    complaint_id = Column(String, index=True, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships to Table 2 and Table 3
    analysis_summary = relationship("AnalysisSummary", back_populates="task", uselist=False, cascade="all, delete-orphan")
    video_segments = relationship("VideoSegment", back_populates="task", cascade="all, delete-orphan")


class AnalysisSummary(Base):
    __tablename__ = "analysis_summaries"

    # Table 2: High-level insights
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    task_id = Column(Integer, ForeignKey("video_tasks.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    final_verdict_report_txt = Column(Text, nullable=True)
    betting_segment_scores = Column(JSON_TYPE, nullable=True)
    crypto_betting_attribution = Column(JSON_TYPE, nullable=True)
    metadata_json = Column(JSON_TYPE, nullable=True)

    # Back-reference to the task
    task = relationship("VideoTask", back_populates="analysis_summary")


class VideoSegment(Base):
    __tablename__ = "video_segments"

    # Table 3: Granular segment data
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    task_id = Column(Integer, ForeignKey("video_tasks.id", ondelete="CASCADE"), nullable=False)
    
    segment_index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    
    qr_detected = Column(Boolean, nullable=False, default=False)
    banking_context = Column(Float, nullable=False, default=0.0)
    crypto_context = Column(Float, nullable=False, default=0.0)
    transaction_likely = Column(Float, nullable=False, default=0.0)
    
    proof_frame_path = Column(String, nullable=True)
    ai_summary = Column(Text, nullable=True)

    # Back-reference to the task
    task = relationship("VideoTask", back_populates="video_segments")
