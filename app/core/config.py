import os


class Settings:
    APP_NAME: str = "IsThisAI"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Auth stub - shared secret header, protects your LLM key from random traffic
    AUTH_TOKEN: str = os.getenv("AUTH_TOKEN", "change-me-locally")

    # LLM provider switch - flip one env var, no code changes needed anywhere else
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")  # "groq" or "anthropic"

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    CORS_ORIGINS: list[str] = ["*"]


settings = Settings()
