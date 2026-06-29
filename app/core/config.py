from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8-sig")

    app_name: str = "FastAPI App"
    debug: bool = False
    database_url: str = "postgresql://postgres:postgres@localhost:5435/ai_test"
    embedding_model_name: str = "BAAI/bge-small-zh-v1.5"
    embedding_dim: int = 512
    embedding_query_instruction: str = "为这个句子生成表示以用于检索相关文章："
    complaint_classify_threshold: float = 0.65
    complaint_name_dedupe_threshold: float = 0.85
    llm_api_base: str = "https://api.deepseek.com/v1"
    openai_api_key: str = ""
    llm_model: str = "deepseek-v4-flash"
    attendance_faces_dir: Path = BASE_DIR / "data" / "attendance_faces"
    jwt_secret_key: str = "change-me-in-production-use-env"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24


settings = Settings()
