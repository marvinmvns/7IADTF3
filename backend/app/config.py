"""Configurações centrais da aplicação."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "MedAssist - Assistente Médico Virtual"
    debug: bool = True

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "medassist"
    db_user: str = "medassist"
    db_pass: str = "medassist123"

    # LLM
    llm_provider: str = "llama-cpp"  # llama-cpp | openai | ollama
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen3.5:4b"
    llama_cpp_url: str = "http://llama-server:8080"
    models_dir: str = "/models"

    # TTS/STT
    tts_model: str = "piper"  # piper (local, sem GPU)
    stt_model: str = "vosk"   # vosk (local, sem GPU)
    piper_voice: str = "pt_BR-faber-medium"

    # Web Search (Brave)
    brave_search_api_key: str = ""

    # Scraping
    scraping_interval_hours: int = 24
    max_concurrent_scrapers: int = 3

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url_sync(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
