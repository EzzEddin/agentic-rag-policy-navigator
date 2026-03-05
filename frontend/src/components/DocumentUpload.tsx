import { useState, useRef } from "react";
import { Upload, Link, X, CheckCircle, AlertCircle, Loader2, FileText, Search } from "lucide-react";
import { indexUrl, uploadDocument, searchIndex } from "../api/client";
import type { SearchResult } from "../api/client";

interface DocumentUploadProps {
  onClose: () => void;
}

type UploadStatus = "idle" | "loading" | "success" | "error";

export const DocumentUpload = ({ onClose }: DocumentUploadProps) => {
  const [tab, setTab] = useState<"file" | "url" | "search">("file");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Search tab state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");

  const handleFile = async (file: File) => {
    setStatus("loading");
    setStatusMsg("");
    try {
      const res = await uploadDocument(file, description || undefined);
      setStatus("success");
      setStatusMsg(res.message);
    } catch (err: unknown) {
      setStatus("error");
      setStatusMsg(
        err instanceof Error ? err.message : "Upload failed. Please try again."
      );
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearchLoading(true);
    setSearchError("");
    setSearchResults([]);
    try {
      const res = await searchIndex(searchQuery.trim(), 5);
      setSearchResults(res.results);
      if (res.results.length === 0) setSearchError("No matching documents found.");
    } catch (err: unknown) {
      setSearchError(err instanceof Error ? err.message : "Search failed.");
    } finally {
      setSearchLoading(false);
    }
  };

  const handleUrlSubmit = async () => {
    if (!url.trim()) return;
    setStatus("loading");
    setStatusMsg("");
    try {
      const res = await indexUrl({ url: url.trim(), description: description || undefined });
      setStatus("success");
      setStatusMsg(res.message);
    } catch (err: unknown) {
      setStatus("error");
      setStatusMsg(
        err instanceof Error ? err.message : "Failed to index URL."
      );
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Add Policy Documents</h3>
          <button className="modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="modal-tabs">
          <button
            className={`tab-btn ${tab === "file" ? "tab-btn-active" : ""}`}
            onClick={() => setTab("file")}
          >
            <FileText size={14} /> File Upload
          </button>
          <button
            className={`tab-btn ${tab === "url" ? "tab-btn-active" : ""}`}
            onClick={() => setTab("url")}
          >
            <Link size={14} /> Index URL
          </button>
          <button
            className={`tab-btn ${tab === "search" ? "tab-btn-active" : ""}`}
            onClick={() => setTab("search")}
          >
            <Search size={14} /> Search Index
          </button>
        </div>

        <div className="modal-body">
          {/* Description field (shared) */}
          <div className="form-group">
            <label className="form-label">Description (optional)</label>
            <input
              className="form-input"
              type="text"
              placeholder="e.g. EPA Clean Air Regulations 2024"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          {tab === "file" ? (
            <div
              className={`drop-zone ${dragging ? "drop-zone-active" : ""}`}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload size={28} className="drop-icon" />
              <p className="drop-text">
                Drop a file here or <span className="drop-link">browse</span>
              </p>
              <p className="drop-hint">PDF, TXT, MD, or CSV · Max 10 MB</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.txt,.md,.csv"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFile(f);
                }}
              />
            </div>
          ) : (
            <div className="form-group">
              <label className="form-label">Public URL</label>
              <input
                className="form-input"
                type="url"
                placeholder="https://www.epa.gov/laws-regulations/..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
              <button
                className="btn-primary"
                onClick={handleUrlSubmit}
                disabled={status === "loading" || !url.trim()}
              >
                {status === "loading" ? (
                  <><Loader2 size={15} className="spin" /> Indexing…</>
                ) : (
                  <><Link size={15} /> Index URL</>
                )}
              </button>
            </div>
          )}

          {tab === "search" && (
            <div className="form-group">
              <label className="form-label">Search the policy index</label>
              <div className="input-row">
                <input
                  className="form-input"
                  type="text"
                  placeholder="e.g. HIPAA compliance requirements"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
                <button
                  className="send-btn"
                  onClick={handleSearch}
                  disabled={searchLoading || !searchQuery.trim()}
                  aria-label="Search"
                >
                  {searchLoading ? <Loader2 size={16} className="spin" /> : <Search size={16} />}
                </button>
              </div>

              {searchError && (
                <div className="status-banner status-error">
                  <AlertCircle size={14} /> {searchError}
                </div>
              )}

              {searchResults.length > 0 && (
                <div className="search-results">
                  {searchResults.map((r, i) => (
                    <div key={r.id} className="search-result-item">
                      <div className="search-result-header">
                        <span className="search-result-rank">#{i + 1}</span>
                        <span className="search-result-score">
                          score: {r.score.toFixed(3)}
                        </span>
                      </div>
                      <p className="search-result-text">{r.text.slice(0, 200)}…</p>
                      <p className="search-result-id">{r.id}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Status feedback */}
          {status === "loading" && tab === "file" && (
            <div className="status-banner status-loading">
              <Loader2 size={16} className="spin" /> Uploading and indexing…
            </div>
          )}
          {status === "success" && (
            <div className="status-banner status-success">
              <CheckCircle size={16} /> {statusMsg}
            </div>
          )}
          {status === "error" && (
            <div className="status-banner status-error">
              <AlertCircle size={16} /> {statusMsg}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
