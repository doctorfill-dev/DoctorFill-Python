"""
RAG Processor - Main orchestrator for retrieval-augmented generation.

Handles document indexing, retrieval, reranking, and LLM question answering.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from tqdm import tqdm

from ..config.settings import (
    RAG_CHUNK_SIZE,
    RAG_CHUNK_OVERLAP,
    RAG_RETRIEVAL_TOP_K,
    RAG_USE_RERANKING,
    RAG_MAX_INPUT_TOKENS,
    RAG_BATCH_SIZE,
)
from ..llm.provider import BaseLLMProvider, get_provider
from ..llm.response_parser import parse_rag_response
from .chunker import chunk_documents
from .context_builder import build_context, count_tokens

logger = logging.getLogger(__name__)

# Optional ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None


@dataclass
class RAGConfig:
    """Configuration for RAG processing."""
    # Chunking
    chunk_size: int = RAG_CHUNK_SIZE
    chunk_overlap: int = RAG_CHUNK_OVERLAP

    # Retrieval
    retrieval_top_k: int = RAG_RETRIEVAL_TOP_K
    use_reranking: bool = RAG_USE_RERANKING

    # Context window
    max_input_tokens: int = RAG_MAX_INPUT_TOKENS

    # LLM
    temperature: float = 0.1
    max_response_tokens: int = 2000
    batch_size: int = RAG_BATCH_SIZE


@dataclass
class RAGResponse:
    """Response for a single field from RAG."""
    id: str
    value: Optional[str] = None
    source_quote: Optional[str] = None
    confidence: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "value": self.value,
            "source_quote": self.source_quote,
            "confidence": self.confidence,
            "error": self.error
        }


class RAGProcessor:
    """
    RAG processor for extracting field values from context documents.

    Uses the LLM provider abstraction for embeddings, reranking, and chat.
    """

    SYSTEM_PROMPT = """Tu es un assistant expert en extraction de données médicales.

INSTRUCTIONS :
1. Analyse le contexte fourni ci-dessous.
2. Renvoie un JSON contenant une liste sous la clé "fields".
3. Pour chaque question reçue, crée un objet avec :
   - "id": L'identifiant fourni dans la question.
   - "value": La réponse extraite précise (null si introuvable).
   - "source_quote": La phrase exacte du texte qui justifie la réponse (null si introuvable).
   - "confidence": Un score de 0.0 à 1.0 indiquant la certitude de la réponse.
4. Si une liste est demandée (ex: médicaments), inclus tous les éléments.
5. Pour les checkboxes (type boolean), réponds "oui" ou "non".
6. Pour les dates, utilise le format JJ.MM.AAAA si possible.

FORMAT DE RÉPONSE ATTENDU (JSON uniquement) :
{
  "fields": [
    { "id": "X.Y", "value": "Réponse...", "source_quote": "Citation...", "confidence": 0.95 }
  ]
}
"""

    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        provider: Optional[BaseLLMProvider] = None
    ):
        """
        Initialize RAG processor.

        Args:
            config: RAG configuration
            provider: LLM provider (uses default if not specified)
        """
        self.config = config or RAGConfig()
        self.provider = provider or get_provider()

        # Storage
        self._chunks: List[str] = []
        self._embeddings: List[List[float]] = []
        self._collection = None

    def index_documents(
        self,
        documents: List[Union[str, Path]],
        progress: bool = True
    ) -> int:
        """
        Index documents for retrieval.

        Args:
            documents: List of file paths or raw text strings
            progress: Show progress bar

        Returns:
            Number of chunks indexed
        """
        logger.info("Loading documents...")

        # Load document contents
        raw_texts = []
        for doc in documents:
            if isinstance(doc, Path):
                raw_texts.append(doc.read_text(encoding='utf-8'))
                continue

            if isinstance(doc, str):
                # Heuristic: strings with newlines are treated as raw text, not paths.
                if "\n" in doc or "\r" in doc:
                    raw_texts.append(doc)
                    continue
                try:
                    path = Path(doc)
                    if path.exists():
                        raw_texts.append(path.read_text(encoding='utf-8'))
                        continue
                except OSError:
                    # Very long strings can raise "File name too long" when treated as a path.
                    pass

            raw_texts.append(str(doc))

        # Chunk documents
        self._chunks = chunk_documents(
            raw_texts,
            chunk_size=self.config.chunk_size,
            overlap=self.config.chunk_overlap
        )

        if not self._chunks:
            raise ValueError("No chunks generated from documents")

        logger.info("Chunking complete: %d segments", len(self._chunks))

        # Generate embeddings
        logger.info("Generating embeddings...")
        self._embeddings = self._generate_embeddings(self._chunks, progress)

        # Create vector store
        self._create_vector_store()

        logger.info("Indexing complete: %d chunks", len(self._chunks))
        return len(self._chunks)

    def process_questions(
        self,
        questions: List[Dict[str, str]],
        progress: bool = True
    ) -> List[RAGResponse]:
        """
        Process questions against indexed documents.

        Args:
            questions: List of {"id": "...", "question": "..."} dicts
            progress: Show progress bar

        Returns:
            List of RAGResponse objects
        """
        if not self._chunks:
            raise RuntimeError("No documents indexed. Call index_documents() first.")

        responses = []
        batches = list(self._chunk_list(questions, self.config.batch_size))

        iterator = tqdm(batches, unit="batch", desc="Processing") if progress else batches

        for batch in iterator:
            batch_responses = self._process_batch(batch)
            responses.extend(batch_responses)

        return responses

    def _generate_embeddings(
        self,
        texts: List[str],
        progress: bool = True
    ) -> List[List[float]]:
        """Generate embeddings for texts in batches."""
        embeddings = []
        batch_size = 20  # Embed in batches

        iterator = range(0, len(texts), batch_size)
        if progress:
            iterator = tqdm(list(iterator), desc="Embeddings", unit="batch")

        for i in iterator:
            batch = texts[i:i + batch_size]
            # Clean texts for embedding
            cleaned = [t.replace("\n", " ") for t in batch]
            batch_embeddings = self.provider.embed_texts(cleaned)
            embeddings.extend(batch_embeddings)

        return embeddings

    def _create_vector_store(self):
        """Create vector store (ChromaDB or fallback)."""
        if CHROMADB_AVAILABLE:
            chroma_client = chromadb.Client(Settings(anonymized_telemetry=False))
            self._collection = chroma_client.create_collection(
                name=f"rag_collection_{uuid.uuid4().hex[:8]}"
            )
            ids = [str(uuid.uuid4()) for _ in self._chunks]
            self._collection.add(
                documents=self._chunks,
                embeddings=self._embeddings,
                ids=ids
            )
            logger.info("Vector store created (ChromaDB)")
        else:
            # Using in-memory store (embeddings already stored)
            logger.info("Vector store created (in-memory)")

    def _query_similar(
        self,
        query_embedding: List[float],
        top_k: int
    ) -> List[str]:
        """Query for similar documents."""
        if self._collection:
            # ChromaDB
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            return results['documents'][0]
        else:
            # In-memory cosine similarity
            scores = []
            for emb in self._embeddings:
                score = self._cosine_similarity(query_embedding, emb)
                scores.append(score)

            indexed = list(enumerate(scores))
            indexed.sort(key=lambda x: x[1], reverse=True)

            return [self._chunks[idx] for idx, _ in indexed[:top_k]]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _process_batch(self, batch: List[Dict[str, str]]) -> List[RAGResponse]:
        """Process a batch of questions."""
        # Multi-query retrieval
        candidate_docs = set()

        for q in batch:
            try:
                q_embedding = self.provider.embed_texts([q['question'].replace("\n", " ")])[0]
                results = self._query_similar(q_embedding, self.config.retrieval_top_k)
                candidate_docs.update(results)
            except Exception as e:
                logger.warning("Retrieval error for '%s': %s", q['id'], e)

        if not candidate_docs:
            return [RAGResponse(id=q['id'], error="No context found") for q in batch]

        unique_docs = list(candidate_docs)

        # Reranking
        if self.config.use_reranking and len(unique_docs) > 1:
            combined_questions = " ".join([q['question'] for q in batch])
            try:
                reranked = self.provider.rerank(combined_questions, unique_docs, top_k=len(unique_docs))
                scored_docs = [(r['document'], r['score']) for r in reranked]
            except Exception as e:
                logger.warning("Reranking failed: %s. Using original order.", e)
                scored_docs = [(doc, 1.0) for doc in unique_docs]
        else:
            scored_docs = [(doc, 1.0) for doc in unique_docs]

        # Build context within token limit
        context = build_context(scored_docs, max_tokens=self.config.max_input_tokens)

        # Call LLM
        try:
            result = self._call_llm(batch, context)
            return self._parse_response(result, batch)
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return [RAGResponse(id=q['id'], error=str(e)) for q in batch]

    def _call_llm(self, batch: List[Dict], context: str) -> str:
        """Call LLM with questions and context."""
        fields_prompt = [{"id": q['id'], "question": q['question']} for q in batch]

        user_prompt = f"""
CONTEXTE DOCUMENTAIRE :
\"\"\"
{context}
\"\"\"

QUESTIONS À TRAITER :
{json.dumps(fields_prompt, indent=2, ensure_ascii=False)}

Renvoie uniquement le JSON valide.
"""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        return self.provider.chat_completion(
            messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_response_tokens
        )

    def _parse_response(
        self,
        content: str,
        batch: List[Dict]
    ) -> List[RAGResponse]:
        """Parse LLM response into RAGResponse objects."""
        fields = parse_rag_response(content)

        responses = []
        batch_ids = {q['id'] for q in batch}

        for field_data in fields:
            field_id = field_data.get("id")
            if field_id in batch_ids:
                responses.append(RAGResponse(
                    id=field_id,
                    value=field_data.get("value"),
                    source_quote=field_data.get("source_quote"),
                    confidence=field_data.get("confidence", 0.8 if field_data.get("value") else 0.0)
                ))
                batch_ids.discard(field_id)

        # Add missing fields
        for missing_id in batch_ids:
            responses.append(RAGResponse(id=missing_id, error="Not in LLM response"))

        return responses

    @staticmethod
    def _chunk_list(lst: List, n: int):
        """Yield successive n-sized chunks from list."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]
