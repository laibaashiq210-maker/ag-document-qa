"""
Step 6 of the RAG pipeline: AUGMENTATION and GENERATION.

Augmentation: stuff the retrieved chunks into a prompt template as context,
each one labeled with its source so the model can (and must) ground its
answer only in that context and reference the sources it actually used.

Generation: send that prompt to a free Groq-hosted LLM via LangChain's
ChatGroq wrapper and get back a natural-language answer.

Retrieval technique used: Maximal Marginal Relevance (MMR). A candidate
pool is first fetched by cosine similarity (restricted to the target
doc_id), then re-ranked by MMR so the final top_k chunks are both
relevant to the question and non-redundant with each other. See
vector_store.py for the implementation.
"""
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import settings
from app.services.vector_store import query_chunks

SYSTEM_PROMPT = """You are a helpful assistant that answers questions using ONLY the \
provided document excerpts. Rules:
- Base your answer strictly on the excerpts given below. Do not use outside knowledge.
- If the excerpts don't contain enough information to answer, say so clearly.
- Be concise and direct.
- Do not mention "excerpt numbers" or the retrieval process in your answer — just answer \
naturally as if you'd read the document."""


def _build_context(matches):
    blocks = []
    for i, m in enumerate(matches):
        page = m["metadata"].get("page_number", -1)
        page_str = f", page {page}" if page and page != -1 else ""
        blocks.append(f"[Excerpt {i + 1} from {m['metadata']['filename']}{page_str}]\n{m['text']}")
    return "\n\n".join(blocks)


def answer_question(doc_id: str, question: str, top_k: int = None):
    top_k = top_k or settings.top_k
    matches = query_chunks(doc_id=doc_id, question=question, top_k=top_k)

    if not matches:
        return {
            "answer": "I couldn't find any relevant content in this document to answer that question.",
            "sources": [],
        }

    context = _build_context(matches)

    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=f"Document excerpts:\n\n{context}\n\nQuestion: {question}\n\nAnswer:"
        ),
    ]

    response = llm.invoke(messages)

    sources = []
    for m in matches:
        page = m["metadata"].get("page_number", -1)
        sources.append(
            {
                "filename": m["metadata"]["filename"],
                "page_number": None if page == -1 else page,
                "chunk_index": m["metadata"]["chunk_index"],
                "text_snippet": m["text"][:300] + ("..." if len(m["text"]) > 300 else ""),
            }
        )

    return {"answer": response.content, "sources": sources}
