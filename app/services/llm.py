import json
import logging
import urllib.error
import urllib.request

from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

# 复用连接，减少首次 HTTPS 握手开销
_http_opener = urllib.request.build_opener()


def warmup() -> None:
    """启动时发一次极短请求，预热 TLS/连接；未配置密钥时跳过。"""
    if not settings.llm_api_key:
        return
    try:
        chat_completion("你是助手。", "请只回复一个字：好", temperature=0)
    except HTTPException:
        logger.warning("LLM 预热失败，首次 polished 请求可能更慢", exc_info=True)


def chat_completion(system_prompt: str, user_prompt: str, *, temperature: float = 0.3) -> str:
    if not settings.llm_api_key:
        raise HTTPException(
            status_code=503,
            detail="未配置 LLM_API_KEY，无法调用大模型",
        )

    url = f"{settings.llm_api_base.rstrip('/')}/chat/completions"
    payload = json.dumps(
        {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        },
        method="POST",
    )

    try:
        with _http_opener.open(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=502,
            detail=f"大模型接口调用失败: {detail}",
        ) from exc
    except urllib.error.URLError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"无法连接大模型服务: {exc.reason}",
        ) from exc

    try:
        return body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail="大模型返回格式异常",
        ) from exc
