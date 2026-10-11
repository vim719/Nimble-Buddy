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

settings = Settings()
