from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    """Application settings loaded from environment variables or .env."""

    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment_gpt4o: str
    azure_openai_deployment_embedding: str
    azure_openai_api_version: str

    # Tavily
    tavily_api_key: str

    # App
    log_level: str = "INFO"
    max_file_size_mb: int = 50
    max_files_per_session: int = 4
    faiss_index_path: str = "./data/faiss_index"
    uploads_path: str = "./data/uploads"
    exports_path: str = "./data/exports"
    sqlite_db_path: str = "./data/app.db"
    cors_origins: List[str] = ["*"]
    grounding_mode: str = "faiss"
    auto_delete_on_new_session: bool = True

    # Azure Blob Storage
    azure_storage_connection_string: str = ""
    azure_storage_container: str = "investment-analyst-sessions"
    session_blob_prefix: str = "sessions"

    # Azure AI Search
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index_name: str = "investment-analyst-sessions"
    azure_search_api_version: str = "2024-07-01"
    azure_search_vector_dimensions: int = 1536

    @staticmethod
    def from_env() -> "Settings":
        cors = os.getenv("CORS_ORIGINS", "*")
        origins = [o.strip() for o in cors.split(",") if o.strip()]
        return Settings(
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            azure_openai_deployment_gpt4o=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4O", "gpt-4o"),
            azure_openai_deployment_embedding=os.getenv("AZURE_OPENAI_DEPLOYMENT_EMBEDDING", "text-embedding-ada-002"),
            azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_file_size_mb=_env_int("MAX_FILE_SIZE_MB", 50),
            max_files_per_session=_env_int("MAX_FILES_PER_SESSION", 4),
            faiss_index_path=os.getenv("FAISS_INDEX_PATH", "./data/faiss_index"),
            uploads_path=os.getenv("UPLOADS_PATH", "./data/uploads"),
            exports_path=os.getenv("EXPORTS_PATH", "./data/exports"),
            sqlite_db_path=os.getenv("SQLITE_DB_PATH", "./data/app.db"),
            cors_origins=origins or ["*"],
            grounding_mode=os.getenv("GROUNDING_MODE", "faiss").strip().lower() or "faiss",
            auto_delete_on_new_session=_env_bool("AUTO_DELETE_ON_NEW_SESSION", True),
            azure_storage_connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING", ""),
            azure_storage_container=os.getenv("AZURE_STORAGE_CONTAINER", "investment-analyst-sessions"),
            session_blob_prefix=os.getenv("SESSION_BLOB_PREFIX", "sessions"),
            azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT", "").rstrip("/"),
            azure_search_api_key=os.getenv("AZURE_SEARCH_API_KEY", ""),
            azure_search_index_name=os.getenv("AZURE_SEARCH_INDEX_NAME", "investment-analyst-sessions"),
            azure_search_api_version=os.getenv("AZURE_SEARCH_API_VERSION", "2024-07-01"),
            azure_search_vector_dimensions=_env_int("AZURE_SEARCH_VECTOR_DIMENSIONS", 1536),
        )


settings = Settings.from_env()
