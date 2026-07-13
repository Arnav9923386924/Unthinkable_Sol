# Meeting Summarizer

A web application that transcribes meeting audio files and generates structured, action-oriented summaries with key decisions and action items.

## Architecture

```
┌──────────────┐     ┌──────────────────────────────────────────┐
│   React UI   │────▶│           FastAPI Backend                │
│  (Vite dev)  │◀────│                                          │
│  :5173       │     │  POST /api/meetings/upload               │
└──────────────┘     │    ├─ Validate file (type, size)         │
                     │    ├─ Transcribe → OpenAI Whisper API    │
                     │    ├─ Summarize  → OpenRouter LLM API   │
                     │    └─ Store      → SQLite                │
                     │                                          │
                     │  GET /api/meetings       (list all)      │
                     │  GET /api/meetings/:id   (get one)       │
                     │  GET /api/health         (health check)  │
                     │  :8000                                   │
                     └──────────────────────────────────────────┘
```

**Stack:** React + FastAPI + OpenAI Whisper (transcription) + OpenRouter (LLM summarization) + SQLite

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- **OpenAI API key** — for Whisper audio transcription
- **OpenRouter API key** — for LLM-powered summarization ([openrouter.ai](https://openrouter.ai))

## Setup & Run

### 1. Clone and configure environment

```bash
cd meeting-summarizer

# Create .env file from template
cp .env.example backend/.env

# Edit backend/.env and add your API keys:
# OPENAI_API_KEY=sk-your-key
# OPENROUTER_API_KEY=sk-or-your-key
```

### 2. Start the backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. You can check it with:
```bash
curl http://localhost:8000/api/health
```

### 3. Start the frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Open `http://localhost:5173` in your browser.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ | OpenAI API key for Whisper transcription |
| `OPENROUTER_API_KEY` | ✅ | OpenRouter API key for LLM summarization |
| `OPENROUTER_MODEL` | ❌ | LLM model to use (default: `openai/gpt-4o-mini`) |

You can use any model available on OpenRouter by changing `OPENROUTER_MODEL`. Examples:
- `anthropic/claude-3.5-sonnet`
- `google/gemini-pro`
- `meta-llama/llama-3-70b-instruct`

## How It Works

1. **Upload** — User uploads a meeting audio file (MP3, WAV, M4A, WebM, OGG; max 25MB)
2. **Transcribe** — Backend sends the audio to OpenAI's Whisper API for speech-to-text
3. **Summarize** — The transcript is sent to an LLM via OpenRouter with a structured prompt that extracts:
   - A concise meeting summary
   - Key decisions made
   - Action items with task, owner, and deadline fields
4. **Store** — Results are persisted in a local SQLite database
5. **Display** — Frontend shows the transcript, summary, and action items in a tabbed interface

## LLM Prompt

The summarization prompt is located in [`backend/app/services/summarization.py`](backend/app/services/summarization.py) and is clearly commented. It instructs the LLM to return structured JSON with:

```json
{
  "summary": "2-3 sentence overview",
  "decisions": ["Decision 1", "Decision 2"],
  "action_items": [
    {
      "task": "What needs to be done",
      "owner": "Who is responsible",
      "deadline": "When it's due"
    }
  ]
}
```

The prompt includes rules to prevent hallucination (only extract what's in the transcript) and uses low temperature (0.3) for consistent output. If JSON parsing fails, it retries once before falling back gracefully.

## Error Handling

| Scenario | Response |
|----------|----------|
| Unsupported file type | 400 — lists accepted formats |
| File too large (>25MB) | 413 — shows size limit |
| Empty/silent audio | 422 — explains the issue |
| Whisper API failure | 502 — "Transcription service unavailable" |
| LLM API failure | 502 — "Summarization service unavailable" |
| Missing API key | 500 — "API key not configured" (no key leaked) |
| Invalid LLM JSON output | Auto-retry, then graceful fallback |

## Project Structure

```
meeting-summarizer/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Settings from environment variables
│   │   ├── models.py            # Pydantic schemas
│   │   ├── database.py          # SQLite CRUD operations
│   │   ├── routes/
│   │   │   └── meetings.py      # API endpoints
│   │   └── services/
│   │       ├── transcription.py # OpenAI Whisper integration
│   │       └── summarization.py # OpenRouter LLM integration + prompt
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main application component
│   │   ├── index.css            # Global styles
│   │   ├── components/
│   │   │   ├── FileUpload.jsx   # Audio file upload with drag-and-drop
│   │   │   ├── MeetingResult.jsx# Tabbed results display
│   │   │   ├── ActionItems.jsx  # Structured action items table
│   │   │   ├── MeetingHistory.jsx# Past meetings list
│   │   │   └── Loader.jsx       # Processing animation
│   │   └── api/
│   │       └── client.js        # Backend API client
│   └── package.json
├── .env.example                 # Environment variable template
└── README.md                    # This file
```
