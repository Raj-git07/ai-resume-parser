# resume_parser.py
"""Simple utilities to extract plain text from PDF and DOCX resumes.

We deliberately avoid OCR – the functions rely on `pdfminer.six` for PDFs
and `python-docx` for DOCX files. The public `read_resume` function
examines the file extension and delegates to the appropriate helper.

Each function returns a single string containing the full text of the
resume. If the file type is not supported we return `None`.
"""

import os
from typing import Optional

# PDF handling ---------------------------------------------------------------
from pdfminer.high_level import extract_text as _pdf_extract_text


def read_pdf(file_path: str) -> Optional[str]:
    """Extract text from a PDF file.

    Parameters
    ----------
    file_path: str
        Path to the PDF file.

    Returns
    -------
    Optional[str]
        The extracted text, or ``None`` if extraction fails.
    """
    if not os.path.isfile(file_path):
        return None
    try:
        text = _pdf_extract_text(file_path)
        return text.strip() if text else None
    except Exception:
        return None

# DOCX handling --------------------------------------------------------------
from docx import Document as _DocxDocument


def read_docx(file_path: str) -> Optional[str]:
    """Extract text from a DOCX file.

    Parameters
    ----------
    file_path: str
        Path to the DOCX file.

    Returns
    -------
    Optional[str]
        The extracted text, or ``None`` on failure.
    """
    if not os.path.isfile(file_path):
        return None
    try:
        doc = _DocxDocument(file_path)
        full_text = [para.text for para in doc.paragraphs]
        return "\n".join(full_text).strip() if full_text else None
    except Exception:
        return None


def read_resume(file_path: str) -> Optional[str]:
    """Read a resume file (PDF or DOCX) and return its plain‑text content.

    The function determines the format from the file extension (case‑
    insensitive).  Unsupported extensions return ``None``.
    """
    _, ext = os.path.splitext(file_path.lower())
    if ext == ".pdf":
        return read_pdf(file_path)
    if ext == ".docx":
        return read_docx(file_path)
    return None
