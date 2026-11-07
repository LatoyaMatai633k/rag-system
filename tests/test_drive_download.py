import pytest

from app.services import drive_download
from app.services.drive_download import extract_google_drive_file_id, validate_pdf_bytes
from app.services.exceptions import DownloadError, InvalidPDFError


def test_extracts_file_id_from_sharing_link():
    assert extract_google_drive_file_id("https://drive.google.com/file/d/abc_123-XYZ/view?usp=sharing") == "abc_123-XYZ"


def test_extracts_file_id_from_query_link():
    assert extract_google_drive_file_id("https://drive.google.com/uc?id=abc123&export=download") == "abc123"


def test_rejects_non_drive_url():
    with pytest.raises(DownloadError):
        extract_google_drive_file_id("https://example.com/file.pdf")


def test_accepts_pdf_signature():
    validate_pdf_bytes(b"%PDF-1.7\nexample", "application/pdf")


def test_rejects_html_instead_of_pdf():
    with pytest.raises(InvalidPDFError, match="HTML"):
        validate_pdf_bytes(b"<!doctype html><html>Drive sign in</html>", "text/html")


def test_rejects_empty_file():
    with pytest.raises(InvalidPDFError, match="empty"):
        validate_pdf_bytes(b"")


def test_download_writes_only_validated_pdf(tmp_path, monkeypatch):
    class Response:
        content = b"%PDF-1.7\nvalid"
        headers = {"Content-Type": "application/pdf"}
        cookies = {}

        def raise_for_status(self):
            pass

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def get(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr(drive_download.requests, "Session", Session)
    destination = tmp_path / "source.pdf"
    result = drive_download.download_google_drive_pdf(
        "https://drive.google.com/file/d/abc123/view", destination
    )
    assert result == destination
    assert destination.read_bytes().startswith(b"%PDF-")
