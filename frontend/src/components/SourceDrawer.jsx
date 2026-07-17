export default function SourceDrawer({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="source-drawer">
      {sources.map((s, i) => (
        <div className="source-chunk" key={i}>
          <div className="source-chunk-header">
            {s.filename}
            {s.page_number ? ` — page ${s.page_number}` : ""}
          </div>
          <div className="source-chunk-text">{s.text_snippet}</div>
        </div>
      ))}
    </div>
  );
}
