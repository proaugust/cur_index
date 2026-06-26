import ast
import operator
import re
from dataclasses import dataclass
from typing import Literal

AgentMode = Literal["single", "sequential", "routing", "reflection"]
AgentEngine = Literal["native", "langchain"]
AgentStepStatus = Literal["pending", "running", "done", "error"]

REFLECTION_MAX_ROUNDS = 2
REFLECTION_PASS_SCORE = 8

SINGLE_SYSTEM = "你是一个 helpful 的 AI 助手，请用简洁清晰的中文回答用户问题。"

SINGLE_ANSWER_SYSTEM = (
    "你是 AI 助手。若提供了「工具计算结果」，必须基于该结果作答，不要自行重算。"
    "用简洁清晰的中文直接回答用户。"
)

CALC_TRIGGER = re.compile(r"等于多少|是多少|计算一下|算一下|多少")
CALC_EXPR = re.compile(r"([\d\.]+(?:\s*[\+\-\*\/\%]\s*[\d\.]+)+)")

_SAFE_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}
_SAFE_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}

SEQUENTIAL_AGENTS: list[dict[str, str]] = [
    {
        "name": "规划 Agent",
        "role": "拆解任务，列出 3 条执行要点",
        "prompt": "你是任务规划专家。针对用户问题，输出 3 条简洁的执行要点，每条一行，不要多余解释。",
    },
    {
        "name": "执行 Agent",
        "role": "根据规划要点生成详细内容",
        "prompt": "你是内容执行专家。根据「规划要点」和「原始问题」，生成完整、有条理的中文回答。",
    },
    {
        "name": "总结 Agent",
        "role": "润色压缩为最终答复",
        "prompt": "你是编辑专家。将「执行结果」精炼为面向用户的最终答复，保留关键信息，语言流畅。",
    },
]

ROUTE_SYSTEM = "你是路由分发器。分析用户问题，只输出一个词：技术、业务 或 通用。不要输出其他内容。"

SPECIALISTS: dict[str, dict[str, str]] = {
    "技术": {"name": "技术专家", "prompt": "你是资深技术专家，用专业但易懂的中文回答技术问题。"},
    "业务": {"name": "业务专家", "prompt": "你是业务分析专家，从业务流程和运营角度给出实用建议。"},
    "通用": {"name": "通用助手", "prompt": "你是通用 AI 助手，用简洁清晰的中文回答问题。"},
}

GENERATE_SYSTEM = "你是内容生成专家。针对用户问题给出初稿回答，简洁完整。"
REVIEW_SYSTEM = "你是严格评审员。对草稿打分（0-10）并给出 1-2 条改进建议。格式：评分：X\n建议：..."
REVISE_SYSTEM = "你是修订专家。根据评审意见改进草稿，输出修订后的完整回答。"


@dataclass
class AgentStepData:
    agent: str
    role: str
    input: str
    output: str = ""
    status: AgentStepStatus = "done"
    meta: str | None = None


def parse_route_category(raw: str) -> str:
    for key in ("技术", "业务", "通用"):
        if key in raw:
            return key
    return "通用"


def parse_reflection_score(review: str) -> int:
    match = re.search(r"(\d+)\s*分|评分[：:]\s*(\d+)", review)
    if match:
        return int(match.group(1) or match.group(2))
    return 6


def build_sequential_context(question: str, step_index: int, output: str, context: str) -> str:
    if step_index == 0:
        return f"{context}\n\n规划要点：\n{output}"
    return f"{context}\n\n执行结果：\n{output}"


def _safe_eval_math(expr: str) -> float | int:
    node = ast.parse(expr.replace(" ", ""), mode="eval").body

    def _eval(n: ast.AST) -> float | int:
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.UnaryOp) and type(n.op) in _SAFE_UNARY:
            return _SAFE_UNARY[type(n.op)](_eval(n.operand))  # type: ignore[operator]
        if isinstance(n, ast.BinOp) and type(n.op) in _SAFE_BINOPS:
            return _SAFE_BINOPS[type(n.op)](_eval(n.left), _eval(n.right))  # type: ignore[operator]
        raise ValueError("不支持的表达式")

    result = _eval(node)
    if isinstance(result, float) and result == int(result):
        return int(result)
    return result


def detect_calc_tool(question: str) -> str | None:
    if not CALC_TRIGGER.search(question):
        return None
    match = CALC_EXPR.search(question)
    if not match:
        return None
    return match.group(1).replace(" ", "")


def run_calc_tool(expr: str) -> str:
    try:
        result = _safe_eval_math(expr)
    except (SyntaxError, ValueError, ZeroDivisionError) as exc:
        return f"{expr} 计算失败：{exc}"
    return f"{expr} = {result}"


def prepare_single_run(question: str) -> tuple[list[AgentStepData], str, bool]:
    """准备单智能体步骤：可选 calc 工具 + 拼装给 LLM 的用户提示。"""
    steps: list[AgentStepData] = []
    expr = detect_calc_tool(question)
    tool_context = ""
    used_tool = False

    if expr:
        tool_output = run_calc_tool(expr)
        used_tool = True
        steps.append(
            AgentStepData(
                agent="工具 Agent",
                role="调用 calc 计算器",
                input=expr,
                output=tool_output,
                meta="builtin:calc",
            )
        )
        tool_context = f"工具计算结果：{tool_output}\n\n"

    user_prompt = f"{tool_context}用户问题：{question}"
    return steps, user_prompt, used_tool
