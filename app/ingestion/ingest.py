"""
app/ingestion/ingest.py
-----------------------
Handles PDF ingestion for SmartDocs AI:
  - Saves the uploaded PDF to data/uploads/
  - Extracts text from every page using PyMuPDF (fitz)
  - Saves extracted text to data/processed/<filename>.txt
  - Returns extraction metadata (pages, character count)
"""

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from app.services.utils import (
    ensure_directories,
    sanitize_filename,
    write_unique_bytes,
    write_unique_text,
)


# ---------------------------------------------------------------------------
# Directory constants — resolved relative to the project root
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]  # project root (SMARTDOCS/)
UPLOADS_DIR = BASE_DIR / "data" / "uploads"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


@dataclass
class IngestionResult:
    """Structured result returned after a successful PDF ingestion."""
    filename: str          # original uploaded filename
    pages: int             # total pages in the PDF
    characters: int        # total characters extracted across all pages
    processed_file: str    # name of the saved .txt file


def save_pdf(file_bytes: bytes, original_filename: str) -> Path:
    """
    Persist the raw PDF bytes to data/uploads/.

    Args:
        file_bytes:        Raw bytes of the uploaded PDF.
        original_filename: The original name of the uploaded file.

    Returns:
        Path to the saved PDF on disk.
    """
    ensure_directories(UPLOADS_DIR)

    safe_name = sanitize_filename(original_filename)
    if not safe_name:
        raise ValueError("Invalid filename provided for uploaded PDF.")

    return write_unique_bytes(UPLOADS_DIR, safe_name, file_bytes)


def extract_text_from_pdf(pdf_path: Path) -> tuple[str, int, int]:
    """
    Open a PDF with PyMuPDF and extract text from every page.

    Args:
        pdf_path: Path to the PDF file on disk.

    Returns:
        A tuple of (full_text, page_count, character_count).

    Raises:
        ValueError: If the file cannot be opened as a valid PDF.
    """
    try:
        file_bytes = pdf_path.read_bytes()
    except Exception as exc:
        raise ValueError(f"Unable to read PDF '{pdf_path.name}': {exc}") from exc

    return extract_text_from_pdf_bytes(file_bytes=file_bytes, source_name=pdf_path.name)


def extract_text_from_pdf_bytes(file_bytes: bytes, source_name: str) -> tuple[str, int, int]:
    """
    Open a PDF from bytes with PyMuPDF and extract text from every page.

    Args:
        file_bytes: Raw bytes of the PDF document.
        source_name: Human-readable name used in error messages.

    Returns:
        A tuple of (full_text, page_count, character_count).
    """
    try:
        document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Unable to open PDF '{source_name}': {exc}") from exc

    page_texts: list[str] = []

    try:
        for page_number in range(len(document)):
            page = document.load_page(page_number)
            # get_text("text") returns plain text; preserves newlines within a page
            page_text = page.get_text("text")
            page_texts.append(page_text)
    finally:
        document.close()

    full_text = "\n".join(page_texts)
    character_count = sum(len(page_text) for page_text in page_texts)
    return full_text, len(page_texts), character_count


def save_extracted_text(text: str, original_filename: str) -> Path:
    """
    Write extracted plain text to data/processed/<stem>.txt.

    Args:
        text:              The full extracted text string.
        original_filename: Original PDF filename (used to derive .txt name).

    Returns:
        Path to the saved .txt file.
    """
    ensure_directories(PROCESSED_DIR)

    safe_name = sanitize_filename(original_filename)
    if not safe_name:
        raise ValueError("Invalid filename provided for extracted text output.")

    # Replace the PDF extension (or whatever it has) with .txt
    stem = Path(safe_name).stem
    txt_filename = f"{stem}.txt"
    return write_unique_text(PROCESSED_DIR, txt_filename, text)


def ingest_pdf(file_bytes: bytes, original_filename: str) -> IngestionResult:
    """
    Full ingestion pipeline for Phase 1:
      1. Save PDF to data/uploads/
      2. Extract text from all pages
      3. Save extracted text to data/processed/

    Args:
        file_bytes:        Raw bytes of the uploaded file.
        original_filename: Original filename as provided by the HTTP client.

    Returns:
        IngestionResult with filename, page count, character count,
        and the processed .txt filename.

    Raises:
        ValueError: Propagated from extract_text_from_pdf on invalid PDFs.
    """
    pdf_path: Path | None = None
    txt_path: Path | None = None

    # Step 1 — validate and extract from bytes before persisting anything.
    full_text, page_count, character_count = extract_text_from_pdf_bytes(
        file_bytes=file_bytes,
        source_name=original_filename,
    )

    try:
        # Step 2 — persist raw PDF
        pdf_path = save_pdf(file_bytes, original_filename)

        # Step 3 — persist extracted text
        txt_path = save_extracted_text(full_text, original_filename)
    except Exception:
        if txt_path is not None and txt_path.exists():
            txt_path.unlink(missing_ok=True)
        if pdf_path is not None and pdf_path.exists():
            pdf_path.unlink(missing_ok=True)
        raise

    return IngestionResult(
        filename=original_filename,
        pages=page_count,
        characters=character_count,
        processed_file=txt_path.name,
    )
