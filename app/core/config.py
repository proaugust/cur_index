from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_LOCAL_DB = "postgresql://postgres:postgres@localhost:5435/ai_test"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8-sig",
        env_ignore_empty=True,
    )

    app_name: str = "FastAPI App"
    debug: bool = False
    database_url: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_db_password: str = ""
    supabase_pooler_host: str = "aws-1-ap-northeast-1.pooler.supabase.com"
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
    # Docker/HF 设为 true：API 挂 /api 前缀并托管 static/；本地不设，保持 Vite 代理
    serve_static: bool = False

    @model_validator(mode="after")
    def _resolve_database_url(self) -> Self:
        if self.database_url.startswith(("postgresql://", "postgresql+")):
            return self
        if self.supabase_url and self.supabase_db_password:
            ref = self.supabase_url.removeprefix("https://").removeprefix("http://").removesuffix(".supabase.co")
            pwd = urllib.parse.quote_plus(self.supabase_db_password)
            object.__setattr__(
                self,
                "database_url",
                (
                    f"postgresql+psycopg2://postgres.{ref}:{pwd}"
                    f"@{self.supabase_pooler_host}:6543/postgres?sslmode=require"
                ),
            )
        else:
            object.__setattr__(self, "database_url", _DEFAULT_LOCAL_DB)
        return self

    def supabase_client(self):
        from supabase import create_client

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL / SUPABASE_KEY 未配置")
        return create_client(self.supabase_url, self.supabase_key)


settings = Settings()
