"""
Step 3 & 4 of the RAG pipeline: EMBEDDING and STORAGE.

Embedding: turn each text chunk into a numeric vector using a local
sentence-transformers model (all-MiniLM-L6-v2 by default) — this runs
fully on-device, no external API call, no cost, no rate limit.

Storage: persist those vectors (+ their text + metadata) to ChromaDB,
saved to disk so the index survives server restarts.

We tag every chunk with doc_id metadata so that at query time we can
filter search to only the document the user is asking about, instead
of searching across every document ever uploaded.
"""
from typing import List, Optional

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.services.document_processor import Chunk

_embedder: Optional[SentenceTransformer] = None
_chroma_client: Optional[chromadb.PersistentClient] = None
_collection = None


def get_embedder() -> SentenceTransformer:
    """Lazily load the embedding model once and reuse it (it's not tiny)."""
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(settings.embedding_model)
    return _embedder


def get_collection():
    """Lazily create/open the single persistent ChromaDB collection."""
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        _collection = _chroma_client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def store_chunks(doc_id: str, filename: str, chunks: List[Chunk]) -> int:
    """Embed a list of chunks and upsert them into ChromaDB with metadata."""
    if not chunks:
        return 0

    embedder = get_embedder()
    collection = get_collection()

    texts = [c.text for c in chunks]
    embeddings = embedder.encode(texts, show_progress_bar=False).tolist()

    ids = [f"{doc_id}_{c.chunk_index}" for c in chunks]
    metadatas = [
        {
            "doc_id": doc_id,
            "filename": filename,
            "page_number": c.page_number if c.page_number is not None else -1,
            "chunk_index": c.chunk_index,
        }
        for c in chunks
    ]

    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return len(chunks)


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1e-10
    return float(np.dot(a, b) / denom)


def _mmr_select(query_vec: np.ndarray, candidate_vecs: List[np.ndarray], top_k: int, lambda_mult: float = 0.5) -> List[int]:
    """
    Maximal Marginal Relevance selection.

    Plain top-k similarity search can return several chunks that all say
    almost the same thing, wasting the LLM's limited context window on
    redundant text. MMR instead picks chunks one at a time, each time
    balancing two things:
      - relevance: how similar is this candidate to the question?
      - diversity: how different is it from chunks already selected?

    lambda_mult controls the balance (1.0 = pure relevance, 0.0 = pure
    diversity). 0.5 is a common, well-rounded default.

    Returns the indices of the selected candidates, in selection order.
    """
    if not candidate_vecs:
        return []

    n = len(candidate_vecs)
    top_k = min(top_k, n)

    relevance = [_cosine_sim(query_vec, v) for v in candidate_vecs]
    selected: List[int] = []
    remaining = set(range(n))

    while len(selected) < top_k and remaining:
        best_idx = None
        best_score = float("-inf")

        for idx in remaining:
            if not selected:
                diversity_penalty = 0.0
            else:
                diversity_penalty = max(_cosine_sim(candidate_vecs[idx], candidate_vecs[j]) for j in selected)

            mmr_score = lambda_mult * relevance[idx] - (1 - lambda_mult) * diversity_penalty

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        selected.append(best_idx)
        remaining.remove(best_idx)

    return selected


def query_chunks(doc_id: str, question: str, top_k: int, fetch_k: int = 15):
    """
    Step 5 of the pipeline: RETRIEVAL, using MMR.

    Embed the question with the SAME model used for the chunks (required —
    mixing embedding models gives meaningless similarity scores). Then:
      1. Fetch a larger candidate pool (fetch_k) from Chroma by plain
         similarity — this is the "recall" pass.
      2. Re-rank that pool with MMR to pick top_k chunks that are both
         relevant AND non-redundant — this is the "precision + diversity" pass.
    """
    embedder = get_embedder()
    collection = get_collection()

    query_embedding = embedder.encode([question])[0]

    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=fetch_k,
        where={"doc_id": doc_id},
        include=["documents", "metadatas", "embeddings"],
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    embeds = results.get("embeddings", [[]])[0]

    if not docs:
        return []

    candidate_vecs = [np.array(e) for e in embeds]
    selected_indices = _mmr_select(query_embedding, candidate_vecs, top_k=top_k)

    matches = []
    for idx in selected_indices:
        matches.append({"text": docs[idx], "metadata": metas[idx]})
    return matches


def doc_exists(doc_id: str) -> bool:
    collection = get_collection()
    existing = collection.get(where={"doc_id": doc_id}, limit=1)
    return len(existing.get("ids", [])) > 0
