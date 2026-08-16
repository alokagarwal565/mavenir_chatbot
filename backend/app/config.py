from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from pathlib import Path

# Resolve root .env path regardless of execution working directory
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/3gpp_rag?sslmode=disable"
    
    # LLM Provider Configuration
    gemini_api_key: str = ""
    gemini_api_key_2: Optional[str] = ""
    gemini_api_key_3: Optional[str] = ""
    gemini_api_key_backup: Optional[str] = ""
    
    llm_provider: str = "gemini"
    gemini_model_fast: str = "gemini-3.5-flash-lite"
    gemini_model_heavy: str = "gemini-3.6-flash"
    gemini_model_fallback_fast: str = "gemini-3.1-flash-lite"
    gemini_model_fallback_heavy: str = "gemini-3.5-flash"
    gemini_vision_model: str = "gemini-3.6-flash"

    llm_model: str = "gemini-3.5-flash-lite"
    llm_fallback_model: str = "gemini-3.1-flash-lite"
    llm_timeout_seconds: float = 25.0
    context_token_limit: int = 6000
    
    # Embedding and Reranker
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_enabled: bool = True
    
    # Reliability Thresholds
    abstain_threshold: float = 0.25
    reranker_floor: float = 0.15
    rrf_floor: float = 0.005
    
    # Cost Tracking Thresholds (USD)
    gemini_input_cost_per_1k: float = 0.000075
    gemini_output_cost_per_1k: float = 0.000300
    llm_cost_warn_threshold_usd: float = 0.01
    
    # Server & CORS
    port: int = 7860
    frontend_url: str = "http://localhost:5173"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=(str(ENV_PATH), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_gemini_api_keys(self) -> List[str]:
        keys = []
        for k in [self.gemini_api_key, self.gemini_api_key_2, self.gemini_api_key_3, self.gemini_api_key_backup]:
            if k and k.strip():
                keys.append(k.strip())
        return keys

settings = Settings()
