export default function Loader() {
  return (
    <div className="loader-container">
      <div className="loader-content">
        <div className="pulse-ring">
          <div className="pulse-core"></div>
        </div>
        <div className="loader-text">
          <h3>Processing your meeting</h3>
          <p>Transcribing audio and generating summary...</p>
          <p className="loader-hint">This may take a minute depending on the audio length</p>
        </div>
      </div>
    </div>
  );
}
