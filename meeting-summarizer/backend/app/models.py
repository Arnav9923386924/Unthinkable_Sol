from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# --- Response Models ---

class ActionItem(BaseModel):
    """A single action item extracted from the meeting."""
    task: str
    owner: str = "Unassigned"
    deadline: str = "Not specified"
    priority: str = "medium"  # high, medium, or low


class MeetingSummary(BaseModel):
    """Structured summary output from the LLM."""
    meeting_type: str = "general"
    summary: str
    decisions: list[str]
    action_items: list[ActionItem]


class MeetingResponse(BaseModel):
    """Full meeting record returned to the frontend."""
    id: str
    filename: str
    transcript: str
    meeting_type: str = "general"
    summary: str
    decisions: list[str]
    action_items: list[ActionItem]
    created_at: str
    audio_duration: Optional[float] = None
    processing_time: Optional[float] = None
    segments: Optional[list[dict]] = None


class MeetingListItem(BaseModel):
    """Abbreviated meeting info for list views."""
    id: str
    filename: str
    summary: str
    created_at: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
