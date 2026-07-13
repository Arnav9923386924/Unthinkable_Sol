import json
import requests
import logging
from app.config import settings
from app.models import MeetingSummary, ActionItem

logger = logging.getLogger(__name__)

# =============================================================================
# LLM SUMMARIZATION PROMPT
# =============================================================================
# This prompt is designed to extract structured meeting insights from a transcript.
# It instructs the LLM to return valid JSON with three fields:
#   - summary: A concise 2-3 sentence overview
#   - decisions: Array of key decisions made
#   - action_items: Array of objects with task/owner/deadline
#
# The prompt explicitly tells the LLM to:
#   1. Only extract information present in the transcript (no hallucination)
#   2. Use "Unassigned" and "Not specified" as defaults for missing fields
#   3. Return empty arrays if no decisions/action items are found
#   4. Keep outputs concise and actionable
# =============================================================================

SUMMARIZATION_PROMPT = """You are a professional meeting analyst. Your job is to analyze meeting transcripts and extract structured, actionable information.

Given the following meeting transcript, extract:

1. **Summary**: A concise 2-3 sentence overview of what the meeting was about and its key outcomes.
2. **Key Decisions**: Important decisions that were agreed upon during the meeting.
3. **Action Items**: Specific tasks that were assigned or agreed upon, with the responsible person and deadline if mentioned.

Return your response as **valid JSON only** (no markdown, no code fences, no explanation) with this exact structure:
{
  "summary": "A concise 2-3 sentence overview of the meeting",
  "decisions": [
    "Decision 1 description",
    "Decision 2 description"
  ],
  "action_items": [
    {
      "task": "Clear description of the task to be done",
      "owner": "Person responsible (use 'Unassigned' if not mentioned)",
      "deadline": "Due date or timeframe (use 'Not specified' if not mentioned)"
    }
  ]
}

Important rules:
- Extract ONLY information explicitly stated or strongly implied in the transcript.
- Do NOT invent names, dates, or tasks that are not present in the text.
- Keep decision descriptions concise — one sentence each.
- For action items, be specific about what needs to be done.
- If no clear decisions were made, return an empty "decisions" array.
- If no clear action items exist, return an empty "action_items" array.
- Respond with valid JSON only. No additional text before or after the JSON.

TRANSCRIPT:
{transcript}"""


async def summarize_transcript(transcript: str) -> MeetingSummary:
    """
    Send the transcript to a local Ollama LLM to generate a structured summary.

    Uses Ollama's OpenAI-compatible API endpoint at /v1/chat/completions.

    Args:
        transcript: The meeting transcript text.

    Returns:
        MeetingSummary with summary, decisions, and action_items.
    """
    prompt = SUMMARIZATION_PROMPT.replace("{transcript}", transcript)

    # Call Ollama via its OpenAI-compatible endpoint
    raw_content = _call_ollama(
        messages=[
            {"role": "system", "content": "You are a meeting analysis assistant. Always respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    logger.info(f"LLM response (first 200 chars): {raw_content[:200]}")

    # Try to parse the LLM response as JSON
    parsed = _parse_llm_response(raw_content)
    if parsed is not None:
        return parsed

    # Retry once if first attempt fails to parse
    logger.warning("First LLM response was not valid JSON, retrying...")
    retry_content = _call_ollama(
        messages=[
            {"role": "system", "content": "You are a meeting analysis assistant. Respond ONLY with valid JSON."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": raw_content},
            {"role": "user", "content": "Your previous response was not valid JSON. Please respond with ONLY the JSON object, no markdown formatting or extra text."}
        ],
        temperature=0.1,
    )

    parsed = _parse_llm_response(retry_content)
    if parsed is not None:
        return parsed

    # Fallback: return the raw text as the summary with empty structured fields
    logger.warning("LLM retry also failed, using fallback")
    return MeetingSummary(
        summary=raw_content[:500] if raw_content else "Could not generate summary.",
        decisions=[],
        action_items=[]
    )


def _call_ollama(messages: list, temperature: float = 0.3) -> str:
    """
    Make a REST call to Ollama's OpenAI-compatible chat completions endpoint.

    Ollama runs locally — no API key needed, no rate limits.
    """
    response = requests.post(
        url=f"{settings.ollama_base_url}/chat/completions",
        headers={"Content-Type": "application/json"},
        json={
            "model": settings.ollama_model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        },
        timeout=120,  # Ollama can be slow on first load
    )

    if response.status_code != 200:
        error_msg = response.text[:300]
        raise RuntimeError(f"Ollama API error (HTTP {response.status_code}): {error_msg}")

    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
        return content.strip() if content else ""
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected Ollama response: {json.dumps(data)[:300]}")
        raise RuntimeError(f"Unexpected response from Ollama: {str(e)}")


def _parse_llm_response(content: str) -> MeetingSummary | None:
    """
    Attempt to parse the LLM response string into a MeetingSummary.

    Handles cases where the LLM wraps JSON in markdown code fences.
    Returns None if parsing fails.
    """
    if not content:
        return None

    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines)

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning(f"JSON parse failed for: {content[:200]}")
        return None

    # Validate and build structured response
    try:
        action_items = []
        for item in data.get("action_items", []):
            if isinstance(item, dict):
                action_items.append(ActionItem(
                    task=item.get("task", ""),
                    owner=item.get("owner", "Unassigned"),
                    deadline=item.get("deadline", "Not specified")
                ))

        return MeetingSummary(
            summary=data.get("summary", ""),
            decisions=data.get("decisions", []),
            action_items=action_items
        )
    except Exception as e:
        logger.warning(f"Failed to build MeetingSummary: {e}")
        return None
