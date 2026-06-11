"""
app/ingestion/ingest.py
-----------------------
Handles PDF ingestion for SmartDocs AI:
  - Saves the uploaded PDF to data/uploads/
  - Extracts text from every page using PyMuPDF (fitz)
  - Saves extracted text to data/processed/<filename>.txt
  - Returns extraction metadata (pages, character count)
"""

from pathlib import Path
from dataclasses import dataclass

import fitz  # PyMuPDF

from app.services.utils import sanitize_filename, ensure_directories


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
    destination = UPLOADS_DIR / safe_name

    destination.write_bytes(file_bytes)
    return destination


def extract_text_from_pdf(pdf_path: Path) -> tuple[str, int]:
    """
    Open a PDF with PyMuPDF and extract text from every page.

    Args:
        pdf_path: Path to the PDF file on disk.

    Returns:
        A tuple of (full_text, page_count).

    Raises:
        ValueError: If the file cannot be opened as a valid PDF.
    """
    try:
        document = fitz.open(str(pdf_path))
    except Exception as exc:
        raise ValueError(f"Unable to open PDF '{pdf_path.name}': {exc}") from exc

    page_texts: list[str] = []

    for page_number in range(len(document)):
        page = document.load_page(page_number)
        # get_text("text") returns plain text; preserves newlines within a page
        page_text = page.get_text("text")
        page_texts.append(page_text)

    document.close()

    full_text = "\n".join(page_texts)
    return full_text, len(page_texts)


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
    # Replace the PDF extension (or whatever it has) with .txt
    stem = Path(safe_name).stem
    txt_filename = f"{stem}.txt"
    destination = PROCESSED_DIR / txt_filename

    destination.write_text(text, encoding="utf-8")
    return destination


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
    # Step 1 — persist raw PDF
    pdf_path = save_pdf(file_bytes, original_filename)

    # Step 2 — extract text
    full_text, page_count = extract_text_from_pdf(pdf_path)

    # Step 3 — persist extracted text
    txt_path = save_extracted_text(full_text, original_filename)

    return IngestionResult(
        filename=original_filename,
        pages=page_count,
        characters=len(full_text),
        processed_file=txt_path.name,
    )