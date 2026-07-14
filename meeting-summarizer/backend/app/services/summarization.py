import json
import requests
import logging
from app.config import settings
from app.models import MeetingSummary, ActionItem

logger = logging.getLogger(__name__)

# =============================================================================
# LLM SUMMARIZATION PROMPT — v2.0
# =============================================================================
# Prompt engineering rationale:
#   1. Role priming: "professional meeting analyst" sets the LLM's persona
#   2. Explicit JSON schema: prevents format drift, especially with smaller models
#   3. Few-shot example: a concrete input→output pair dramatically improves format
#      adherence for local models like llama3:8b that may not follow instructions
#      as reliably as GPT-4
#   4. Anti-hallucination rules: "Extract ONLY information explicitly stated"
#      prevents the LLM from inventing names, dates, or tasks
#   5. Priority classification: adds actionable severity to each action item
#   6. Meeting type detection: helps downstream consumers categorize meetings
#   7. Temperature 0.3: low enough for consistent structured output, high enough
#      to avoid degenerate repetition
#
# Changes from v1.0:
#   - Added few-shot example for better format adherence
#   - Added meeting_type classification field
#   - Added priority (high/medium/low) to action items
#   - Added explicit handling for edge cases (empty transcripts, single-speaker)
# =============================================================================

PROMPT_VERSION = "2.0"

SUMMARIZATION_PROMPT = """You are a professional meeting analyst. Your job is to analyze meeting transcripts and extract structured, actionable information.

Given the following meeting transcript, extract:

1. **Meeting Type**: Classify as one of: "standup", "planning", "review", "brainstorming", "decision-making", "status-update", "retrospective", or "general".
2. **Summary**: An elaborate 5-6 sentence overview of the meeting. It must cover: what was discussed, the flow/order of agenda items, key context behind decisions (not just the decision itself), and any notable discussion points or disagreements. Stay strictly factual to the transcript content, and do not invent any details.
3. **Key Decisions**: Important decisions that were agreed upon during the meeting.
4. **Action Items**: Specific tasks that were assigned or agreed upon, including priority level.

Return your response as **valid JSON only** (no markdown, no code fences, no explanation) with this exact structure:
{
  "meeting_type": "general",
  "summary": "An elaborate 5-6 sentence overview covering topics discussed, flow of agenda, context of decisions, and notable discussion/disagreement points.",
  "decisions": [
    "Decision 1 description",
    "Decision 2 description"
  ],
  "action_items": [
    {
      "task": "Clear description of the task to be done",
      "owner": "Person responsible (use 'Unassigned' if not mentioned)",
      "deadline": "Due date or timeframe (use 'Not specified' if not mentioned)",
      "priority": "high, medium, or low based on urgency and importance"
    }
  ]
}

Here is an example of a correct input and output:

EXAMPLE TRANSCRIPT:
"Alright team, quick standup. Sarah, what's your update? I finished the API integration yesterday and will start writing tests today. John, I'm blocked on the database migration — need DevOps to give me access to staging. Can we get that done by end of day? Sure, I'll ping DevOps right now. Also, reminder — the client demo is Friday, so all feature work needs to be wrapped up by Thursday EOD."

EXAMPLE OUTPUT:
{"meeting_type": "standup", "summary": "The team held their daily standup meeting to discuss project updates and upcoming deadlines. Sarah kicked off the updates by announcing that the API integration was completed yesterday, and she plans to start writing tests today. John then raised a major blocker regarding the database migration, noting that he currently lacks access to staging and needs DevOps to resolve this today. The team discussed the urgency of this blocker and agreed that John should contact DevOps immediately to prevent project lag. Lastly, the team reviewed the upcoming client demo scheduled for Friday, confirming that all feature work must be wrapped up by Thursday EOD to ensure a smooth presentation.", "decisions": ["DevOps will be contacted immediately to unblock staging access for database migration", "All feature work must be completed by Thursday EOD for Friday client demo"], "action_items": [{"task": "Write tests for the completed API integration", "owner": "Sarah", "deadline": "Today", "priority": "medium"}, {"task": "Get DevOps to provide staging database access", "owner": "John", "deadline": "End of day today", "priority": "high"}, {"task": "Complete all feature work before client demo", "owner": "Unassigned", "deadline": "Thursday EOD", "priority": "high"}]}

Important rules:
- Extract ONLY information explicitly stated or strongly implied in the transcript.
- Do NOT invent names, dates, or tasks that are not present in the text.
- Keep decision descriptions concise — one sentence each.
- For action items, be specific about what needs to be done.
- Assign priority: "high" for urgent/blocking items, "medium" for standard tasks, "low" for nice-to-haves.
- If no clear decisions were made, return an empty "decisions" array.
- If no clear action items exist, return an empty "action_items" array.
- Respond with valid JSON only. No additional text before or after the JSON.

TRANSCRIPT:
{transcript}"""

# Maximum characters to send to the LLM to avoid exceeding context window.
# llama3:8b has an 8K context window (~6K tokens ≈ ~24K characters).
# We reserve ~2K tokens for the prompt template + response, leaving ~4K for transcript.
MAX_TRANSCRIPT_CHARS = 16000


async def summarize_transcript(transcript: str) -> MeetingSummary:
    """
    Send the transcript to a local Ollama LLM to generate a structured summary.

    Uses Ollama's OpenAI-compatible API endpoint at /v1/chat/completions.
    Includes transcript truncation to prevent context window overflow,
    and a 2-tier retry mechanism for JSON parsing failures.

    Args:
        transcript: The meeting transcript text.

    Returns:
        MeetingSummary with meeting_type, summary, decisions, and action_items.
    """
    # Truncate long transcripts to avoid exceeding model context window
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        logger.warning(
            f"Transcript too long ({len(transcript)} chars), truncating to {MAX_TRANSCRIPT_CHARS} chars"
        )
        transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n\n[Transcript truncated due to length]"

    prompt = SUMMARIZATION_PROMPT.replace("{transcript}", transcript)

    # --- Attempt 1: Primary LLM call ---
    raw_content = _call_ollama(
        messages=[
            {"role": "system", "content": "You are a meeting analysis assistant. Always respond with valid JSON only. Never wrap your response in markdown code fences."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    logger.info(f"LLM response [v{PROMPT_VERSION}] (first 200 chars): {raw_content[:200]}")

    # Try to parse the LLM response as JSON
    parsed = _parse_llm_response(raw_content)
    if parsed is not None:
        return parsed

    # --- Attempt 2: Retry with self-correction ---
    # Feed the failed response back so the LLM can see and fix its own mistake.
    # Lower temperature (0.1) reduces creativity and increases format adherence.
    logger.warning("First LLM response was not valid JSON, retrying with self-correction...")
    retry_content = _call_ollama(
        messages=[
            {"role": "system", "content": "You are a meeting analysis assistant. Respond ONLY with valid JSON. No markdown."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": raw_content},
            {"role": "user", "content": "Your previous response was not valid JSON. Please respond with ONLY the raw JSON object — no markdown code fences, no explanation, no text before or after."}
        ],
        temperature=0.1,
    )

    parsed = _parse_llm_response(retry_content)
    if parsed is not None:
        return parsed

    # --- Fallback: return raw text as summary with empty structured fields ---
    logger.warning("LLM retry also failed JSON parsing, using graceful fallback")
    return MeetingSummary(
        meeting_type="general",
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
                    deadline=item.get("deadline", "Not specified"),
                    priority=item.get("priority", "medium"),
                ))

        # Validate meeting_type against known types
        valid_types = {"standup", "planning", "review", "brainstorming",
                       "decision-making", "status-update", "retrospective", "general"}
        meeting_type = data.get("meeting_type", "general").lower()
        if meeting_type not in valid_types:
            meeting_type = "general"

        return MeetingSummary(
            meeting_type=meeting_type,
            summary=data.get("summary", ""),
            decisions=data.get("decisions", []),
            action_items=action_items
        )
    except Exception as e:
        logger.warning(f"Failed to build MeetingSummary: {e}")
        return None

