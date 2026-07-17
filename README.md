# RAG Document Q&A App

Upload a PDF or TXT file, ask questions about it in a chat interface, and get
answers grounded in the document with visible source citations (filename +
page number).

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangChain |
| Backend API | FastAPI |
| Validation | Pydantic / pydantic-settings |
| Vector store | ChromaDB (persisted to disk) |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`, local, no API key) |
| LLM | Groq (free API key) |
| Frontend | React + Vite |

## Why LangChain over LlamaIndex

Both frameworks were researched for the orchestration layer:

- **LlamaIndex** is purpose-built around indexing and retrieval. It gives
  very strong defaults for "load documents → build an index → query it"
  out of the box, with less manual wiring.
- **LangChain** is a more general orchestration framework: it treats
  document loading, splitting, embedding, vector stores, and LLM calls as
  interchangeable, composable pieces (loaders, splitters, chains).

For this project, LangChain was chosen because:
1. The spec explicitly asks us to design and justify each pipeline step
   ourselves (chunking strategy, retrieval technique, prompt construction)
   rather than rely on a framework's opinionated defaults — LangChain's
   modularity fits that better.
2. `langchain-groq` gives a clean, well-documented `ChatGroq` wrapper, and
   `langchain-community` has a ready `PyPDFLoader`/text splitter we use
   directly.
3. LangChain has a larger ecosystem/community for troubleshooting during
   development and viva prep.

LlamaIndex would be the better choice if the goal were to stand up a
retrieval system as fast as possible with minimal custom logic — but here,
understanding and explaining each step was part of the assignment.

## Project Structure

```
rag-app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + CORS + routers
│   │   ├── config.py            # Pydantic settings (reads .env)
│   │   ├── models/schemas.py    # All request/response Pydantic models
│   │   ├── services/
│   │   │   ├── document_processor.py  # Load (PDF/TXT) + chunk
│   │   │   ├── vector_store.py        # Embed + store/query in ChromaDB
│   │   │   └── rag_pipeline.py        # Build prompt + call Groq LLM
│   │   └── routers/
│   │       ├── upload.py        # POST /upload
│   │       └── chat.py          # POST /ask
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── src/
        ├── App.jsx
        └── components/
            ├── UploadPanel.jsx
            ├── ChatInterface.jsx
            └── SourceDrawer.jsx
```

## RAG Pipeline (what happens under the hood)

1. **Load** — `document_processor.py` reads a PDF page-by-page (via `pypdf`)
   or a plain `.txt` file, keeping page numbers for PDFs (needed for source
   citations).
2. **Chunk** — `RecursiveCharacterTextSplitter` splits text into ~1000-char
   chunks with 150-char overlap, trying paragraph → sentence → word breaks
   in that order so chunks stay semantically coherent. Overlap prevents an
   important sentence from being cut in half between two chunks.
3. **Embed** — each chunk is embedded locally with
   `sentence-transformers/all-MiniLM-L6-v2` — small, fast, and runs with no
   external API call or cost.
4. **Store** — embeddings + text + metadata (`doc_id`, `filename`,
   `page_number`, `chunk_index`) are upserted into a ChromaDB collection
   persisted to `./chroma_db`.
5. **Retrieve** — at question time, the question is embedded with the same
   model. We use **Maximal Marginal Relevance (MMR)** for retrieval: first
   Chroma fetches a larger candidate pool (15 chunks) by cosine similarity,
   filtered to the selected `doc_id`; then those candidates are re-ranked
   with MMR, which balances relevance to the question against redundancy
   with chunks already picked. This avoids returning several near-duplicate
   chunks when the answer is spread across different parts of the document,
   and yields the final top-k (default 4) chunks used for generation.
6. **Augment + Generate** — the retrieved chunks are inserted into a prompt
   template as labeled excerpts, and sent to a Groq-hosted LLM
   (`llama-3.1-8b-instant` by default) via `langchain-groq`. The model is
   instructed to answer only from the given excerpts.

## Setup & Run Locally

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

Open `.env` and paste your free Groq API key (get one at
https://console.groq.com/keys):

```
GROQ_API_KEY=your_actual_key_here
```

Run the server:

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be live at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`.

### 2. Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### 3. Use it

1. Upload a `.pdf` or `.txt` file in the left panel.
2. Type a question about the document in the chat box and press Enter.
3. Click "View sources" under any answer to see which chunk(s) — with
   filename and page number — the answer was drawn from.

## Notes

- First run will download the embedding model (~90MB) from HuggingFace —
  this needs internet access once; after that it's cached locally.
- ChromaDB data persists in `backend/chroma_db/` between restarts.
- Uploaded files are stored in `backend/uploaded_docs/`.
