"""FastAPI interface for Ask Yaya and local RAG administration."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.schemas import APIResponse, DriveIngestRequest, IngestResponse, QuestionRequest, Source
from app.services.drive_download import download_google_drive_pdf
from app.services.exceptions import DownloadError, IngestionError, NotIndexedError, ProviderError
from app.services.rag_service import RAGService

settings = get_settings()
service = RAGService(settings)

app = FastAPI(title="Ask Yaya RAG API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(HTTPException)
async def structured_http_error(_, exc: HTTPException) -> JSONResponse:
    """Keep all expected API failures in the documented response envelope."""
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


@app.exception_handler(RequestValidationError)
async def structured_validation_error(_, exc: RequestValidationError) -> JSONResponse:
    """Return bad client input in the same documented JSON shape."""
    first_error = exc.errors()[0]
    message = first_error.get("msg", "Invalid request")
    return JSONResponse(
        status_code=422,
        content={"success": False, "answer": None, "sources": [], "error": f"Invalid request: {message}"},
    )


def api_error(status_code: int, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "answer": None, "sources": [], "error": message},
    )


@app.get("/health")
def health() -> dict[str, bool]:
    return {"success": True, "indexed": bool(service.nodes)}


@app.post("/documents/from-drive", response_model=IngestResponse)
def ingest_from_drive(payload: DriveIngestRequest) -> IngestResponse:
    try:
        path = settings.data_dir / "source.pdf"
        downloaded = download_google_drive_pdf(str(payload.drive_url), path)
        result = service.ingest_pdf(downloaded)
        return IngestResponse(success=True, **result.__dict__)
    except (DownloadError, IngestionError, ProviderError) as exc:
        raise api_error(422, str(exc)) from exc


@app.post("/chat", response_model=APIResponse)
def chat(payload: QuestionRequest) -> APIResponse:
    try:
        answer, source_data = service.answer(payload.question)
        return APIResponse(success=True, answer=answer, sources=[Source(**source) for source in source_data])
    except NotIndexedError as exc:
        raise api_error(409, str(exc)) from exc
    except ProviderError as exc:
        raise api_error(502, str(exc)) from exc
    except ValueError as exc:
        raise api_error(422, str(exc)) from exc
