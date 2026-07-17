"""
All request/response schemas for the API, defined with Pydantic.
Keeping these separate from route logic makes the API contract easy
to read and easy to reuse (e.g. for auto-generated OpenAPI docs).
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    doc_id: str = Field(..., description="Unique id assigned to the uploaded document")
    filename: str
    chunks_created: int
    message: str = "Document processed and indexed successfully."


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The user's question")
    doc_id: str = Field(..., description="Which uploaded document to search within")


class SourceChunk(BaseModel):
    filename: str
    page_number: Optional[int] = Field(
        None, description="1-indexed page number, if the source format has pages (PDF)"
    )
    chunk_index: int
    text_snippet: str


class AnswerResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    chunks_created: int


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]


class ErrorResponse(BaseModel):
    detail: str
