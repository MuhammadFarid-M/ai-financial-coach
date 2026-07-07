"""
Central application configuration.

Why a dedicated config module?
- One place to read every environment variable, validated on startup.
- The rest of the code imports `settings` instead of calling os.getenv()
  everywhere, so a missing/invalid variable fails loudly and immediately.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    # Read from the DATABASE_URL environment variable (or the .env file).
    DATABASE_URL: str

    # --- Auth / JWT ---
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # --- OpenRouter (the AI engine) ---
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-oss-120b:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    # Strict JSON mode. Leave False for max compatibility with free models
    # (many free models reject response_format). The prompt already asks for
    # JSON, and the engine parses it leniently either way.
    OPENROUTER_JSON_MODE: bool = False

    # --- CORS: which frontend origins may call this API ---
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        """
        Render (and Heroku) hand out URLs that start with `postgres://`,
        but SQLAlchemy + psycopg2 expects `postgresql://`. Normalise it here
        so the exact same code runs locally and in the cloud.
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    # lru_cache => the .env file is read once, then cached for the process.
    return Settings()


settings = get_settings()
