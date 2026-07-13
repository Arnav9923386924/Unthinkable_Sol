import { useState, useRef } from "react";
import { uploadMeeting } from "../api/client";

const ACCEPTED_TYPES = ".mp3,.wav,.m4a,.webm,.ogg,.mp4,.mpeg,.mpga";
const MAX_SIZE_MB = 25;

export default function FileUpload({ onUploadStart, onUploadSuccess, onUploadError, isProcessing }) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  const validateFile = (file) => {
    const ext = "." + file.name.split(".").pop().toLowerCase();
    const allowedExts = ACCEPTED_TYPES.split(",");

    if (!allowedExts.includes(ext)) {
      return `Unsupported file type "${ext}". Accepted: ${ACCEPTED_TYPES}`;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Max: ${MAX_SIZE_MB}MB.`;
    }
    return null;
  };

  const handleFile = (file) => {
    setError("");
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = () => setDragActive(false);

  const handleInputChange = (e) => {
    if (e.target.files?.[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleSubmit = async () => {
    if (!selectedFile) return;
    setError("");
    onUploadStart();

    try {
      const result = await uploadMeeting(selectedFile);
      setSelectedFile(null);
      if (inputRef.current) inputRef.current.value = "";
      onUploadSuccess(result);
    } catch (err) {
      setError(err.message);
      onUploadError(err.message);
    }
  };

  return (
    <div className="upload-section">
      <div
        className={`drop-zone ${dragActive ? "drag-active" : ""} ${isProcessing ? "disabled" : ""}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !isProcessing && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          onChange={handleInputChange}
          hidden
          disabled={isProcessing}
        />
        <div className="drop-zone-content">
          <div className="waveform-animation">
            {Array.from({ length: 40 }).map((_, i) => (
              <span
                key={i}
                className="wave-bar"
                style={{
                  animationDelay: `${(i * 0.07) % 1.2}s`,
                  height: `${12 + Math.sin(i * 0.8) * 10 + Math.random() * 8}px`,
                }}
              />
            ))}
          </div>
          <p className="drop-zone-text">
            {dragActive ? "Drop your audio file here" : "Drop meeting audio here"}
          </p>
          <p className="drop-zone-hint">or click to browse — MP3, WAV, M4A, MP4, WEBM, OGG, FLAC (max {MAX_SIZE_MB}MB)</p>
        </div>
      </div>

      {selectedFile && !isProcessing && (
        <div className="selected-file">
          <div className="file-info">
            <span className="file-icon">🎵</span>
            <div>
              <p className="file-name">{selectedFile.name}</p>
              <p className="file-size">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
          </div>
          <button className="upload-btn" onClick={handleSubmit}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 16 12 12 8 16" />
              <line x1="12" y1="12" x2="12" y2="21" />
              <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
            </svg>
            Process Meeting
          </button>
        </div>
      )}

      {error && (
        <div className="error-message">
          <span>⚠️</span> {error}
        </div>
      )}
    </div>
  );
}
