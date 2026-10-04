# models.py
"""Data models for the resume screening system.

Defines the Pydantic schemas that represent structured data used
throughout the project.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class JobDescription(BaseModel):
    """Schema for a job description.

    All fields are optional to accommodate the variability of real
    job postings. Missing information will be ``None``.
    """

    role: Optional[str] = Field(
        default=None,
        description="Title of the position, e.g., 'Software Development Engineer I'.",
    )
    required_skills: Optional[List[str]] = Field(
        default=None, description="List of required skills."
    )
    preferred_skills: Optional[List[str]] = Field(
        default=None, description="List of preferred/nice‑to‑have skills."
    )
    minimum_experience: Optional[str] = Field(
        default=None, description="Minimum years of experience or textual description."
    )
    educational_requirements: Optional[str] = Field(
        default=None, description="Degree or education level required."
    )
    responsibilities: Optional[List[str]] = Field(
        default=None, description="Key responsibilities for the role."
    )

    class Config:
        # Allows the LLM to use either field names or aliases without error.
        populate_by_name = True

class Resume(BaseModel):
    """Simple model representing a resume.

    For now we only store the raw text extracted from a PDF/DOCX file.
    Additional fields (name, skills, experience, etc.) can be added later.
    """
    filename: str = Field(..., description="Original filename of the resume file.")
    raw_text: str = Field(..., description="Full plain‑text content of the resume.")

class MatchResult(BaseModel):
    """Result of matching a resume against a job description.

    - `resume_name`: the filename of the resume.
    - `score`: a float between 0 and 1 indicating how many required skills were found.
    - `matched_skills`: list of required skills that appear in the resume text.
    """
    resume_name: str = Field(..., description="Filename of the evaluated resume.")
    score: float = Field(..., ge=0.0, le=1.0, description="Match score (0‑1).")
    matched_skills: List[str] = Field(default_factory=list, description="Required skills found in the resume.")
