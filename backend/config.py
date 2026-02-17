import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ai_coach.db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_TRANSCRIPTION_MODEL = os.getenv("GEMINI_TRANSCRIPTION_MODEL", "gemini-2.5-flash")
GEMINI_EVALUATION_MODEL = os.getenv("GEMINI_EVALUATION_MODEL", "gemini-2.5-flash")

TELPHIN_APP_ID = os.getenv("TELPHIN_APP_ID", "")
TELPHIN_APP_SECRET = os.getenv("TELPHIN_APP_SECRET", "")
TELPHIN_API_BASE = "https://apiproxy.telphin.ru"
TELPHIN_MIN_DURATION = int(os.getenv("TELPHIN_MIN_DURATION", "10"))
TELPHIN_DELAY_BETWEEN_CALLS = int(os.getenv("TELPHIN_DELAY_BETWEEN_CALLS", "5"))

default_origins = "http://localhost:3000,https://ai-coach3-lena.vercel.app"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", default_origins).split(",")