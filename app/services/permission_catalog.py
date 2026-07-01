"""菜单与接口权限目录（前后端对齐的唯一来源）。"""

from typing import Literal

PermType = Literal["menu", "api"]

# menu: code, name, parent_code, route_path, icon
MENU_PERMISSIONS: list[tuple[str, str, str | None, str | None, str | None]] = [
    ("0", "系统首页", None, "/dashboard", "Odometer"),
    ("1", "系统管理", None, "1", "HomeFilled"),
    ("11", "用户管理", "1", "/system-user", None),
    ("12", "角色管理", "1", "/system-role", None),
    ("13", "菜单管理", "1", "/system-menu", None),
    ("90", "LLM 用量", "1", "/system-llm-usage", None),
    ("8", "业务演示", None, "8", "DataAnalysis"),
    ("80", "AI 资讯导航", "8", "/demo-ai-news", None),
    ("81", "投诉归类演示", "8", "/demo-complaints", None),
    ("82", "RAG 检索演示", "8", "/demo-rag", None),
    ("83", "AI训练提问", "8", "/demo-ai-chat", None),
    ("84", "Agent 展示", "8", "/demo-agent", None),
    ("85", "会议整理", "8", "/demo-meeting", None),
    ("86", "智能路由", "8", "/demo-smart-route", None),
    ("87", "人脸打卡", "8", "/demo-attendance", None),
    ("88", "COBOL to Java", "8", "/demo-cobol-migrate", None),
    ("89", "炸金花", "8", "/demo-zha-jinhua", None),
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

# api: menu_code, api_id, name, method, path
API_PERMISSIONS: list[tuple[str, str, str, str, str]] = [
    # 用户管理
    ("11", "list", "用户列表", "GET", "/users/"),
    ("11", "create", "创建用户", "POST", "/users/"),
    ("11", "update", "更新用户", "PUT", "/users/{user_id}"),
    ("11", "delete", "删除用户", "DELETE", "/users/{user_id}"),
    # 角色管理
    ("12", "list", "角色列表", "GET", "/roles/"),
    ("12", "create", "创建角色", "POST", "/roles/"),
    ("12", "update", "更新角色", "PUT", "/roles/{role_id}"),
    ("12", "permissions", "分配权限", "PUT", "/roles/{role_id}/permissions"),
    ("12", "delete", "删除角色", "DELETE", "/roles/{role_id}"),
    # 菜单管理
    ("13", "list", "菜单列表", "GET", "/menus/"),
    ("13", "create", "创建菜单", "POST", "/menus/"),
    ("13", "update", "更新菜单", "PUT", "/menus/{code}"),
    ("13", "delete", "删除菜单", "DELETE", "/menus/{code}"),
    # 投诉归类
    ("81", "init-categories", "初始化分类", "POST", "/complaints/init-categories"),
    ("81", "seed", "造数", "POST", "/complaints/seed"),
    ("81", "embed", "向量化", "POST", "/complaints/embed"),
    ("81", "classify", "执行归类", "POST", "/complaints/classify"),
    ("81", "stats", "多维统计", "GET", "/complaints/stats"),
    ("81", "samples", "样本列表", "GET", "/complaints/samples"),
    ("81", "create", "新增投诉", "POST", "/complaints"),
    ("81", "categories", "分类列表", "GET", "/complaints/categories"),
    ("81", "settings", "归类设置", "GET", "/complaints/settings"),
    ("81", "settings", "归类设置", "PUT", "/complaints/settings"),
    # RAG
    ("82", "import", "导入文档", "POST", "/documents/import"),
    ("82", "listByFile", "按文件名查", "GET", "/documents/listByFile"),
    ("82", "search", "向量检索", "GET", "/documents/search"),
    ("82", "search-and-llm", "搜索+LLM", "GET", "/documents/search_and_llm"),
    ("82", "chunks-create", "新增切块", "POST", "/documents/chunks"),
    ("82", "chunks-update", "更新切块", "PUT", "/documents/chunks/{chunk_id}"),
    ("82", "chunks-delete", "删除切块", "DELETE", "/documents/chunks/{chunk_id}"),
    # AI 提问
    ("83", "ask", "AI 提问", "POST", "/chat/ask"),
    # Agent
    ("84", "run", "运行 Agent", "POST", "/my_agent/run"),
    # 会议
    ("85", "organize", "会议整理", "POST", "/meeting/organize"),
    # 智能路由
    ("86", "dispatch", "智能分发", "POST", "/smart-route/dispatch"),
    # 人脸打卡
    ("87", "punch", "人脸打卡", "POST", "/attendance/punch"),
    ("87", "punches", "打卡历史", "GET", "/attendance/punches"),
    ("87", "persons", "已登记人员", "GET", "/attendance/persons"),
    ("87", "person-photo", "人员照片", "GET", "/attendance/persons/{user_id}/photo"),
    ("87", "punch-delete", "删除打卡", "DELETE", "/attendance/punches/{punch_id}"),
    ("87", "person-delete", "删除人员", "DELETE", "/attendance/persons/{person_id}"),
    # COBOL → Java 迁移示范
    ("88", "run", "执行迁移步骤", "POST", "/cobol_migrate/step/{step}"),
    ("88", "pipeline", "一键全流程", "POST", "/cobol_migrate/pipeline"),
    # 炸金花
    ("89", "start", "开始一局", "POST", "/game/start"),
    ("89", "next-round", "下一局", "POST", "/game/next-round"),
    ("89", "reset", "重置游戏", "POST", "/game/reset"),
    ("89", "turn", "玩家出牌", "POST", "/game/turn/{player_id}"),
    ("89", "referee", "裁判解说", "GET", "/game/referee"),
    ("89", "status", "牌局状态", "GET", "/game/status"),
    ("89", "access", "开启/关闭游戏", "POST", "/game/access"),
    # 功能介绍（演示页共用）
    ("8", "feature-intros-list", "功能介绍列表", "GET", "/feature-intros/"),
    ("8", "feature-intros-upsert", "保存功能介绍", "PUT", "/feature-intros/{page_key}/{section_key}"),
    ("8", "feature-intros-seed", "初始化功能介绍", "POST", "/feature-intros/seed"),
    # LLM 用量统计（管理员）
    ("90", "stats", "用量统计", "GET", "/llm-usage/stats"),
    ("90", "recent", "最近调用", "GET", "/llm-usage/recent"),
]

MENU_CODES = [code for code, *_ in MENU_PERMISSIONS]
API_CODES = [f"{menu}.{api_id}" for menu, api_id, *_ in API_PERMISSIONS]
ALL_PERMISSION_CODES = MENU_CODES + API_CODES

# 路由 -> 权限码，供 require_api 使用
ROUTE_PERMISSION_MAP: dict[tuple[str, str], str] = {
    (method.upper(), path): f"{menu}.{api_id}" for menu, api_id, _, method, path in API_PERMISSIONS
}

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
    "7",
    "6",
    "61",
    "62",
    "63",
    "64",
    "65",
    "66",
]

USER_MENU_PERMISSIONS = ["0", "8", "80", "81", "82", "83", "84", "85", "86", "87", "88", "89"]

# 仅管理员角色分配的 API 权限（普通用户即使有菜单 89 也不包含）
ADMIN_ONLY_API_CODES = frozenset({"89.access", "90.stats", "90.recent"})


def api_codes_for_menus(menu_codes: list[str]) -> list[str]:
    menus = set(menu_codes)
    return [code for code in API_CODES if code.split(".", 1)[0] in menus]


def default_permissions_for_menus(
    menu_codes: list[str],
    *,
    include_admin_only_apis: bool = False,
) -> list[str]:
    apis = api_codes_for_menus(menu_codes)
    if not include_admin_only_apis:
        apis = [code for code in apis if code not in ADMIN_ONLY_API_CODES]
    return sorted(set(menu_codes) | set(apis))
