import { useState } from "react";
import ActionItems from "./ActionItems";

export default function MeetingResult({ meeting }) {
  const [activeTab, setActiveTab] = useState("summary");
  const [copied, setCopied] = useState(false);

  const formatDuration = (seconds) => {
    if (!seconds) return "";
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  const formatProcessingTime = (seconds) => {
    if (!seconds) return "";
    return `Processed in ${seconds.toFixed(1)}s`;
  };

  const formatSegmentTime = (seconds) => {
    const pad = (num) => String(num).padStart(2, "0");
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hrs > 0) {
      return `${hrs}:${pad(mins)}:${pad(secs)}`;
    }
    return `${mins}:${pad(secs)}`;
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(meeting.summary || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadTranscript = () => {
    const element = document.createElement("a");
    const file = new Blob([meeting.transcript || ""], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `${meeting.filename || "meeting"}_transcript.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="result-container">
      <div className="result-header">
        <div className="result-title">
          <h2>📋 Meeting Analysis</h2>
          <span className="filename-badge">{meeting.filename}</span>
          {meeting.meeting_type && meeting.meeting_type !== "general" && (
            <span className="meeting-type-badge">{meeting.meeting_type}</span>
          )}
        </div>
        
        {(meeting.audio_duration > 0 || meeting.processing_time > 0) && (
          <div className="header-meta">
            {meeting.audio_duration > 0 && (
              <span className="meta-badge duration-badge">
                ⏱️ {formatDuration(meeting.audio_duration)}
              </span>
            )}
            {meeting.processing_time > 0 && (
              <span className="meta-badge speed-badge">
                ⚡ {formatProcessingTime(meeting.processing_time)}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === "summary" ? "active" : ""}`}
          onClick={() => setActiveTab("summary")}
        >
          Summary
        </button>
        <button
          className={`tab ${activeTab === "actions" ? "active" : ""}`}
          onClick={() => setActiveTab("actions")}
        >
          Action Items
          {meeting.action_items?.length > 0 && (
            <span className="tab-count">{meeting.action_items.length}</span>
          )}
        </button>
        <button
          className={`tab ${activeTab === "transcript" ? "active" : ""}`}
          onClick={() => setActiveTab("transcript")}
        >
          Transcript
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === "summary" && (
          <div className="summary-tab">
            <div className="tab-actions-bar">
              <button className="btn-action" onClick={copyToClipboard}>
                {copied ? "✓ Copied" : "📋 Copy Summary"}
              </button>
            </div>

            <div className="summary-section">
              <h3>Overview</h3>
              <p className="summary-text">{meeting.summary || "No summary available."}</p>
            </div>

            {meeting.decisions?.length > 0 && (
              <div className="summary-section">
                <h3>Key Decisions</h3>
                <ul className="decisions-list">
                  {meeting.decisions.map((decision, i) => (
                    <li key={i}>
                      <span className="decision-marker">✓</span>
                      {decision}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {meeting.decisions?.length === 0 && (
              <div className="summary-section">
                <h3>Key Decisions</h3>
                <p className="empty-note">No specific decisions were identified in this meeting.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === "actions" && (
          <ActionItems items={meeting.action_items} />
        )}

        {activeTab === "transcript" && (
          <div className="transcript-tab">
            <div className="tab-actions-bar">
              <button className="btn-action" onClick={downloadTranscript}>
                💾 Download Transcript (.txt)
              </button>
            </div>

            {meeting.segments && meeting.segments.length > 0 ? (
              <div className="transcript-segments">
                {meeting.segments.map((seg, idx) => (
                  <div key={idx} className="transcript-segment-row">
                    <span className="segment-timestamp">
                      {formatSegmentTime(seg.start)} - {formatSegmentTime(seg.end)}
                    </span>
                    <span className="segment-text">{seg.text}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="transcript-text">
                {meeting.transcript}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
