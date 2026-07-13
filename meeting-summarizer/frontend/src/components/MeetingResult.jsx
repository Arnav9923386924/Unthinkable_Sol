import { useState } from "react";
import ActionItems from "./ActionItems";

export default function MeetingResult({ meeting }) {
  const [activeTab, setActiveTab] = useState("summary");

  return (
    <div className="result-container">
      <div className="result-header">
        <div className="result-title">
          <h2>📋 Meeting Analysis</h2>
          <span className="filename-badge">{meeting.filename}</span>
        </div>
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
            <div className="transcript-text">
              {meeting.transcript}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
