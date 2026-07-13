import os
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Ollama base URL for LLM summarization (OpenAI-compatible endpoint)
    ollama_base_url: str = "http://localhost:11434/v1"

    # Ollama model for summarization
    ollama_model: str = "llama3:8b"

    # Local Whisper model size for transcription (tiny/base/small/medium/large)
    whisper_model_size: str = "base"

    # Max upload size in bytes (25MB — Whisper limit)
    max_upload_size: int = 25 * 1024 * 1024

    # Allowed audio file extensions
    allowed_extensions: set = {".mp3", ".wav", ".m4a", ".webm", ".ogg", ".mp4", ".mpeg", ".mpga"}

    # SQLite database path
    database_path: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "meetings.db")

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
