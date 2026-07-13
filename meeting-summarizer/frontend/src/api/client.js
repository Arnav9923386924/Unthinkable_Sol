const API_BASE = "http://localhost:8000/api";

/**
 * Upload a meeting audio file for transcription and summarization.
 * Returns the full meeting object on success.
 */
export async function uploadMeeting(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/meetings/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch all meetings (list view).
 */
export async function fetchMeetings() {
  const response = await fetch(`${API_BASE}/meetings`);

  if (!response.ok) {
    throw new Error("Failed to fetch meetings");
  }

  return response.json();
}

/**
 * Fetch a single meeting by ID.
 */
export async function fetchMeeting(id) {
  const response = await fetch(`${API_BASE}/meetings/${id}`);

  if (!response.ok) {
    throw new Error("Meeting not found");
  }

  return response.json();
}
