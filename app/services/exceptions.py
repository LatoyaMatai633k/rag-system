"""Exceptions that turn technical failures into useful API responses."""


class RAGError(Exception):
    """Base error for expected RAG pipeline failures."""


class DownloadError(RAGError):
    """A remote document could not be downloaded as a PDF."""


class InvalidPDFError(RAGError):
    """A downloaded or uploaded file is not a usable PDF."""


class IngestionError(RAGError):
    """No readable document content could be extracted."""


class NotIndexedError(RAGError):
    """A question was asked before a valid document was indexed."""


class ProviderError(RAGError):
    """The LLM or embedding provider could not complete its work."""
