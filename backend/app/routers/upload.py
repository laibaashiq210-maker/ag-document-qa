import os
import shutil

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import settings
from app.models.schemas import UploadResponse
from app.services.document_processor import load_document, chunk_pages, generate_doc_id
from app.services.vector_store import store_chunks

router = APIRouter(tags=["upload"])

ALLOWED_EXTENSIONS = {".pdf", ".txt"}


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Only .pdf and .txt are allowed.",
        )

    os.makedirs(settings.upload_dir, exist_ok=True)
    doc_id = generate_doc_id()
    saved_path = os.path.join(settings.upload_dir, f"{doc_id}{ext}")

    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        pages = load_document(saved_path, file.filename)
        chunks = chunk_pages(pages)
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No extractable text found in this document (it may be a scanned/image-only PDF).",
            )
        num_stored = store_chunks(doc_id=doc_id, filename=file.filename, chunks=chunks)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

    return UploadResponse(doc_id=doc_id, filename=file.filename, chunks_created=num_stored)
