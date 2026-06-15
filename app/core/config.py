from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8-sig",
    )

    app_name: str = "FastAPI App"
    debug: bool = False
    database_url: str = "postgresql://postgres:postgres@localhost:5435/callmind"
    embedding_model_name: str = "BAAI/bge-small-zh-v1.5"
    embedding_dim: int = 512
    embedding_query_instruction: str = "为这个句子生成表示以用于检索相关文章："
    llm_api_base: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"


settings = Settings()
