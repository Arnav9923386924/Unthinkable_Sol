import { useState, useEffect } from "react";
import FileUpload from "./components/FileUpload";
import MeetingResult from "./components/MeetingResult";
import MeetingHistory from "./components/MeetingHistory";
import Loader from "./components/Loader";
import { fetchMeetings, fetchMeeting } from "./api/client";

function App() {
  const [currentMeeting, setCurrentMeeting] = useState(null);
  const [meetings, setMeetings] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [globalError, setGlobalError] = useState("");

  // Load meeting history on mount
  useEffect(() => {
    loadMeetings();
  }, []);

  const loadMeetings = async () => {
    try {
      const data = await fetchMeetings();
      setMeetings(data);
    } catch {
      // Silently fail — history is non-critical
    }
  };

  const handleUploadStart = () => {
    setIsProcessing(true);
    setGlobalError("");
    setCurrentMeeting(null);
  };

  const handleUploadSuccess = (meeting) => {
    setIsProcessing(false);
    setCurrentMeeting(meeting);
    loadMeetings(); // Refresh history
  };

  const handleUploadError = (errorMsg) => {
    setIsProcessing(false);
    setGlobalError(errorMsg);
  };

  const handleSelectMeeting = async (id) => {
    try {
      const meeting = await fetchMeeting(id);
      setCurrentMeeting(meeting);
      setGlobalError("");
    } catch {
      setGlobalError("Failed to load meeting");
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="logo">
            <div className="logo-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </svg>
            </div>
            <h1>Meeting Summarizer</h1>
          </div>
          <p className="tagline">Upload meeting audio → Get transcript, decisions & action items</p>
        </div>
      </header>

      <main className="app-main">
        <div className="main-content">
          {/* Upload Section */}
          <FileUpload
            onUploadStart={handleUploadStart}
            onUploadSuccess={handleUploadSuccess}
            onUploadError={handleUploadError}
            isProcessing={isProcessing}
          />

          {/* Processing Loader */}
          {isProcessing && <Loader />}

          {/* Global Error */}
          {globalError && !isProcessing && (
            <div className="error-banner">
              <span>❌</span> {globalError}
            </div>
          )}

          {/* Meeting Result */}
          {currentMeeting && !isProcessing && (
            <MeetingResult meeting={currentMeeting} />
          )}

          {/* Meeting History */}
          {!isProcessing && (
            <MeetingHistory meetings={meetings} onSelect={handleSelectMeeting} />
          )}
        </div>
      </main>

      <footer className="app-footer">
        <p>Meeting Summarizer • Powered by OpenAI Whisper + OpenRouter</p>
      </footer>
    </div>
  );
}

export default App;
