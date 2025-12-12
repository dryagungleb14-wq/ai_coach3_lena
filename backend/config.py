import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ai_coach.db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_TRANSCRIPTION_MODEL = os.getenv("GEMINI_TRANSCRIPTION_MODEL", "gemini-2.5-flash")
GEMINI_EVALUATION_MODEL = os.getenv("GEMINI_EVALUATION_MODEL", "gemini-2.5-flash")

# CORS Configuration
# Default to "*" for development convenience, but strongly recommended to set in production
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
