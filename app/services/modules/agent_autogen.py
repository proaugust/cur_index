"""AutoGen 风格示意：Assistant ↔ Critic 两轮对话（未引入 AutoGen SDK）。"""

from app.services.modules.agent_common import AgentStepData
from app.services.shared.llm import chat_completion

ASSISTANT_SYS = "你是 AutoGen Assistant。针对用户问题给出简洁初稿，用中文。"
CRITIC_SYS = "你是 AutoGen Critic。指出初稿的 1-2 个问题，用中文，不要重写全文。"
REVISE_SYS = "你是 AutoGen Assistant。根据评审意见修订初稿，输出最终答复，用中文。"


def _ask(system_prompt: str, user_prompt: str, *, temperature: float, caller: str) -> str:
    return chat_completion(system_prompt, user_prompt, temperature=temperature, caller=caller)


def run_agent_autogen(question: str, *, temperature: float) -> tuple[list[AgentStepData], str]:
    steps: list[AgentStepData] = []
    draft = _ask(ASSISTANT_SYS, question, temperature=temperature, caller="agent.autogen.draft")
    steps.append(
        AgentStepData(agent="Assistant", role="生成初稿", input=question, output=draft, meta="autogen:round1")
    )
    critique = _ask(
        CRITIC_SYS,
        f"用户问题：{question}\n\n初稿：{draft}",
        temperature=min(temperature, 0.3),
        caller="agent.autogen.critic",
    )
    steps.append(
        AgentStepData(agent="Critic", role="评审初稿", input=draft, output=critique, meta="autogen:critic")
    )
    answer = _ask(
        REVISE_SYS,
        f"用户问题：{question}\n\n初稿：{draft}\n\n评审：{critique}",
        temperature=temperature,
        caller="agent.autogen.revise",
    )
    steps.append(
        AgentStepData(agent="Assistant", role="按评审修订", input=critique, output=answer, meta="autogen:round2")
    )
    return steps, answer
