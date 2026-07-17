"""
Step 1 & 2 of the RAG pipeline: LOADING and CHUNKING.

Loading: read raw text out of a PDF or .txt file, keeping track of which
page each piece of text came from (PDFs only — .txt has no pages).

Chunking: split that raw text into overlapping chunks small enough to fit
comfortably into an embedding model's context window and to keep retrieved
context focused. We use LangChain's RecursiveCharacterTextSplitter, which
tries to split on paragraph breaks first, then sentences, then words —
so chunks stay semantically coherent instead of cutting mid-sentence.

Why chunk_size / chunk_overlap matter:
- chunk_size too large -> retrieval pulls in irrelevant text, wastes LLM context.
- chunk_size too small -> loses surrounding context, answers get shallow.
- overlap -> prevents an answer-relevant sentence from being split across
  two chunks with neither half having the full idea.
"""
import os
import uuid
from dataclasses import dataclass
from typing import List, Optional

from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.config import settings


@dataclass
class RawPage:
    text: str
    page_number: Optional[int]  # None for plain text files (no concept of pages)


@dataclass
class Chunk:
    text: str
    page_number: Optional[int]
    chunk_index: int


def load_document(file_path: str, filename: str) -> List[RawPage]:
    """Load a PDF or .txt file into a list of (text, page_number) pairs."""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        reader = PdfReader(file_path)
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(RawPage(text=text, page_number=i + 1))
        return pages

    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return [RawPage(text=text, page_number=None)]

    else:
        raise ValueError(f"Unsupported file type: {ext}. Only .pdf and .txt are supported.")


def chunk_pages(pages: List[RawPage]) -> List[Chunk]:
    """Split loaded pages into overlapping text chunks, preserving page numbers."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: List[Chunk] = []
    idx = 0
    for page in pages:
        pieces = splitter.split_text(page.text)
        for piece in pieces:
            if piece.strip():
                chunks.append(Chunk(text=piece, page_number=page.page_number, chunk_index=idx))
                idx += 1
    return chunks


def generate_doc_id() -> str:
    return uuid.uuid4().hex[:12]
