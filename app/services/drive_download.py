"""Safe Google Drive PDF download and validation utilities."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

from app.services.exceptions import DownloadError, InvalidPDFError

PDF_MAGIC = b"%PDF-"
HTML_PREFIXES = (b"<!doctype html", b"<html", b"<!doc")


def extract_google_drive_file_id(drive_url: str) -> str:
    """Extract a Drive file ID from normal sharing or download links."""
    parsed = urlparse(drive_url.strip())
    if parsed.netloc not in {"drive.google.com", "www.drive.google.com"}:
        raise DownloadError("The document URL must be a Google Drive link.")

    match = re.search(r"/d/([A-Za-z0-9_-]+)", parsed.path)
    if match:
        return match.group(1)
    file_id = parse_qs(parsed.query).get("id", [None])[0]
    if file_id and re.fullmatch(r"[A-Za-z0-9_-]+", file_id):
        return file_id
    raise DownloadError("Could not find a Google Drive file ID in the supplied link.")


def validate_pdf_bytes(content: bytes, content_type: str | None = None) -> None:
    """Reject HTML pages, empty data, and files that are not real PDFs."""
    sample = content.lstrip()[:32].lower()
    if not content:
        raise InvalidPDFError("The downloaded file is empty.")
    if sample.startswith(HTML_PREFIXES) or (content_type and "html" in content_type.lower()):
        raise InvalidPDFError(
            "Google Drive returned an HTML page instead of a PDF. "
            "Check that the file is shared with access and is a PDF."
        )
    if not content.startswith(PDF_MAGIC):
        raise InvalidPDFError(
            "The downloaded file is not a PDF (expected it to start with %PDF-). "
            "Google Drive may require sign-in, confirmation, or different sharing permissions."
        )


def _find_confirm_token(response: requests.Response) -> str | None:
    """Find Drive's virus-scan confirmation token when one is supplied."""
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            return value
    match = re.search(r"confirm=([0-9A-Za-z_-]+)", response.text)
    return match.group(1) if match else None


def download_google_drive_pdf(drive_url: str, save_path: str | Path, timeout: int = 30) -> Path:
    """Download a shared Drive PDF only after confirming its bytes are a PDF.

    A temporary file is used so an invalid HTML page never overwrites a usable PDF.
    """
    file_id = extract_google_drive_file_id(drive_url)
    destination = Path(save_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = "https://drive.google.com/uc"

    try:
        with requests.Session() as session:
            response = session.get(
                url,
                params={"export": "download", "id": file_id},
                timeout=timeout,
                allow_redirects=True,
            )
            response.raise_for_status()
            if not response.content.startswith(PDF_MAGIC):
                confirm = _find_confirm_token(response)
                if confirm:
                    response = session.get(
                        url,
                        params={"export": "download", "id": file_id, "confirm": confirm},
                        timeout=timeout,
                        allow_redirects=True,
                    )
                    response.raise_for_status()
    except requests.RequestException as exc:
        raise DownloadError(f"Unable to download the Google Drive file: {exc}") from exc

    validate_pdf_bytes(response.content, response.headers.get("Content-Type"))
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        temporary.write_bytes(response.content)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
