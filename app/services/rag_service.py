"""The existing LlamaIndex RAG flow, exposed as a reusable service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.services.exceptions import IngestionError, NotIndexedError, ProviderError


@dataclass
class IngestionResult:
    document_count: int
    chunk_count: int
    source: str


class RAGService:
    """Retains the notebook's LlamaIndex, BGE, semantic splitter and fusion pack."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.nodes: list[Any] = []
        self.query_rewriting_pack: Any | None = None
        self.source: str | None = None

    def _configure_models(self) -> Any:
        if not self.settings.openrouter_api_key:
            raise ProviderError("OPENROUTER_API_KEY is not configured.")
        try:
            from llama_index.core import Settings as LlamaSettings
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            from llama_index.llms.openrouter import OpenRouter

            llm = OpenRouter(
                api_key=self.settings.openrouter_api_key,
                model=self.settings.openrouter_model,
                max_tokens=512,
                temperature=0.1,
                timeout=60,
                system_prompt=(
                    "You are Yaya (Latoya Matai), a junior software developer, answering visitors to your portfolio. "
                    "Speak in first person, warm, confident and conversational. "
                    "Answer ONLY using the provided context and never invent facts. "
                    "If the answer isn't in the context, say you'd rather not guess and suggest reaching out by email or LinkedIn. "
                    "Keep answers to 2 to 5 sentences. No bullet points and no citations."
                ),
            )
            embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
            LlamaSettings.llm = llm
            LlamaSettings.embed_model = embed_model
            return embed_model
        except Exception as exc:
            raise ProviderError(f"Could not configure the RAG models: {exc}") from exc

    def ingest_pdf(self, pdf_path: str | Path) -> IngestionResult:
        """Extract text, create semantic chunks, and populate the fusion vector index."""
        path = Path(pdf_path)
        if not path.is_file() or path.stat().st_size == 0:
            raise IngestionError("The PDF file is missing or empty.")
        if not path.read_bytes()[:5] == b"%PDF-":
            raise IngestionError("The selected file is not a valid PDF.")

        embed_model = self._configure_models()
        try:
            from llama_index.core import SimpleDirectoryReader
            from llama_index.core.llama_pack import download_llama_pack
            from llama_index.core.node_parser import SemanticSplitterNodeParser

            documents = SimpleDirectoryReader(input_files=[str(path)]).load_data()
            if not documents or not any(document.text.strip() for document in documents):
                raise IngestionError("No readable text could be extracted from this PDF.")

            parser = SemanticSplitterNodeParser(
                buffer_size=3,
                breakpoint_percentile_threshold=95,
                embed_model=embed_model,
            )
            nodes = parser.get_nodes_from_documents(documents)
            if not nodes:
                raise IngestionError("The PDF produced zero text chunks; it may be scanned or empty.")
            for node in nodes:
                node.metadata["source"] = str(path)
                node.metadata["chunk_type"] = "semantic"

            pack_type = download_llama_pack("QueryRewritingRetrieverPack", str(self.settings.pack_dir))
            self.query_rewriting_pack = pack_type(
                nodes,
                chunk_size=256,
                vector_similarity_top_k=8,
                fusion_similarity_top_k=8,
                num_queries=6,
            )
            self.nodes = nodes
            self.source = str(path)
            return IngestionResult(len(documents), len(nodes), str(path))
        except IngestionError:
            raise
        except Exception as exc:
            raise IngestionError(f"PDF ingestion failed: {exc}") from exc

    def answer(self, question: str) -> tuple[str, list[dict[str, Any]]]:
        """Run the original query-rewrite and fusion retrieval workflow."""
        if not self.query_rewriting_pack or not self.nodes:
            raise NotIndexedError("No document is indexed. Ingest a valid PDF before asking questions.")
        if not question or not question.strip():
            raise ValueError("Question cannot be empty.")
        try:
            response = self.query_rewriting_pack.run(question.strip())
            answer = str(response).strip()
            if not answer or answer.lower() == "empty response":
                raise ProviderError("The language model returned an empty response.")
            source_nodes = getattr(response, "source_nodes", []) or []
            sources = [
                {
                    "source": item.node.metadata.get("source", self.source),
                    "page": item.node.metadata.get("page_label"),
                    "score": round(float(item.score), 4) if item.score is not None else None,
                }
                for item in source_nodes
            ]
            return answer, sources
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"RAG query failed: {exc}") from exc
