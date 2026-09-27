from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from functools import lru_cache
from typing import List, Union
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = (PROJECT_ROOT / "data" / "ibvap_dev.db").as_posix()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"), extra="ignore")

    APP_NAME: str = "IBVAP"
    APP_ENV: str = "development"
    API_VERSION: str = "1.0.0"
    
    # Auth
    JWT_SECRET_KEY: str = "super_secret_dev_key_change_in_prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # DB
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}"
    
    # Paths
    CAMERAS_CONFIG_PATH: str = str(PROJECT_ROOT / "configs" / "cameras.yaml")
    EVIDENCE_STORAGE_PATH: str = str(PROJECT_ROOT / "data" / "evidence")
    
    # ML
    DETECTION_MODEL: str = "yolov8n"
    DETECTION_MODEL_PATH: str = str(PROJECT_ROOT / "models" / "yolov8n.pt")
    DETECTION_DEVICE: str = "cpu"
    DETECTION_CONFIDENCE_THRESHOLD: float = 0.4
    
    CORS_ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        if not v or "ibvap_dev.db" in str(v):
            return f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}"
        if str(v).startswith("sqlite:///") and "+aiosqlite" not in str(v):
            return str(v).replace("sqlite:///", "sqlite+aiosqlite:///")
        return str(v)

    @field_validator("DETECTION_MODEL_PATH", mode="before")
    @classmethod
    def assemble_model_path(cls, v: str) -> str:
        if not v or not Path(v).is_file():
            return str(PROJECT_ROOT / "models" / "yolov8n.pt")
        return str(v)

@lru_cache()
def get_settings():
    return Settings()
