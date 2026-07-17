from fastapi import APIRouter, HTTPException

from app.models.schemas import QuestionRequest, AnswerResponse, SourceChunk
from app.services.vector_store import doc_exists
from app.services.rag_pipeline import answer_question

router = APIRouter(tags=["chat"])


@router.post("/ask", response_model=AnswerResponse)
async def ask_question(payload: QuestionRequest):
    if not doc_exists(payload.doc_id):
        raise HTTPException(
            status_code=404,
            detail=f"No document found with doc_id '{payload.doc_id}'. Upload it first.",
        )

    result = answer_question(doc_id=payload.doc_id, question=payload.question)

    return AnswerResponse(
        answer=result["answer"],
        sources=[SourceChunk(**s) for s in result["sources"]],
    )
