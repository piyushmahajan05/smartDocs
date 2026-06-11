"""
main.py
-------
SmartDocs AI — FastAPI application entry point.
Registers all routes and configures the app instance.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from app.ingestion.ingest import ingest_pdf

app = FastAPI(
    title="SmartDocs AI",
    description="Enterprise-style RAG system — local, no paid APIs.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health_check() -> dict:
    """Confirm the API is running."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Phase 1 — PDF Upload & Text Extraction
# ---------------------------------------------------------------------------

@app.post("/upload", tags=["Ingestion"])
async def upload_pdf(file: UploadFile = File(...)) -> JSONResponse:
    """
    Accept a PDF upload, extract its text, and persist both the raw PDF
    and the extracted .txt file to disk.

    Returns JSON with:
      - filename:       original uploaded filename
      - pages:          total pages in the PDF
      - characters:     total characters extracted
      - processed_file: name of the saved .txt file
    """
    # --- Validate MIME type -------------------------------------------------
    # Browsers may send 'application/pdf' or 'application/octet-stream'.
    # We also check the file extension as a secondary guard.
    content_type = file.content_type or ""
    filename = file.filename or ""

    if not filename.lower().endswith(".pdf") and "pdf" not in content_type.lower():
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Please upload a PDF (.pdf) file.",
        )

    # --- Read file bytes ----------------------------------------------------
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # --- Run ingestion pipeline ---------------------------------------------
    try:
        result = ingest_pdf(file_bytes=file_bytes, original_filename=filename)
    except ValueError as exc:
        # ingest_pdf raises ValueError for corrupt / unreadable PDFs
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Catch-all for unexpected I/O errors
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during ingestion: {exc}",
        ) from exc

    return JSONResponse(
        status_code=200,
        content={
            "filename": result.filename,
            "pages": result.pages,
            "characters": result.characters,
            "processed_file": result.processed_file,
        },
    )