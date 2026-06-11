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
    # Strip leading/trailing whitespace
    filename = filename.strip()

    # Replace spaces with underscores
    filename = filename.replace(" ", "_")

    # Remove any character that is not alphanumeric, dash, underscore, or dot
    filename = re.sub(r"[^\w\-.]", "", filename)

    # Collapse multiple dots to prevent path traversal like ../../
    filename = re.sub(r"\.{2,}", ".", filename)

    return filename


def ensure_directories(*paths: Path) -> None:
    """
    Create directories if they do not already exist.

    Args:
        *paths: One or more Path objects to create.
    """
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)