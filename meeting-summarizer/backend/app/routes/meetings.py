import os
import uuid
import tempfile
import time
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import settings
from app.models import MeetingResponse, MeetingListItem, ActionItem
from app.database import save_meeting, get_meeting, get_all_meetings
from app.services.transcription import transcribe_audio
from app.services.summarization import summarize_transcript

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


@router.post("/upload", response_model=MeetingResponse)
async def upload_meeting(file: UploadFile = File(...)):
    """
    Upload a meeting audio file for transcription and summarization.

    Flow: Validate → Save temp file → Transcribe (Whisper) → Summarize (LLM) → Store → Return
    """
    # --- Validate file extension ---
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_ext}'. Accepted formats: {', '.join(sorted(settings.allowed_extensions))}"
        )

    # --- Validate file size ---
    contents = await file.read()
    if len(contents) > settings.max_upload_size:
        max_mb = settings.max_upload_size // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_mb}MB."
        )

    # --- Save to temp file for processing ---
    meeting_id = str(uuid.uuid4())
    temp_path = None
    start_time = time.time()

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            tmp.write(contents)
            temp_path = tmp.name

        # --- Step 1: Transcribe with Whisper ---
        try:
            transcription_res = await transcribe_audio(temp_path)
            transcript = transcription_res["text"]
            segments = transcription_res["segments"]
            audio_duration = transcription_res["duration"]
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Transcription service unavailable: {str(e)}"
            )

        if not transcript or transcript.strip() == "":
            raise HTTPException(
                status_code=422,
                detail="Transcription returned empty. The audio may be silent or unrecognizable."
            )

        # --- Step 2: Summarize with LLM via OpenRouter ---
        try:
            summary_result = await summarize_transcript(transcript)
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Summarization service unavailable: {str(e)}"
            )

        processing_time = time.time() - start_time

        # --- Step 3: Store in SQLite ---
        action_items_dicts = [item.model_dump() for item in summary_result.action_items]
        save_meeting(
            meeting_id=meeting_id,
            filename=file.filename or "unknown",
            transcript=transcript,
            meeting_type=summary_result.meeting_type,
            summary=summary_result.summary,
            decisions=summary_result.decisions,
            action_items=action_items_dicts,
            audio_duration=audio_duration,
            processing_time=processing_time,
            segments=segments
        )

        return MeetingResponse(
            id=meeting_id,
            filename=file.filename or "unknown",
            transcript=transcript,
            meeting_type=summary_result.meeting_type,
            summary=summary_result.summary,
            decisions=summary_result.decisions,
            action_items=summary_result.action_items,
            created_at="just now",
            audio_duration=audio_duration,
            processing_time=processing_time,
            segments=segments
        )

    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting_by_id(meeting_id: str):
    """Retrieve a single meeting by its ID."""
    meeting = get_meeting(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Convert raw action_items dicts back to ActionItem models
    action_items = [ActionItem(**item) for item in meeting["action_items"]]

    return MeetingResponse(
        id=meeting["id"],
        filename=meeting["filename"],
        transcript=meeting["transcript"],
        meeting_type=meeting.get("meeting_type", "general"),
        summary=meeting["summary"],
        decisions=meeting["decisions"],
        action_items=action_items,
        created_at=meeting["created_at"],
        audio_duration=meeting.get("audio_duration", 0.0),
        processing_time=meeting.get("processing_time", 0.0),
        segments=meeting.get("segments", []),
    )


@router.get("", response_model=list[MeetingListItem])
async def list_meetings():
    """List all meetings, most recent first."""
    meetings = get_all_meetings()
    return [
        MeetingListItem(
            id=m["id"],
            filename=m["filename"],
            summary=m["summary"],
            created_at=m["created_at"],
        )
        for m in meetings
    ]
