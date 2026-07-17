import { useRef, useState } from "react";

export default function UploadPanel({ apiBase, onUploaded }) {
  const fileInputRef = useRef(null);
  const [status, setStatus] = useState(null); // { type: 'loading'|'success'|'error', message }

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setStatus({ type: "loading", message: `Uploading "${file.name}"...` });

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${apiBase}/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Upload failed.");
      }

      setStatus({
        type: "success",
        message: `"${data.filename}" indexed (${data.chunks_created} chunks).`,
      });
      onUploaded(data);
    } catch (err) {
      setStatus({ type: "error", message: err.message || "Something went wrong." });
    } finally {
      e.target.value = ""; // allow re-uploading the same file name
    }
  };

  return (
    <div>
      <div className="upload-box" onClick={() => fileInputRef.current?.click()}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt"
          onChange={handleFileChange}
        />
        <div style={{ fontSize: 14, fontWeight: 600 }}>Click to upload</div>
        <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>
          PDF or TXT file
        </div>
      </div>

      {status && <div className={`upload-status ${status.type}`}>{status.message}</div>}
    </div>
  );
}
