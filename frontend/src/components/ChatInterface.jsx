import { useState } from "react";
import SourceDrawer from "./SourceDrawer.jsx";

export default function ChatInterface({ apiBase, activeDoc }) {
  const [messages, setMessages] = useState([]); // { role, content, sources?, showSources? }
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || !activeDoc || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${apiBase}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, doc_id: activeDoc.doc_id }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to get an answer.");
      }

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer, sources: data.sources, showSources: false },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${err.message}`, sources: [] },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const toggleSources = (index) => {
    setMessages((prev) =>
      prev.map((m, i) => (i === index ? { ...m, showSources: !m.showSources } : m))
    );
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleSend();
  };

  return (
    <>
      <div className="chat-header">
        <strong>{activeDoc ? activeDoc.filename : "No document selected"}</strong>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-state">
            {activeDoc
              ? "Ask a question about this document to get started."
              : "Upload a document on the left to begin."}
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            {m.content}
            {m.role === "assistant" && m.sources && m.sources.length > 0 && (
              <div>
                <button className="sources-toggle" onClick={() => toggleSources(i)}>
                  {m.showSources ? "Hide sources" : `View sources (${m.sources.length})`}
                </button>
                {m.showSources && <SourceDrawer sources={m.sources} />}
              </div>
            )}
          </div>
        ))}

        {loading && <div className="message assistant loading">Thinking...</div>}
      </div>

      <div className="chat-input-bar">
        <input
          type="text"
          placeholder={activeDoc ? "Ask a question about this document..." : "Upload a document first"}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!activeDoc || loading}
        />
        <button onClick={handleSend} disabled={!activeDoc || loading || !input.trim()}>
          Send
        </button>
      </div>
    </>
  );
}
