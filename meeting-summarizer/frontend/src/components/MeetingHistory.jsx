import { useState } from "react";

export default function MeetingHistory({ meetings, onSelect }) {
  if (!meetings || meetings.length === 0) return null;

  return (
    <div className="history-section">
      <h3 className="history-title">Previous Meetings</h3>
      <div className="history-list">
        {meetings.map((m) => (
          <button key={m.id} className="history-item" onClick={() => onSelect(m.id)}>
            <div className="history-item-header">
              <span className="history-filename">{m.filename}</span>
              <span className="history-date">
                {new Date(m.created_at).toLocaleDateString()}
              </span>
            </div>
            <p className="history-summary">{m.summary?.slice(0, 120)}...</p>
          </button>
        ))}
      </div>
    </div>
  );
}
