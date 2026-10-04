# app.py
"""FastAPI web server for the AI Resume Parser.

Endpoints
---------
GET  /              → Serve the main HTML UI
POST /analyze       → Accept JD text + resume files, return match results as JSON

Run locally:
    uvicorn app:app --reload --port 8000
"""

import json
import os
import sys
import tempfile
import shutil
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

from jd_parser import parse_job_description
from matcher import match_resume
from models import JobDescription, Resume
from resume_parser import read_resume

# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Resume Parser",
    description="Parse JDs and match resumes using Groq LLM",
    version="1.0.0",
)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured on server.")
    return Groq(api_key=api_key)


def _fallback_parse(jd_text: str) -> JobDescription:
    """Heuristic fallback when LLM JSON validation fails."""
    lines = jd_text.splitlines()
    role = lines[0].strip() if lines else "Unknown Role"
    required_skills: list[str] = []
    capture = False
    for line in lines:
        low = line.strip().lower()
        if low.startswith("required skills") or low.startswith("required skill"):
            capture = True
            continue
        if capture:
            stripped = line.strip()
            if stripped.startswith("-"):
                skill = stripped.lstrip("- ").split(",")[0].strip()
                required_skills.append(skill)
            elif stripped:
                break
    return JobDescription(role=role, required_skills=required_skills)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(
    jd_text: str = Form(..., description="Raw job description text"),
    resumes: List[UploadFile] = File(..., description="PDF or DOCX resume files"),
):
    """Parse the JD with the LLM, then match each uploaded resume."""

    # 1. Parse JD ----------------------------------------------------------
    client = _get_groq_client()
    try:
        job: JobDescription = parse_job_description(jd_text, client=client, max_tokens=2000)
    except Exception as exc:
        # Graceful fallback
        job = _fallback_parse(jd_text)

    # 2. Process each uploaded resume  ------------------------------------
    results = []
    tmp_dir = tempfile.mkdtemp()
    try:
        for upload in resumes:
            # Save to temp file
            suffix = os.path.splitext(upload.filename or "resume")[-1].lower()
            if suffix not in (".pdf", ".docx"):
                continue  # skip unsupported formats silently

            tmp_path = os.path.join(tmp_dir, upload.filename or f"resume{suffix}")
            with open(tmp_path, "wb") as f:
                shutil.copyfileobj(upload.file, f)

            text = read_resume(tmp_path)
            if text is None:
                results.append({
                    "resume_name": upload.filename,
                    "score": 0.0,
                    "matched_skills": [],
                    "error": "Could not extract text from file.",
                })
                continue

            resume_model = Resume(filename=upload.filename or "resume", raw_text=text)
            match = match_resume(job, resume_model)
            results.append(match.model_dump())
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Sort by score descending
    results.sort(key=lambda r: r.get("score", 0), reverse=True)

    return JSONResponse(content={
        "job": {
            "role": job.role,
            "required_skills": job.required_skills or [],
            "preferred_skills": job.preferred_skills or [],
        },
        "results": results,
    })
