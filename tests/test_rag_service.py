from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.services.exceptions import NotIndexedError, ProviderError
from app.services.rag_service import RAGService


class FakeResponse:
    source_nodes = []

    def __str__(self):
        return "Grounded answer"


class FakePack:
    def run(self, question):
        assert question == "What does the document say?"
        return FakeResponse()


def test_answer_requires_index():
    service = RAGService(Settings(openrouter_api_key="test"))
    with pytest.raises(NotIndexedError):
        service.answer("Question")


def test_answer_rejects_empty_provider_response():
    service = RAGService(Settings(openrouter_api_key="test"))
    service.nodes = [object()]
    service.query_rewriting_pack = SimpleNamespace(run=lambda _: "Empty Response")
    with pytest.raises(ProviderError, match="empty response"):
        service.answer("Question")


def test_answer_uses_existing_query_fusion_pack():
    service = RAGService(Settings(openrouter_api_key="test"))
    service.nodes = [object()]
    service.query_rewriting_pack = FakePack()
    answer, sources = service.answer("What does the document say?")
    assert answer == "Grounded answer"
    assert sources == []
