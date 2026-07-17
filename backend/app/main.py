from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import upload, chat

app = FastAPI(
    title="RAG Document Q&A API",
    description="Upload a PDF/TXT document and ask questions about it, with cited sources.",
    version="1.0.0",
)

# Allow the Vite dev server (default port 5173) to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "RAG Document Q&A API is running."}


@app.get("/health")
async def health():
    return {"status": "healthy"}
