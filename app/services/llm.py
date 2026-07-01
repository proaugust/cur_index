import json
import logging
import time
import urllib.error
import urllib.request

from fastapi import HTTPException

from app.core.config import settings
from app.core.http_logging import get_request_id
from app.services.llm_usage_service import record_llm_usage

logger = logging.getLogger(__name__)

# 复用连接，减少首次 HTTPS 握手开销
_http_opener = urllib.request.build_opener()


def warmup() -> None:
    """启动时发一次极短请求，预热 TLS/连接；未配置密钥时跳过。"""
    if not settings.openai_api_key:
        return
    try:
        chat_completion("你是助手。", "请只回复一个字：好", temperature=0, caller="warmup")
    except HTTPException:
        logger.warning("LLM 预热失败，首次 polished 请求可能更慢", exc_info=True)


def _parse_usage(body: dict) -> tuple[int, int, int]:
    usage = body.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    total_tokens = int(usage.get("total_tokens", 0) or 0)
    if total_tokens <= 0:
        total_tokens = prompt_tokens + completion_tokens
    return prompt_tokens, completion_tokens, total_tokens


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.3,
    json_mode: bool = False,
    caller: str = "unknown",
    engine: str = "native",
) -> str:
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="未配置 OPENAI_API_KEY，无法调用大模型")

    url = f"{settings.llm_api_base.rstrip('/')}/chat/completions"
    body: dict = {
        "model": settings.llm_model,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": temperature,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.openai_api_key}"}, method="POST"
    )

    rid = get_request_id()
    model = settings.llm_model
    started = time.perf_counter()
    try:
        with _http_opener.open(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.warning(
            "LLM 请求失败 request_id=%s caller=%s model=%s json_mode=%s %.0fms http=%s",
            rid,
            caller,
            model,
            json_mode,
            elapsed_ms,
            exc.code,
        )
        record_llm_usage(
            caller=caller,
            engine=engine,
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=elapsed_ms,
            success=False,
            request_id=rid,
        )
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"大模型接口调用失败: {detail}") from exc
    except urllib.error.URLError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.warning(
            "LLM 连接失败 request_id=%s caller=%s model=%s json_mode=%s %.0fms reason=%s",
            rid,
            caller,
            model,
            json_mode,
            elapsed_ms,
            exc.reason,
        )
        record_llm_usage(
            caller=caller,
            engine=engine,
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=elapsed_ms,
            success=False,
            request_id=rid,
        )
        raise HTTPException(status_code=502, detail=f"无法连接大模型服务: {exc.reason}") from exc

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    try:
        content = body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning(
            "LLM 返回格式异常 request_id=%s caller=%s model=%s json_mode=%s %.0fms",
            rid,
            caller,
            model,
            json_mode,
            elapsed_ms,
        )
        record_llm_usage(
            caller=caller,
            engine=engine,
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=elapsed_ms,
            success=False,
            request_id=rid,
        )
        raise HTTPException(status_code=502, detail="大模型返回格式异常") from exc

    prompt_tokens, completion_tokens, total_tokens = _parse_usage(body)
    record_llm_usage(
        caller=caller,
        engine=engine,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        latency_ms=elapsed_ms,
        success=True,
        request_id=rid,
    )
    return content
