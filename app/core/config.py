from dotenv import load_dotenv

load_dotenv()

import os


class Settings:
    APP_NAME: str = "IsThisAI"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    AUTH_TOKEN: str = os.getenv("AUTH_TOKEN", "change-me-locally")

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    CORS_ORIGINS: list[str] = ["*"]


settings = Settings()
