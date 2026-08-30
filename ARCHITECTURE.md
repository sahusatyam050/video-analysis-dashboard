# Video Evidence Promotion & Regulatory Tracking System
## System Architecture & Run Guide

This document outlines the decoupled, microservice-style architecture of the Video Analysis System and provides instructions on how to start the entire stack.

---

## 1. High-Level Architecture

The system is broken down into three distinct, decoupled layers:

1. **The Data Layer:** A PostgreSQL database running in a Docker container to ensure data persistence, concurrent task tracking, and structured reporting.
2. **The Processing Engine (Backend):** A FastAPI REST application that handles HTTP requests, serves video files, and orchestrates heavy, asynchronous computer vision and OCR tasks without blocking the UI.
3. **The Presentation Layer (Frontend):** 
   - *Current:* A highly customized Streamlit dashboard serving forensic evidence and PDF generation.
   - *Future:* A Next.js (React) enterprise dashboard.

### Architecture Diagram

```mermaid
graph TD
    %% Define Nodes
    User([End User])
    UI_Streamlit["Streamlit Dashboard<br/>(Port 8501)"]
    UI_NextJS["Next.js Frontend<br/>(Port 3000)"]
    API["FastAPI Backend<br/>(Port 8000)"]
    CV["CV & OCR Engine<br/>(extractframes.py)"]
    DB[(PostgreSQL Database<br/>Port 5432)]
    FS[/"File System<br/>(uploads/, outputs/)"/]

    %% Interactions
    User -->|Uploads Video / Views Reports| UI_Streamlit
    User -.-|Future Interface| UI_NextJS
    
    UI_Streamlit -->|HTTP POST /analyze| API
    UI_Streamlit -->|HTTP GET /progress| API
    UI_Streamlit -->|HTTP GET /verdicts| API
    
    API -->|Saves Video| FS
    API -->|Triggers Async Task| CV
    
    CV -->|Reads Video & Writes Annotated Frames| FS
    CV -->|Writes Task Progress (0-100%)| DB
    CV -->|Saves Segments & Verdicts| DB
    
    API -->|Reads Progress & Verdicts| DB
```

---

## 2. Core Components

### 🗄️ Database (`models.py`, `database.py`, `docker-compose.yml`)
- Tracks `VideoTask` (ID, status, progress percentage).
- Tracks `Segment` (Start/End times, proof frames, raw OCR text).
- Tracks `Verdict` (Classification scores: Banking, Crypto, Gambling, etc.).

### ⚙️ Processing Engine (`api.py`, `extractframes.py`)
- **FastAPI (`api.py`):** Acts as the bridge. It accepts videos, kicks off the analysis in the background, and exposes endpoints so the UI can constantly check the progress without freezing.
- **Extraction Engine (`extractframes.py`):** The heavy lifter. Uses OpenCV to capture frames, PyTesseract to extract coordinate-aware text, and draws color-coded bounding boxes around regulatory keywords (Financial, Gaming, Authentication).

### 🖥️ Frontend (`dashboard.py` / `frontend/`)
- Takes the JSON responses from FastAPI and renders them into beautiful KPI cards, interactive horizontal bar charts, and the robust Segment Explorer (featuring synced video playback and PDF report generation).

---

## 3. How to Run the System

Because the system is decoupled, you must start the layers independently. Open three separate terminal windows in the root of your project directory (`/home/satyam/softwares/video-analysis-dashboard`).

### Terminal 1: Start the Database (Data Layer)
*Ensure Docker is running on your machine.*
```bash
# Start the PostgreSQL database in the background
docker-compose up -d

# (Optional: If this is your first time ever running it, initialize the tables)
python init_db.py
```

### Terminal 2: Start the FastAPI Backend (Processing Engine)
*Ensure your Python virtual environment is activated.*
```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Start the API server on port 8000
uvicorn api:app --reload
```
*You can view the API documentation at `http://localhost:8000/docs`*

### Terminal 3: Start the Frontend (Presentation Layer)
*Ensure your Python virtual environment is activated.*
```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Start the Streamlit Dashboard on port 8501
streamlit run dashboard.py
```
*You can view the Dashboard at `http://localhost:8501`*

---

*(Optional) To view the Next.js React frontend layout we started building:*
```bash
cd frontend
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
npm run dev
```
*Accessible at `http://localhost:3000`*
