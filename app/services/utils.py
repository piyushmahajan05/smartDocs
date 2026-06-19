"""
app/services/utils.py
---------------------
Reusable helper utilities for SmartDocs AI.
"""

import re
from pathlib import Path


def sanitize_filename(filename: str) -> str:
    """
    Remove or replace characters that are unsafe for filesystem paths.

    Args:
        filename: Original filename from the upload.

    Returns:
        A sanitized filename safe for use on disk.
    """
    # Keep only the terminal path component, then normalize whitespace.
    filename = Path(filename).name.strip()

    # Replace spaces with underscores
    filename = filename.replace(" ", "_")

    # Remove any character that is not alphanumeric, dash, underscore, or dot
    filename = re.sub(r"[^\w\-.]", "", filename)

    # Collapse multiple dots to prevent path traversal like ../../
    filename = re.sub(r"\.{2,}", ".", filename)

    # Remove leading/trailing punctuation that can create hidden or invalid names.
    filename = filename.strip("._-")

    return filename


def unique_path(directory: Path, filename: str) -> Path:
    """
    Build a non-overwriting path inside a directory.

    If the requested filename already exists, append an incrementing suffix
    before the extension: `file.pdf` -> `file_1.pdf` -> `file_2.pdf`.
    """
    directory.mkdir(parents=True, exist_ok=True)

    candidate = directory / filename
    if not candidate.exists():
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    index = 1

    while True:
        candidate = directory / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def _candidate_name(filename: str, index: int) -> str:
    if index == 0:
        return filename

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    return f"{stem}_{index}{suffix}"


def write_unique_bytes(directory: Path, filename: str, data: bytes) -> Path:
    """
    Write bytes to a unique file path inside a directory without overwriting.

    Uses exclusive creation so two concurrent writers cannot pick the same path.
    """
    directory.mkdir(parents=True, exist_ok=True)

    index = 0
    while True:
        candidate = directory / _candidate_name(filename, index)
        try:
            with candidate.open("xb") as handle:
                handle.write(data)
            return candidate
        except FileExistsError:
            index += 1
        except Exception:
            if candidate.exists():
                candidate.unlink(missing_ok=True)
            raise


def write_unique_text(directory: Path, filename: str, text: str) -> Path:
    """
    Write text to a unique file path inside a directory without overwriting.
    """
    directory.mkdir(parents=True, exist_ok=True)

    index = 0
    while True:
        candidate = directory / _candidate_name(filename, index)
        try:
            with candidate.open("x", encoding="utf-8") as handle:
                handle.write(text)
            return candidate
        except FileExistsError:
            index += 1
        except Exception:
            if candidate.exists():
                candidate.unlink(missing_ok=True)
            raise


def ensure_directories(*paths: Path) -> None:
    """
    Create directories if they do not already exist.

    Args:
        *paths: One or more Path objects to create.
    """
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
