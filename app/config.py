import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if available
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

class Settings:
    NIMBLE_API_KEY: str = os.environ.get("NIMBLE_API_KEY", "")
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    # Natural-sounding voice replies (Orpheus TTS on Groq) and the small model that
    # rewrites answers into a short spoken style. Separate model = separate rate limit.
    TTS_MODEL: str = os.environ.get("TTS_MODEL", "canopylabs/orpheus-v1-english")
    TTS_VOICE: str = os.environ.get("TTS_VOICE", "hannah")
    SPEECH_STYLE_MODEL: str = os.environ.get("SPEECH_STYLE_MODEL", "openai/gpt-oss-20b")
    # Primary voice when set: ElevenLabs (falls back to Orpheus, then the browser voice).
    # Default voice "Sarah" is one of ElevenLabs' premade voices available on the free tier.
    ELEVENLABS_API_KEY: str = os.environ.get("ELEVENLABS_API_KEY", "").strip().replace("your-elevenlabs-api-key", "")
    ELEVENLABS_VOICE_ID: str = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
    ELEVENLABS_MODEL: str = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")

settings = Settings()
