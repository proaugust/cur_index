"""运维域 schema：错误日志等。"""

from datetime import datetime

from pydantic import BaseModel, Field


class AppErrorLogItem(BaseModel):
    id: int
    created_at: datetime
    level: str
    source: str
    error_type: str
    message: str
    detail: str | None = None
    request_id: str | None = None
    user_id: int | None = None
    path: str | None = None
    method: str | None = None
    ref_type: str | None = None
    ref_id: str | None = None
    status: str

    model_config = {"from_attributes": True}


class AppErrorLogListResponse(BaseModel):
    items: list[AppErrorLogItem]
    total: int
    page: int
    page_size: int


class AppErrorLogStatusUpdate(BaseModel):
    status: str = Field(pattern="^(open|resolved)$")
