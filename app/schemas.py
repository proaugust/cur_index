from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_serializer


def _as_utc_aware(value: datetime) -> datetime:
    """DB 中 naive datetime 按 UTC 存储，序列化时补上时区供前端正确转本地时间。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ItemBase(BaseModel):
    title: str


class ItemCreate(ItemBase):
    pass


class ItemRead(ItemBase):
    id: int

    model_config = {"from_attributes": True}


class DocumentImportResult(BaseModel):
    source_file: str
    sections: int
    chunks: int


class DocumentChunkRead(BaseModel):
    id: int
    source_file: str
    section_title: str
    section_path: str
    chunk_index: int
    content: str
    char_count: int

    model_config = {"from_attributes": True}


class DocumentChunkCreate(BaseModel):
    source_file: str = Field(min_length=1, description="来源文件名")
    content: str = Field(min_length=1, description="切块正文，入库时自动计算向量")
    section_title: str = Field(default="", description="章节标题")
    section_path: str = Field(default="", description="章节路径")
    chunk_index: int | None = Field(default=None, ge=0, description="块序号；留空则在该文件下自动取 max+1")


class DocumentChunkUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, description="切块正文，更新后自动重算向量")
    section_title: str | None = Field(default=None, description="章节标题")
    section_path: str | None = Field(default=None, description="章节路径")


class DocumentChunkSearchResult(DocumentChunkRead):
    similarity: float


class DocumentSearchPolishedSource(BaseModel):
    snippet_index: int = Field(description="片段编号，与 polished_answer 中〔片段N〕对应")
    id: int = Field(description="document_chunks 表主键")
    source_file: str = Field(description="原始文件名")
    source_label: str = Field(description="来源展示名：文件名 + 章节")
    section_title: str
    section_path: str
    chunk_index: int
    content: str = Field(description="数据库中的原始文本片段")
    char_count: int
    similarity: float = Field(description="与查询的向量相似度，越高越相关")

    model_config = {"from_attributes": True}


class DocumentSearchPolishedResult(BaseModel):
    query: str
    polished_answer: str = Field(description="大模型综合所有片段后生成的丰富回答（Markdown）")
    source_count: int = Field(description="参与润色的原始片段数量")
    original_sources: list[DocumentSearchPolishedSource] = Field(description="检索到的原始资料，供前端展示出处与原文对照")


class DocumentAnalyzeRequest(BaseModel):
    source_files: list[str] | None = Field(default=None, description="要分析的文档文件名列表；为空则分析库中全部文档")
    report_type: Literal["risk", "summary"] = Field(default="risk", description="risk=风险分析报告，summary=多文档综合摘要")
    topic: str | None = Field(default=None, description="可选关注点，如「供应链合规」「数据安全」")
    chunks_per_query: int = Field(default=5, ge=1, le=20, description="每条检索 query 取 top-k 片段")


class DocumentRiskItem(BaseModel):
    title: str = Field(description="风险项标题")
    severity: Literal["高", "中", "低"] = Field(description="风险等级")
    description: str = Field(description="风险说明")
    source_file: str = Field(description="主要来源文档")
    snippet_indices: list[int] = Field(default_factory=list, description="依据片段编号，与 original_sources 中 snippet_index 对应")


class DocumentAnalyzeResult(BaseModel):
    report_type: str
    source_files: list[str] = Field(description="实际参与分析的文档列表")
    topic: str | None
    report_markdown: str = Field(description="完整分析报告（Markdown）")
    risks: list[DocumentRiskItem] = Field(default_factory=list, description="结构化风险清单，仅 report_type=risk 时有值")
    source_count: int
    original_sources: list[DocumentSearchPolishedSource] = Field(description="分析过程中检索到的全部原始片段")


class ComplaintCategoryRead(BaseModel):
    id: int
    name: str
    description: str
    seed_phrases: str

    model_config = {"from_attributes": True}


class ComplaintCategoryDetail(BaseModel):
    id: int
    name: str
    description: str
    seed_phrases: list[str] = Field(description="种子句列表")
    complaint_count: int = Field(description="该类型下投诉条数")
    has_embedding: bool = Field(description="是否已向量化")


class ComplaintRead(BaseModel):
    id: int
    complaint_text: str
    address: str | None = None
    complaint_time: datetime | None = None
    category_id: int | None
    category_name: str | None = None
    similarity: float | None

    model_config = {"from_attributes": True}


class ComplaintCreate(BaseModel):
    complaint_text: str = Field(min_length=5, max_length=2000, description="投诉正文")
    address: str | None = Field(default=None, max_length=100, description="地区")
    complaint_time: datetime | None = Field(default=None, description="投诉时间，默认当前时间")


class ComplaintCategoryScore(BaseModel):
    category_id: int
    category_name: str
    similarity: float


class ComplaintCreateResult(BaseModel):
    complaint: ComplaintRead
    category_created: bool = Field(description="是否新建了投诉类型")
    assigned_category_id: int | None = None
    assigned_category_name: str | None = None
    similarity: float | None = Field(description="与最终归类的相似度")
    category_scores: list[ComplaintCategoryScore] = Field(description="与各类别相似度排行，供图表展示")


class ComplaintSamplesPage(BaseModel):
    items: list[ComplaintRead]
    total: int
    page: int
    page_size: int


class ComplaintStatsDimension(BaseModel):
    key: Literal["category", "address", "time"]
    field: str
    label: str
    group_by: str


class ComplaintStatsCountItem(BaseModel):
    label: str
    count: int
    percentage: float


class ComplaintStatsFilters(BaseModel):
    time_from: date | None = None
    time_to: date | None = None
    category_name: str | None = None
    address: str | None = None


class ComplaintStatsParsedQuery(BaseModel):
    intent: Literal["stats", "samples"] = "stats"
    filters: ComplaintStatsFilters
    group_by: Literal["address", "category", "day"] | None = None
    rank: Literal["max", "min"] = "max"
    limit: int = Field(default=5, ge=1, le=20)
    original_question: str = ""


class ComplaintStatsReport(BaseModel):
    total: int
    classified: int
    unclassified: int
    dimensions: list[ComplaintStatsDimension]
    by_category: list[ComplaintStatsCountItem]
    by_address: list[ComplaintStatsCountItem]
    by_time: list[ComplaintStatsCountItem]
    parsed_query: ComplaintStatsParsedQuery | None = None
    total_in_scope: int | None = Field(default=None, description="当前过滤条件下投诉总数")
    ranked: list[ComplaintStatsCountItem] = Field(default_factory=list, description="自然语言聚合排行结果")
    data_time_from: date | None = Field(default=None, description="库内投诉最早日期")
    data_time_to: date | None = Field(default=None, description="库内投诉最晚日期")


class ComplaintSeedResult(BaseModel):
    inserted: int


class ComplaintEmbedResult(BaseModel):
    embedded: int
    skipped: int


class ComplaintClassifyCategoryCount(BaseModel):
    category_name: str
    count: int
    percentage: float


class ComplaintClassifyResult(BaseModel):
    classified: int
    by_category: list[ComplaintClassifyCategoryCount]


class ComplaintSettings(BaseModel):
    classify_threshold: float = Field(ge=0.0, le=1.0, description="投诉向量归类阈值，≥ 此值归入已有类")


class ComplaintSettingsUpdate(BaseModel):
    classify_threshold: float = Field(ge=0.0, le=1.0, description="投诉向量归类阈值")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatAskRequest(BaseModel):
    question: str = Field(min_length=1, description="用户提问")
    system_prompt: str | None = Field(default=None, description="训练/系统提示词")
    history: list[ChatMessage] = Field(default_factory=list, description="多轮对话历史")
    temperature: float = Field(default=0.7, ge=0, le=2)


class ChatAskResponse(BaseModel):
    question: str
    answer: str


class MeetingOrganizeRequest(BaseModel):
    text: str = Field(min_length=1, description="待整理的杂乱会议记录或口述文字")
    style: Literal["concise", "formal"] = Field(
        default="formal",
        description="整理风格：concise 精简版，formal 正规版",
    )
    temperature: float = Field(default=0.3, ge=0, le=2)


class MeetingOrganizeResponse(BaseModel):
    original_text: str
    organized_text: str = Field(description="整理后的结构化会议纪要（Markdown）")


class SmartRouteRequest(BaseModel):
    question: str = Field(min_length=1, description="用户一句话提问")


class SmartRouteEmployee(BaseModel):
    user_id: str
    created_at: datetime
    punch_count: int = 0
    has_reference_image: bool = False
    photo_url: str | None = None
    last_punch_at: datetime | None = None

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> datetime:
        return _as_utc_aware(value)

    @field_serializer("last_punch_at")
    def serialize_last_punch_at(self, value: datetime | None) -> datetime | None:
        return _as_utc_aware(value) if value is not None else None


class SmartRouteResponse(BaseModel):
    question: str
    intent: Literal["weather", "employee", "email", "unknown"]
    message: str = Field(description="路由展示文案，如：调用了天气查询接口")
    employees: list[SmartRouteEmployee] = Field(default_factory=list, description="员工查询结果")


class EmployeeProfileRead(BaseModel):
    user_id: str
    created_at: datetime
    punch_count: int = 0
    has_reference_image: bool = False
    last_punch_at: datetime | None = None

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> datetime:
        return _as_utc_aware(value)

    @field_serializer("last_punch_at")
    def serialize_last_punch_at(self, value: datetime | None) -> datetime | None:
        return _as_utc_aware(value) if value is not None else None


AgentMode = Literal["single", "sequential", "routing", "reflection"]
AgentEngine = Literal["native", "langchain"]
AgentStepStatus = Literal["pending", "running", "done", "error"]


class AgentStep(BaseModel):
    agent: str
    role: str
    input: str
    output: str = ""
    status: AgentStepStatus = "done"
    meta: str | None = None


class AgentRunRequest(BaseModel):
    question: str = Field(min_length=1, description="用户提问")
    mode: AgentMode = Field(description="Agent 模式：single / sequential / routing / reflection")
    engine: AgentEngine = Field(default="native", description="执行引擎：native 原生编排 / langchain")
    temperature: float = Field(default=0.7, ge=0, le=2)


class AgentRunResponse(BaseModel):
    question: str
    mode: AgentMode
    engine: AgentEngine
    steps: list[AgentStep]
    answer: str = Field(description="最终答复")


class CobolMigrateStepResponse(BaseModel):
    step: int = Field(ge=1, le=7)
    step_name: str
    steps: list[AgentStep]
    payload: dict = Field(default_factory=dict)


class CobolMigratePipelineResponse(BaseModel):
    results: list[CobolMigrateStepResponse]


class AttendancePunchRequest(BaseModel):
    descriptor: list[float] = Field(min_length=128, max_length=128, description="face-api 128 维人脸特征向量")
    match_threshold: float = Field(default=0.55, ge=0.3, le=0.9, description="人脸匹配阈值，越小越严格")
    face_image: str | None = Field(default=None, description="裁切后的人脸 JPEG base64")
    face_score: float | None = Field(default=None, ge=0, description="人脸质量分，越高越适合作为标准照")
    dedup_enabled: bool = Field(default=True, description="同一人短时重复刷脸是否跳过记新记录")
    dedup_seconds: float = Field(default=2.0, ge=0.5, le=30, description="去重时间窗口（秒）")


class AttendancePunchResponse(BaseModel):
    user_id: str
    punched_at: datetime
    is_new_person: bool
    match_distance: float | None = Field(default=None, description="与已登记人脸的匹配距离，新人时为 null")
    reference_image_updated: bool = Field(default=False, description="本次是否更新标准照")
    punch_skipped: bool = Field(default=False, description="因去重跳过新增打卡记录")

    @field_serializer("punched_at")
    def serialize_punched_at(self, value: datetime) -> datetime:
        return _as_utc_aware(value)


class AttendancePunchRead(BaseModel):
    id: int
    user_id: str
    punched_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("punched_at")
    def serialize_punched_at(self, value: datetime) -> datetime:
        return _as_utc_aware(value)


class AttendancePunchesPage(BaseModel):
    items: list[AttendancePunchRead]
    total: int
    page: int
    page_size: int


class FeatureIntroRead(BaseModel):
    page_key: str
    section_key: str
    title: str
    content: str
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("updated_at")
    def serialize_updated_at(self, value: datetime) -> datetime:
        return _as_utc_aware(value)


class FeatureIntroUpsert(BaseModel):
    title: str = ""
    content: str = ""


class AttendancePersonRead(BaseModel):
    id: int
    user_id: str
    created_at: datetime
    punch_count: int = 0
    has_reference_image: bool = False

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> datetime:
        return _as_utc_aware(value)


class ZhaJinhuaPotEntry(BaseModel):
    step: int
    player_id: str
    display_name: str
    amount: int
    reason: str
    pot_after: int = 0
    line_stake: int = 0


class ZhaJinhuaPotPlayerTotal(BaseModel):
    player_id: str
    display_name: str
    total: int


class ZhaJinhuaPotLedgerRow(BaseModel):
    step: int
    player_id: str
    display_name: str
    amount: int
    display_amount: int | None = None
    reason: str
    line_stake: int = 0
    pool_running: int = 0
    player_running: int = 0
    action_kind: str = "default"
    bet_kind: str = ""
    all_in: bool = False
    at_line: bool = False


class ZhaJinhuaPotView(BaseModel):
    total: int = 0
    player_totals: list[ZhaJinhuaPotPlayerTotal] = []
    rows: list[ZhaJinhuaPotLedgerRow] = []


class ZhaJinhuaStartResponse(BaseModel):
    message: str
    state: "ZhaJinhuaStatusResponse"


class ZhaJinhuaMessageResponse(BaseModel):
    message: str


class ZhaJinhuaTurnResponse(BaseModel):
    player_id: str
    display_name: str
    skipped: bool = False
    reason: str = ""
    thought: str = ""
    action: str = ""
    amount: int = 0
    bet_tag: str = ""
    target: str = ""
    state: "ZhaJinhuaStatusResponse"


class ZhaJinhuaRefereeResponse(BaseModel):
    referee_voice: str


class ZhaJinhuaAccessRequest(BaseModel):
    enabled: bool


class ZhaJinhuaAccessResponse(BaseModel):
    enabled: bool
    message: str


class ZhaJinhuaPlayerStatus(BaseModel):
    display_name: str
    balance: int
    has_looked: bool
    alive: bool
    all_in: bool = False
    forced_all_in: bool = False
    cards: list[str]
    cards_display: str = ""
    hand_label: str = ""
    session_pnl: int = 0


class ZhaJinhuaSettlementPlayer(BaseModel):
    display_name: str
    cards: list[str]
    cards_display: str
    hand_label: str
    round_pnl: int
    balance: int
    session_pnl: int
    alive: bool


class ZhaJinhuaSettlement(BaseModel):
    winner_id: str
    winner_name: str
    pot_total: int
    winner_net_win: int
    pot_ledger: list[ZhaJinhuaPotEntry] = []
    players: dict[str, ZhaJinhuaSettlementPlayer]


class ZhaJinhuaStatusResponse(BaseModel):
    round: int
    max_rounds: int
    pot: int
    current_bet: int
    phase: str
    early_showdown: bool = False
    game_enabled: bool = False
    last_winner: str | None
    last_winner_name: str | None = None
    current_player_id: str | None = None
    actions_this_round: int = 0
    max_actions_per_round: int = 24
    last_settlement: ZhaJinhuaSettlement | None = None
    pot_ledger: list[ZhaJinhuaPotEntry] = []
    pot_view: ZhaJinhuaPotView | None = None
    players: dict[str, ZhaJinhuaPlayerStatus]


class LlmUsageCallerStats(BaseModel):
    caller: str
    calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    share_percent: float


class LlmUsageUserStats(BaseModel):
    user_id: int | None
    username: str
    calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    share_percent: float


class LlmUsageStatsResponse(BaseModel):
    days: int | None = None
    total_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    by_caller: list[LlmUsageCallerStats]
    by_user: list[LlmUsageUserStats]


class LlmUsageLogItem(BaseModel):
    id: int
    caller: str
    engine: str
    model: str
    request_id: str | None
    user_id: int | None
    username: str | None = None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    success: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> datetime:
        return _as_utc_aware(value)


class LlmUsageRecentResponse(BaseModel):
    items: list[LlmUsageLogItem]
    total: int
    page: int
    page_size: int


class AiNewsFavoriteRef(BaseModel):
    type: Literal["preset", "custom"]
    id: str


class AiNewsCustomLink(BaseModel):
    id: str
    url: str
    title: str
    icon: str
    letter: str
    color: str
    region: Literal["international", "domestic"] | None = None


class AiNewsUserPrefsBody(BaseModel):
    hiddenPresetIds: list[str] = Field(default_factory=list)
    customLinks: list[AiNewsCustomLink] = Field(default_factory=list)
    favorites: list[AiNewsFavoriteRef] = Field(default_factory=list)
    presetColumns: dict[str, Literal["international", "domestic"]] = Field(default_factory=dict)
    internationalOrder: list[str] = Field(default_factory=list)
    domesticOrder: list[str] = Field(default_factory=list)


class AiNewsUserPrefsRead(AiNewsUserPrefsBody):
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
