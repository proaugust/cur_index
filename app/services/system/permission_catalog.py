"""内置菜单目录与默认角色权限策略。"""

# menu: code, name, parent_code, route_path, icon
MENU_PERMISSIONS: list[tuple[str, str, str | None, str | None, str | None]] = [
    ("0", "系统首页", None, "/dashboard", "Odometer"),
    ("1", "系统管理", None, "1", "HomeFilled"),
    ("11", "用户管理", "1", "/system-user", None),
    ("12", "角色管理", "1", "/system-role", None),
    ("13", "菜单管理", "1", "/system-menu", None),
    ("8", "业务演示", None, "8", "DataAnalysis"),
    ("90", "LLM 用量", "8", "/system-llm-usage", None),
    ("80", "AI 资讯导航", "8", "/demo-ai-news", None),
    ("81", "投诉归类演示", "8", "/demo-complaints", None),
    ("82", "RAG 检索演示", "8", "/demo-rag", None),
    ("83", "AI训练提问", "8", "/demo-ai-chat", None),
    ("84", "Agent 展示", "8", "/demo-agent", None),
    ("85", "会议整理", "8", "/demo-meeting", None),
    ("86", "智能路由", "8", "/demo-smart-route", None),
    ("87", "人脸打卡", "8", "/demo-attendance", None),
    ("88", "COBOL to Java", "8", "/demo-cobol-migrate", None),
    ("89", "炸金花", "8", "/modules-zha-jinhua", None),
    ("91", "Customer Insight AI Platform", "8", "/modules-insight", None),
    ("7", "主题设置", None, "/theme", "Brush"),
    ("6", "附加页面", None, "6", "DocumentAdd"),
    ("61", "个人中心", "6", "/ucenter", None),
    ("62", "登录", "6", "/login", None),
    ("63", "注册", "6", "/register", None),
    ("64", "重置密码", "6", "/reset-pwd", None),
    ("65", "403", "6", "/403", None),
    ("66", "404", "6", "/404", None),
    ("2", "组件", None, "2", None),
    ("21", "表单", "2", "/form", None),
    ("22", "上传", "2", "/upload", None),
    ("23", "统计", "2", "/icon", None),
    ("24", "富文本", "2", "/editor", None),
    ("25", "Markdown", "2", "/markdown", None),
    ("26", "轮播", "2", "/carousel", None),
    ("27", "树", "2", "/tree", None),
    ("28", "图标", "2", "/icon", None),
    ("3", "表格", None, "3", None),
    ("31", "基础表格", "3", "/table", None),
    ("32", "可编辑表格", "3", "/table-editor", None),
    ("33", "导入Excel", "3", "/import", None),
    ("34", "导出Excel", "3", "/export", None),
    ("4", "图表", None, "4", None),
    ("41", "Schart", "4", "/schart", None),
    ("42", "Echarts", "4", "/echarts", None),
    ("5", "图标", None, "/icon", None),
    ("291", "图标 291", "2", "/icon", None),
    ("292", "图标 292", "2", "/icon", None),
]

MENU_CODES = [code for code, *_ in MENU_PERMISSIONS]

SUPER_ADMIN_MENU_PERMISSIONS = MENU_CODES

ADMIN_MENU_PERMISSIONS = [
    "0",
    "1",
    "11",
    "12",
    "13",
    "90",
    "8",
    "80",
    "81",
    "82",
    "83",
    "84",
    "85",
    "86",
    "87",
    "88",
    "89",
    "91",
    "7",
    "6",
    "61",
    "62",
    "63",
    "64",
    "65",
    "66",
]

USER_MENU_PERMISSIONS = ["0", "8", "90", "80", "81", "82", "83", "84", "85", "86", "87", "88", "89", "91"]

# 仅管理员角色分配的 API 权限（普通用户即使有菜单 89 也不包含）
ADMIN_ONLY_API_CODES = frozenset({"89.access"})


def api_codes_for_menus(menu_codes: list[str], api_codes: list[str]) -> list[str]:
    menus = set(menu_codes)
    return [code for code in api_codes if code.split(".", 1)[0] in menus]


def default_permissions_for_menus(
    menu_codes: list[str],
    api_codes: list[str],
    *,
    include_admin_only_apis: bool = False,
) -> list[str]:
    apis = api_codes_for_menus(menu_codes, api_codes)
    if not include_admin_only_apis:
        apis = [code for code in apis if code not in ADMIN_ONLY_API_CODES]
    return sorted(set(menu_codes) | set(apis))
