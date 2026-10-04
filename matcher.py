# matcher.py
"""Utilities to match a Resume against a JobDescription.

Matching strategy (keyword-based):
- Each required skill string is split into meaningful keywords.
- A skill is considered "matched" if ANY of its key terms appears in the
  resume text (case-insensitive).
- The score is the proportion of required skills matched (0–1).

This is more robust than exact-phrase matching and avoids false negatives
caused by paraphrasing or partial descriptions in the JD.
"""

from __future__ import annotations

import re
from typing import List

from models import JobDescription, MatchResult, Resume

# Words that carry no discriminative signal – filtered out before matching.
_STOP_WORDS = {
    "a", "an", "the", "of", "and", "or", "in", "to", "with", "for",
    "on", "at", "by", "is", "are", "be", "as", "such", "ability",
    "understanding", "knowledge", "experience", "familiarity", "good",
    "strong", "basic", "new", "similar", "technologies", "well",
}


def _keywords(phrase: str) -> List[str]:
    """Return meaningful lowercase tokens from a skill phrase.

    We split on whitespace and punctuation, remove stop words, and keep
    tokens that are at least 2 characters long.
    """
    tokens = re.split(r"[\s/,.()\-]+", phrase.lower())
    return [t for t in tokens if len(t) >= 2 and t not in _STOP_WORDS]


def _normalize(text: str) -> str:
    """Lower-case and collapse whitespace."""
    return " ".join(text.lower().split())


def match_resume(job: JobDescription, resume: Resume) -> MatchResult:
    """Match a resume against a job description.

    Parameters
    ----------
    job : JobDescription
        The parsed job description containing a list of ``required_skills``.
    resume : Resume
        The resume model with ``filename`` and ``raw_text``.

    Returns
    -------
    MatchResult
        Contains the filename, a score between 0 and 1, and the list of
        required skills that were found in the resume text.
    """
    required: List[str] | None = job.required_skills
    if not required:
        # No required skills defined – treat as a perfect match.
        return MatchResult(resume_name=resume.filename, score=1.0, matched_skills=[])

    resume_text = _normalize(resume.raw_text)
    matched: List[str] = []

    for skill in required:
        kws = _keywords(skill)
        if not kws:
            continue
        # A skill is matched if at least one of its keywords appears in the resume.
        if any(kw in resume_text for kw in kws):
            matched.append(skill)

    score = len(matched) / len(required) if required else 0.0
    return MatchResult(
        resume_name=resume.filename,
        score=score,
        matched_skills=matched,
    )
