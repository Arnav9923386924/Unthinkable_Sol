import whisper
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.config import settings

logger = logging.getLogger(__name__)

# Load model once at module level to avoid reloading on every request.
_model = None


def _get_model():
    """Lazy-load the Whisper model on first use with automatic CUDA-to-CPU fallback."""
    global _model
    if _model is None:
        model_size = settings.whisper_model_size
        logger.info(f"Loading Whisper '{model_size}' model (first request may take a moment)...")
        try:
            # Try loading on CUDA first
            _model = whisper.load_model(model_size, device="cuda")
            logger.info("Whisper model loaded on CUDA successfully.")
        except Exception as e:
            logger.warning(
                f"Could not load Whisper model on CUDA (likely out of VRAM due to Ollama). "
                f"Falling back to CPU. Error: {e}"
            )
            _model = whisper.load_model(model_size, device="cpu")
            logger.info("Whisper model loaded on CPU successfully.")
    return _model


async def transcribe_audio(file_path: str) -> dict:
    """
    Transcribe an audio file using local OpenAI Whisper model.

    Runs Whisper locally — no API key or network call needed.
    The model is loaded once and cached for subsequent requests.
    Automatically handles device compatibility (CUDA/CPU) and avoids blocking the event loop.

    Args:
        file_path: Path to the audio file on disk.

    Returns:
        A dict containing "text", "segments", and "duration".
    """
    model = _get_model()

    logger.info(f"Transcribing: {file_path}")

    # Determine device type of loaded model to set fp16 correctly
    # fp16=True is only supported on GPU; running it on CPU raises RuntimeError
    device = next(model.parameters()).device
    fp16 = device.type == "cuda"
    logger.info(f"Whisper inference device: {device} (fp16={fp16})")

    # Run blocking transcribe in a separate thread to prevent event loop lag
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(
            pool,
            lambda: model.transcribe(file_path, fp16=fp16)
        )

    transcript = result.get("text", "").strip()
    segments = result.get("segments", [])
    duration = segments[-1].get("end", 0.0) if segments else 0.0
    logger.info(f"Transcription complete: {len(transcript)} characters, duration: {duration}s")

    # Sanitize segments to keep start, end, and text
    clean_segments = []
    for s in segments:
        clean_segments.append({
            "start": s.get("start", 0.0),
            "end": s.get("end", 0.0),
            "text": s.get("text", "").strip()
        })

    return {
        "text": transcript,
        "segments": clean_segments,
        "duration": duration
    }
