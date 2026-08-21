"""CrewAI 风格示意：研究员 → 执笔 顺序协作（未引入 CrewAI SDK）。"""

from app.services.modules.agent_common import AgentStepData
from app.services.shared.llm import chat_completion

RESEARCHER_SYS = "你是 Crew 研究员。针对任务列出 3 条要点，每条一行，用中文，不要写成文章。"
WRITER_SYS = "你是 Crew 执笔。根据研究员要点写成一段给管理层的简报，用中文，不超过 150 字。"


def _ask(system_prompt: str, user_prompt: str, *, temperature: float, caller: str) -> str:
    return chat_completion(system_prompt, user_prompt, temperature=temperature, caller=caller)


def run_agent_crewai(question: str, *, temperature: float) -> tuple[list[AgentStepData], str]:
    notes = _ask(RESEARCHER_SYS, question, temperature=temperature, caller="agent.crewai.research")
    answer = _ask(
        WRITER_SYS,
        f"任务：{question}\n\n要点：\n{notes}",
        temperature=temperature,
        caller="agent.crewai.write",
    )
    steps = [
        AgentStepData(agent="研究员", role="收集要点", input=question, output=notes, meta="crew:researcher"),
        AgentStepData(agent="执笔", role="写成简报", input=notes, output=answer, meta="crew:writer"),
    ]
    return steps, answer
