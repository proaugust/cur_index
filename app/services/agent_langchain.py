from fastapi import HTTPException
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.services.agent_common import (
    GENERATE_SYSTEM,
    REFLECTION_MAX_ROUNDS,
    REFLECTION_PASS_SCORE,
    REVISE_SYSTEM,
    REVIEW_SYSTEM,
    ROUTE_SYSTEM,
    ROUTING_ANSWER_WITH_TOOL_SYSTEM,
    SEQUENTIAL_AGENTS,
    SINGLE_ANSWER_SYSTEM,
    SPECIALISTS,
    AgentMode,
    AgentStepData,
    build_routing_user_prompt,
    build_sequential_context,
    detect_weather_tool,
    extract_weather_city,
    parse_reflection_score,
    parse_route_category,
    prepare_single_run,
    run_weather_tool,
)
from app.services.llm_usage_callback import LlmUsageCallbackHandler


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


def run_single(question: str, *, temperature: float) -> tuple[list[AgentStepData], str]:
    steps, user_prompt, used_tool = prepare_single_run(question)
    llm = _make_llm(temperature=temperature)
    answer = _invoke(_chain(SINGLE_ANSWER_SYSTEM, llm), user_prompt, "agent.langchain.single")
    steps.append(
        AgentStepData(
            agent="回答 Agent (LangChain)",
            role="基于工具结果生成答复" if used_tool else "ChatPromptTemplate | ChatOpenAI | StrOutputParser",
            input=user_prompt,
            output=answer,
            meta="used_tool=calc" if used_tool else "direct",
        )
    )
    return steps, answer


def run_sequential(question: str, *, temperature: float) -> tuple[list[AgentStepData], str]:
    llm = _make_llm(temperature=temperature)
    steps: list[AgentStepData] = []
    context = f"原始问题：{question}"
    last_output = ""

    for i, agent in enumerate(SEQUENTIAL_AGENTS):
        user_input = question if i == 0 else context
        chain = _chain(agent["prompt"], llm)
        output = _invoke(chain, user_input, f"agent.langchain.sequential.{i}")
        steps.append(
            AgentStepData(
                agent=f"{agent['name']} (LangChain)",
                role=agent["role"],
                input=context,
                output=output,
            )
        )
        context = build_sequential_context(question, i, output, context)
        last_output = output

    return steps, last_output


def run_routing(question: str, *, temperature: float) -> tuple[list[AgentStepData], str]:
    llm_route = _make_llm(temperature=min(temperature, 0.2))
    llm_answer = _make_llm(temperature=temperature)
    use_weather = detect_weather_tool(question)

    route_chain = _chain(ROUTE_SYSTEM, llm_route)
    route_raw = _invoke(route_chain, question, "agent.langchain.routing.route")
    category = parse_route_category(route_raw)
    specialist = SPECIALISTS[category]

    steps = [
        AgentStepData(
            agent="路由 Agent (LangChain)",
            role="RunnableBranch 路由分发",
            input=question,
            output=f"路由结果：{category}",
            meta=f"选中 {specialist['name']}" + (" + weather 工具" if use_weather else ""),
        ),
    ]

    if use_weather:
        city = extract_weather_city(question)
        tool_output = run_weather_tool(city)
        steps.append(
            AgentStepData(
                agent="工具 Agent (LangChain)",
                role=f"调用 weather 查询 {city} 天气",
                input=city,
                output=tool_output,
                meta="builtin:weather",
            )
        )
        user_prompt = build_routing_user_prompt(question, tool_output)
        answer = _invoke(
            _chain(ROUTING_ANSWER_WITH_TOOL_SYSTEM, llm_answer),
            user_prompt,
            "agent.langchain.routing.weather_answer",
        )
        steps.append(
            AgentStepData(
                agent=f"{specialist['name']} (LangChain)",
                role="基于天气数据作答",
                input=user_prompt,
                output=answer,
            )
        )
        return steps, answer

    specialist_chain = _chain(specialist["prompt"], llm_answer)
    answer = _invoke(specialist_chain, question, f"agent.langchain.routing.{category}")
    steps.append(
        AgentStepData(
            agent=f"{specialist['name']} (LangChain)",
            role="领域专家作答",
            input=question,
            output=answer,
        )
    )
    return steps, answer


def run_reflection(question: str, *, temperature: float) -> tuple[list[AgentStepData], str]:
    llm = _make_llm(temperature=temperature)
    llm_review = _make_llm(temperature=min(temperature, 0.3))

    generate_chain = _chain(GENERATE_SYSTEM, llm)
    review_chain = _chain(REVIEW_SYSTEM, llm_review)
    revise_chain = _chain(REVISE_SYSTEM, llm)

    steps: list[AgentStepData] = []
    draft = _invoke(generate_chain, question, "agent.langchain.reflection.generate")
    steps.append(
        AgentStepData(
            agent="生成 Agent (LangChain)",
            role="第 1 轮初稿",
            input=question,
            output=draft,
        )
    )

    for round_num in range(1, REFLECTION_MAX_ROUNDS + 1):
        review = _invoke(
            review_chain,
            f"用户问题：{question}\n\n草稿：\n{draft}",
            f"agent.langchain.reflection.review.{round_num}",
        )
        steps.append(
            AgentStepData(
                agent="评审 Agent (LangChain)",
                role=f"第 {round_num} 轮评审",
                input=draft,
                output=review,
            )
        )

        score = parse_reflection_score(review)
        if score >= REFLECTION_PASS_SCORE or round_num == REFLECTION_MAX_ROUNDS:
            steps.append(
                AgentStepData(
                    agent="最终输出 (LangChain)",
                    role="评审通过" if score >= REFLECTION_PASS_SCORE else "达到最大轮次",
                    input=review,
                    output=draft,
                    meta=f"评分 {score}/10",
                )
            )
            return steps, draft

        old_draft = draft
        draft = _invoke(
            revise_chain,
            f"用户问题：{question}\n\n当前草稿：\n{draft}\n\n评审意见：\n{review}",
            f"agent.langchain.reflection.revise.{round_num}",
        )
        steps.append(
            AgentStepData(
                agent="修订 Agent (LangChain)",
                role=f"第 {round_num} 轮修订",
                input=f"{old_draft}\n\n评审意见：\n{review}",
                output=draft,
            )
        )

    return steps, draft


_RUNNERS = {
    "single": run_single,
    "sequential": run_sequential,
    "routing": run_routing,
    "reflection": run_reflection,
}


def run_agent_langchain(mode: AgentMode, question: str, *, temperature: float) -> tuple[list[AgentStepData], str]:
    text = question.strip()
    if not text:
        raise HTTPException(status_code=400, detail="问题不能为空")
    runner = _RUNNERS.get(mode)
    if runner is None:
        raise HTTPException(status_code=400, detail=f"不支持的 mode: {mode}")
    return runner(text, temperature=temperature)
