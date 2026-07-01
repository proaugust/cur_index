"""LangChain LLM 调用用量回调。"""

from __future__ import annotations

import time

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.core.config import settings
from app.services.llm_usage_service import record_llm_usage


class LlmUsageCallbackHandler(BaseCallbackHandler):
    def __init__(self, caller: str) -> None:
        self.caller = caller
        self._started = 0.0

    def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs) -> None:
        self._started = time.perf_counter()

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        usage = _extract_token_usage(response)
        elapsed_ms = int((time.perf_counter() - self._started) * 1000)
        record_llm_usage(
            caller=self.caller,
            engine="langchain",
            model=settings.llm_model,
            prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
            completion_tokens=int(usage.get("completion_tokens", 0) or 0),
            total_tokens=int(usage.get("total_tokens", 0) or 0),
            latency_ms=elapsed_ms,
            success=True,
        )

    def on_llm_error(self, error: BaseException, **kwargs) -> None:
        elapsed_ms = int((time.perf_counter() - self._started) * 1000)
        record_llm_usage(
            caller=self.caller,
            engine="langchain",
            model=settings.llm_model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=elapsed_ms,
            success=False,
        )


def _extract_token_usage(response: LLMResult) -> dict:
    if response.llm_output:
        usage = response.llm_output.get("token_usage")
        if isinstance(usage, dict):
            return usage
    for gen_list in response.generations:
        for gen in gen_list:
            info = getattr(gen, "generation_info", None) or {}
            usage = info.get("token_usage") if isinstance(info, dict) else None
            if isinstance(usage, dict) and usage:
                return usage
    return {}
