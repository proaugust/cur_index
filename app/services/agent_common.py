import ast
import operator
import re
from dataclasses import dataclass
from typing import Literal

import httpx

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

ROUTING_ANSWER_WITH_TOOL_SYSTEM = (
    "你是 AI 助手。若提供了「工具查询结果」，必须基于该结果作答，不要编造天气数据。"
    "用简洁清晰的中文直接回答用户。"
)

CALC_TRIGGER = re.compile(r"等于多少|是多少|计算一下|算一下|多少")
WEATHER_TRIGGER = re.compile(r"天气|气温|温度|下雨|晴天|刮风|预报")
DEFAULT_WEATHER_CITY = "Tokyo"

_CITY_ALIASES: dict[str, str] = {
    "东京": "Tokyo",
    "大阪": "Osaka",
    "大版": "Osaka",
    "京都": "Kyoto",
    "名古屋": "Nagoya",
    "横滨": "Yokohama",
    "北京": "Beijing",
    "上海": "Shanghai",
    "广州": "Guangzhou",
    "深圳": "Shenzhen",
    "杭州": "Hangzhou",
    "成都": "Chengdu",
    "纽约": "New York",
    "伦敦": "London",
    "巴黎": "Paris",
    "悉尼": "Sydney",
}
_WEATHER_CITY_STOPWORDS = frozenset({"今天", "明天", "后天", "这里", "当地", "本地", "现在", "本周", "这周"})
_CITY_WEATHER_PATTERNS = (
    re.compile(r"(?:今天|明天|后天)(.+?)的?天气"),
    re.compile(r"(.+?)的?(?:今天|明天|后天)?天气"),
    re.compile(r"查(?:一下)?(.+?)的?天气"),
    re.compile(r"(.+?)的?(?:气温|温度|预报)"),
)

_WMO_WEATHER: dict[int, str] = {
    0: "晴空",
    1: "大部晴朗",
    2: "局部多云",
    3: "多云",
    45: "有雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "中毛毛雨",
    55: "大毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    80: "小阵雨",
    81: "中阵雨",
    82: "大阵雨",
    95: "雷暴",
}
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


def detect_weather_tool(question: str) -> bool:
    return bool(WEATHER_TRIGGER.search(question))


def _normalize_city_query(raw: str) -> str:
    city = raw.strip()
    return _CITY_ALIASES.get(city, city)


def extract_weather_city(question: str) -> str:
    """从问题中提取城市名；未识别时默认东京。"""
    if not detect_weather_tool(question):
        return DEFAULT_WEATHER_CITY

    for pattern in _CITY_WEATHER_PATTERNS:
        match = pattern.search(question)
        if not match:
            continue
        raw_city = match.group(1).strip()
        if raw_city and raw_city not in _WEATHER_CITY_STOPWORDS:
            return _normalize_city_query(raw_city)
    return DEFAULT_WEATHER_CITY


def _geocode_city(city_query: str) -> tuple[float, float, str, str]:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city_query, "count": 1, "language": "zh"},
        )
        response.raise_for_status()
        data = response.json()

    results = data.get("results") or []
    if not results:
        raise ValueError(f"未找到城市：{city_query}")

    place = results[0]
    return (
        float(place["latitude"]),
        float(place["longitude"]),
        str(place.get("name") or city_query),
        str(place.get("timezone") or "auto"),
    )


def _wmo_weather_label(code: int | None) -> str:
    if code is None:
        return "未知"
    return _WMO_WEATHER.get(code, "多变")


def run_weather_tool(city: str = DEFAULT_WEATHER_CITY) -> str:
    """调用 Open-Meteo 按城市查询实时天气。"""
    city_query = _normalize_city_query(city.strip()) if city.strip() else DEFAULT_WEATHER_CITY
    try:
        latitude, longitude, city_label, timezone = _geocode_city(city_query)
    except (httpx.HTTPError, ValueError) as exc:
        return f"{city_query} 天气查询失败：{exc}"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "timezone": timezone,
        "wind_speed_unit": "kmh",
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get("https://api.open-meteo.com/v1/forecast", params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        return f"{city_label}天气查询失败：{exc}"

    current = data.get("current") or {}
    temp = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    weather_code = current.get("weather_code")
    wind = current.get("wind_speed_10m")
    desc = _wmo_weather_label(weather_code if isinstance(weather_code, int) else None)

    parts = [city_label]
    if temp is not None:
        parts.append(f"当前 {temp}°C")
    parts.append(desc)
    if humidity is not None:
        parts.append(f"湿度 {humidity}%")
    if wind is not None:
        parts.append(f"风速 {wind} km/h")
    return "，".join(parts)


def build_routing_user_prompt(question: str, tool_output: str) -> str:
    return f"工具查询结果：{tool_output}\n\n用户问题：{question}"


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
