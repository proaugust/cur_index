"""LangChain LCEL 示意：要点 ∥ 风险 → 汇总（不套用原生四种模式）。"""

from fastapi import HTTPException
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.services.modules.agent_common import AgentStepData
from app.services.ops.llm_usage_callback import LlmUsageCallbackHandler

POINTS_SYS = "你是要点抽取器。针对用户任务列出 3 条关键要点，每条一行，用中文，不要写成文章。"
RISKS_SYS = "你是风险扫描器。针对用户任务列出 2 条潜在风险或注意点，每条一行，用中文。"
MERGE_SYS = "你是汇总助手。根据要点和风险，用中文写一段给业务同事的说明，不超过 120 字。"


def _make_llm(*, temperature: float) -> ChatOpenAI:
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="未配置 OPENAI_API_KEY，无法调用大模型")
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        base_url=settings.llm_api_base.rstrip("/"),
        temperature=temperature,
    )


def _chain(system_prompt: str, llm: ChatOpenAI) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("user", "{input}")])
    return prompt | llm | StrOutputParser()


def _invoke(chain: Runnable, user_input: str, caller: str) -> str:
    return chain.invoke(
        {"input": user_input},
        config={"callbacks": [LlmUsageCallbackHandler(caller)]},
    )


def run_agent_langchain(question: str, *, temperature: float) -> tuple[list[AgentStepData], str]:
    text = question.strip()
    if not text:
        raise HTTPException(status_code=400, detail="问题不能为空")

    llm = _make_llm(temperature=temperature)
    points = _invoke(_chain(POINTS_SYS, llm), text, "agent.langchain.points")
    risks = _invoke(_chain(RISKS_SYS, llm), text, "agent.langchain.risks")
    merge_in = f"任务：{text}\n\n要点：\n{points}\n\n风险：\n{risks}"
    answer = _invoke(_chain(MERGE_SYS, llm), merge_in, "agent.langchain.merge")

    steps = [
        AgentStepData(agent="要点抽取", role="LCEL 支路", input=text, output=points, meta="graph:points"),
        AgentStepData(agent="风险扫描", role="LCEL 支路", input=text, output=risks, meta="graph:risks"),
        AgentStepData(agent="汇总", role="Prompt | ChatOpenAI | Parser", input=merge_in, output=answer, meta="graph:merge"),
    ]
    return steps, answer
