from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_LOCAL_DB = "postgresql://postgres:postgres@localhost:5435/ai_test"
# Supabase 东京区 Pooler：Dashboard 给 aws-1，旧文档/Secret 常见误写 aws-0
_POOLER_AWS0 = "aws-0-ap-northeast-1.pooler.supabase.com"
_POOLER_AWS1 = "aws-1-ap-northeast-1.pooler.supabase.com"


def _normalize_pooler_host(url: str) -> str:
    return url.replace(_POOLER_AWS0, _POOLER_AWS1)


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
    # auto：有 CUDA 用 gpu；也可强制 cpu / cuda。batch_size=0 按设备自适应
    embedding_device: str = "auto"
    embedding_batch_size: int = 0
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
    database_url_source: str = ""
    redis_url: str = "redis://127.0.0.1:6379/0"
    redis_enabled: bool = True
    redis_socket_timeout: float = 2.0
    complaint_stats_cache_ttl: int = 3600  # 多维统计默认缓存 1 小时
    complaint_stats_nl_cache_ttl: int = 86400  # 自然语言查询缓存 24 小时
    complaint_stats_memory_cache_enabled: bool = True
    complaint_stats_memory_cache_maxsize: int = 32
    llm_usage_stats_cache_ttl: int = 90
    insight_profile_cache_ttl: int = 86400
    insight_model_dir: Path = BASE_DIR / "data" / "insight" / "models"
    insight_auto_train: bool = True
    insight_model_backend: str = "auto"
    rate_limit_enabled: bool = True
    rate_limit_complaints_stats: int = 20  # /complaints/stats 每用户每分钟
    rate_limit_complaints_samples: int = 60  # /complaints/samples 每用户每分钟

    @model_validator(mode="after")
    def _resolve_database_url(self) -> Self:
        source = "local_default"
        if self.database_url.startswith(("postgresql://", "postgresql+")):
            source = "DATABASE_URL"
        elif self.supabase_url and self.supabase_db_password:
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
            source = "supabase_compose"
        else:
            object.__setattr__(self, "database_url", _DEFAULT_LOCAL_DB)

        url = _normalize_pooler_host(self.database_url)
        if url != self.database_url:
            source = f"{source}+pooler_fix"
        object.__setattr__(self, "database_url", url)
        object.__setattr__(self, "database_url_source", source)
        return self

    def supabase_client(self):
        from supabase import create_client

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL / SUPABASE_KEY 未配置")
        return create_client(self.supabase_url, self.supabase_key)


settings = Settings()
