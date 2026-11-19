from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_project_env() -> None:
    """Load the local project .env without adding another runtime dependency."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_project_env()


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    app_secret_key: str = os.getenv("APP_SECRET_KEY", "change-me-in-production")
    frontend_origins: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
        if item.strip()
    )
    data_backend: str = os.getenv("ELECTORAW_DATA_BACKEND", "mysql").lower()
    data_root: Path = Path(os.getenv("ELECTORAW_DATA_ROOT", str(ROOT / "data" / "processed")))
    mysql_host: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_database: str = os.getenv("MYSQL_DATABASE", "electoraw")
    mysql_user: str = os.getenv("MYSQL_USER", "")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "")
    workflow_backend: str = os.getenv("WORKFLOW_BACKEND", "mysql").lower()
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017/")
    mongodb_database: str = os.getenv("MONGODB_DATABASE", "electoraw")
    admin_token: str = os.getenv("ADMIN_TOKEN", "")
    workflow_db_path: Path = Path(os.getenv("WORKFLOW_DB_PATH", str(ROOT / "database" / "electoraw_workflow.sqlite3")))
    certificate_dir: Path = Path(os.getenv("CERTIFICATE_DIR", str(ROOT / "database" / "certificates")))
    vector_db_path: Path = Path(os.getenv("VECTOR_DB_PATH", str(ROOT / "database" / "chroma")))
    vector_collection: str = os.getenv("VECTOR_COLLECTION", "electoraw_corpus")
    rag_llm_base_url: str = os.getenv("RAG_LLM_BASE_URL", "")
    rag_llm_api_key: str = os.getenv("RAG_LLM_API_KEY", "")
    rag_llm_model: str = os.getenv("RAG_LLM_MODEL", "")
    rag_allow_remote_fetch: bool = _bool("RAG_ALLOW_REMOTE_FETCH", False)

    @property
    def mongodb_configured(self) -> bool:
        return bool(os.getenv("MONGODB_URI"))


settings = Settings()
