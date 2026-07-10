from fastapi import HTTPException

from app.services.modules.agent_common import (
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
from app.services.shared.llm import chat_completion


def _ask(system_prompt: str, user_prompt: str, *, temperature: float, caller: str) -> str:
    return chat_completion(system_prompt, user_prompt, temperature=temperature, caller=caller)


def run_single(question: str, *, temperature: float) -> tuple[list[AgentStepData], str]:
    steps, user_prompt, used_tool = prepare_single_run(question)
    answer = _ask(SINGLE_ANSWER_SYSTEM, user_prompt, temperature=temperature, caller="agent.native.single")
    steps.append(
        AgentStepData(
            agent="回答 Agent",
            role="基于工具结果生成答复" if used_tool else "直接回答用户问题",
            input=user_prompt,
            output=answer,
            meta="used_tool=calc" if used_tool else "direct",
        )
    )
    return steps, answer


def run_sequential(question: str, *, temperature: float) -> tuple[list[AgentStepData], str]:
    steps: list[AgentStepData] = []
    context = f"原始问题：{question}"
    last_output = ""

    for i, agent in enumerate(SEQUENTIAL_AGENTS):
        user_prompt = question if i == 0 else context
        output = _ask(
            agent["prompt"],
            user_prompt,
            temperature=temperature,
            caller=f"agent.native.sequential.{i}",
        )
        steps.append(
            AgentStepData(
                agent=agent["name"],
                role=agent["role"],
                input=context,
                output=output,
            )
        )
        context = build_sequential_context(question, i, output, context)
        last_output = output

    return steps, last_output


def run_routing(question: str, *, temperature: float) -> tuple[list[AgentStepData], str]:
    route_raw = _ask(ROUTE_SYSTEM, question, temperature=min(temperature, 0.2), caller="agent.native.routing.route")
    category = parse_route_category(route_raw)
    specialist = SPECIALISTS[category]
    use_weather = detect_weather_tool(question)

    steps = [
        AgentStepData(
            agent="路由 Agent",
            role="判断问题所属领域",
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
                agent="工具 Agent",
                role=f"调用 weather 查询 {city} 天气",
                input=city,
                output=tool_output,
                meta="builtin:weather",
            )
        )
        user_prompt = build_routing_user_prompt(question, tool_output)
        answer = _ask(
            ROUTING_ANSWER_WITH_TOOL_SYSTEM,
            user_prompt,
            temperature=temperature,
            caller="agent.native.routing.weather_answer",
        )
        steps.append(
            AgentStepData(
                agent=specialist["name"],
                role="基于天气数据作答",
                input=user_prompt,
                output=answer,
            )
        )
        return steps, answer

    steps.append(
        AgentStepData(
            agent=specialist["name"],
            role="领域专家作答",
            input=question,
            output="",
        )
    )
    answer = _ask(
        specialist["prompt"],
        question,
        temperature=temperature,
        caller=f"agent.native.routing.{category}",
    )
    steps[-1].output = answer
    return steps, answer


def run_reflection(question: str, *, temperature: float) -> tuple[list[AgentStepData], str]:
    steps: list[AgentStepData] = []
    draft = _ask(GENERATE_SYSTEM, question, temperature=temperature, caller="agent.native.reflection.generate")
    steps.append(
        AgentStepData(
            agent="生成 Agent",
            role="第 1 轮初稿",
            input=question,
            output=draft,
        )
    )

    for round_num in range(1, REFLECTION_MAX_ROUNDS + 1):
        review = _ask(
            REVIEW_SYSTEM,
            f"用户问题：{question}\n\n草稿：\n{draft}",
            temperature=min(temperature, 0.3),
            caller=f"agent.native.reflection.review.{round_num}",
        )
        steps.append(
            AgentStepData(
                agent="评审 Agent",
                role=f"第 {round_num} 轮评审",
                input=draft,
                output=review,
            )
        )

        score = parse_reflection_score(review)
        if score >= REFLECTION_PASS_SCORE or round_num == REFLECTION_MAX_ROUNDS:
            steps.append(
                AgentStepData(
                    agent="最终输出",
                    role="评审通过" if score >= REFLECTION_PASS_SCORE else "达到最大轮次",
                    input=review,
                    output=draft,
                    meta=f"评分 {score}/10",
                )
            )
            return steps, draft

        revise_input = f"用户问题：{question}\n\n当前草稿：\n{draft}\n\n评审意见：\n{review}"
        old_draft = draft
        draft = _ask(
            REVISE_SYSTEM,
            revise_input,
            temperature=temperature,
            caller=f"agent.native.reflection.revise.{round_num}",
        )
        steps.append(
            AgentStepData(
                agent="修订 Agent",
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


def run_agent_native(mode: AgentMode, question: str, *, temperature: float) -> tuple[list[AgentStepData], str]:
    text = question.strip()
    if not text:
        raise HTTPException(status_code=400, detail="问题不能为空")
    runner = _RUNNERS.get(mode)
    if runner is None:
        raise HTTPException(status_code=400, detail=f"不支持的 mode: {mode}")
    return runner(text, temperature=temperature)
