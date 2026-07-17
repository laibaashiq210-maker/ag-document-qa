import { useState } from "react";
import UploadPanel from "./components/UploadPanel.jsx";
import ChatInterface from "./components/ChatInterface.jsx";

const API_BASE = "http://localhost:8000";

export default function App() {
  // List of uploaded documents: { doc_id, filename, chunks_created }
  const [documents, setDocuments] = useState([]);
  const [activeDocId, setActiveDocId] = useState(null);

  const handleUploaded = (doc) => {
    setDocuments((prev) => [...prev, doc]);
    setActiveDocId(doc.doc_id);
  };

  const activeDoc = documents.find((d) => d.doc_id === activeDocId) || null;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <h1 className="app-title">RAG Document Q&A</h1>
          <p className="app-subtitle">Upload a document, then ask questions about it.</p>
        </div>

        <UploadPanel apiBase={API_BASE} onUploaded={handleUploaded} />

        <div className="doc-list">
          {documents.map((doc) => (
            <div
              key={doc.doc_id}
              className={`doc-item ${doc.doc_id === activeDocId ? "active" : ""}`}
              onClick={() => setActiveDocId(doc.doc_id)}
            >
              {doc.filename}
              <div className="doc-meta">{doc.chunks_created} chunks indexed</div>
            </div>
          ))}
        </div>
      </aside>

      <main className="main-panel">
        <ChatInterface apiBase={API_BASE} activeDoc={activeDoc} />
      </main>
    </div>
  );
}
