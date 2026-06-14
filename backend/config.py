import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # OpenAI
    OPENAI_API_KEY: str  = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str    = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_TTS_MODEL: str= os.getenv("OPENAI_TTS_MODEL", "tts-1")
    OPENAI_STT_MODEL: str= os.getenv("OPENAI_STT_MODEL", "whisper-1")
    OPENAI_TTS_VOICE: str= os.getenv("OPENAI_TTS_VOICE", "alloy")

    # App
    APP_TITLE: str   = "ShopWave Customer Support Agent"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool      = os.getenv("DEBUG", "false").lower() == "true"

    # SMTP (leave blank to use dev-mode console logging)
    SMTP_HOST: str     = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int     = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str     = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM: str    = os.getenv("EMAIL_FROM", "")

settings = Settings()
