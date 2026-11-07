"""Request and response types for the portfolio-facing API."""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class DriveIngestRequest(BaseModel):
    drive_url: HttpUrl


class Source(BaseModel):
    source: str | None
    page: str | None = None
    score: float | None = None


class APIResponse(BaseModel):
    success: bool
    answer: str | None = None
    sources: list[Source] = []
    error: str | None = None


class IngestResponse(BaseModel):
    success: bool
    document_count: int = 0
    chunk_count: int = 0
    source: str | None = None
    error: str | None = None
