from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/attendance"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    faiss_index_path: str = "./faiss_indexes/faces.index"
    faiss_meta_path: str = "./faiss_indexes/faces_meta.json"
    insightface_model: str = "buffalo_l"
    insightface_ctx_id: int = -1  # -1 CPU, 0 first GPU
    det_size_width: int = 320
    det_size_height: int = 320
    recognition_threshold: float = 0.45
    unknown_threshold: float = 0.35
    enrichment_threshold: float = 0.75
    enrichment_max_ratio: float = 0.35
    enrichment_max_embeddings_per_user: int = 20
    enrichment_dedupe_seconds: int = 60
    dedupe_window_seconds: int = 120
    frame_process_workers: int = 2
    onnx_providers: str = "CUDAExecutionProvider,CPUExecutionProvider"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
