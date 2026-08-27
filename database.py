import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Use environment variable for database URL if available, otherwise default to a local postgres instance
# Format: postgresql://user:password@localhost:5432/dbname
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@localhost:5432/video_analysis_db"
)

# For SQLite fallback during rapid local testing (uncomment if postgres is not yet installed)
# DATABASE_URL = "sqlite:///./video_analysis.db"

# Create the SQLAlchemy engine
# Note: connect_args={"check_same_thread": False} is needed ONLY for SQLite.
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for our models to inherit from
Base = declarative_base()

def get_db():
    """
    Dependency generator to provide a database session for FastAPI routes.
    Ensures the session is closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
