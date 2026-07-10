export type ParamType = 'string' | 'number' | 'boolean' | 'file' | 'json';

export interface ApiParam {
    name: string;
    label: string;
    type: ParamType;
    default?: string | number | boolean;
    placeholder?: string;
    min?: number;
    max?: number;
    step?: number;
    required?: boolean;
}

export interface ApiResultTableColumn {
    prop: string;
    label: string;
    width?: number;
    minWidth?: number;
    showOverflowTooltip?: boolean;
}

export interface ApiResultRowActions {
    /** 行主键字段，默认 id */
    idField?: string;
    updatePath: string;
    deletePath: string;
    createPath: string;
    /** 编辑弹窗字段（值从选中行预填） */
    editableFields: ApiParam[];
    /** 新增弹窗字段 */
    createFields: ApiParam[];
}

export interface ApiResultTableView {
    mode: 'table';
    /** 点分路径，如 original_sources；留空表示响应本身为数组 */
    dataPath?: string;
    /** 表格上方展示的文本字段 */
    highlightFields?: { key: string; label: string }[];
    columns: ApiResultTableColumn[];
    pageSize?: number;
    /** 选中行后可编辑 / 删除 / 新增 */
    rowActions?: ApiResultRowActions;
}

export interface ApiResultContentView {
    mode: 'content';
    /** 单独展示的响应正文字段 */
    contentField: string;
    contentLabel?: string;
}

export type ApiResultView = ApiResultTableView | ApiResultContentView;

export interface ApiQueryExample {
    label: string;
    query: Record<string, string | number>;
}

export interface ApiEndpoint {
    id: string;
    name: string;
    method: 'GET' | 'POST' | 'PUT' | 'DELETE';
    path: string;
    description?: string;
    pathParams?: ApiParam[];
    queryParams?: ApiParam[];
    bodyParams?: ApiParam[];
    formParams?: ApiParam[];
    resultView?: ApiResultView;
    /** 快捷填充 Query 参数示例 */
    queryExamples?: ApiQueryExample[];
}

export const complaintEndpoints: ApiEndpoint[] = [
    {
        id: 'init-categories',
        name: '初始化分类',
        method: 'POST',
        path: '/complaints/init-categories',
        description: '初始化 8 类电信投诉分类目录及向量',
    },
    {
        id: 'seed',
        name: '造数',
        method: 'POST',
        path: '/complaints/seed',
        description: '批量插入电信类模拟投诉（8类均分，complaint_text / address / complaint_time）',
        queryParams: [
            { name: 'count', label: '数量', type: 'number', default: 500, min: 1, max: 2000 },
        ],
    },
    {
        id: 'embed',
        name: '向量化',
        method: 'POST',
        path: '/complaints/embed',
        description: '对 embedding 为空的投诉按 complaint_text 生成 vector 并写入',
    },
    {
        id: 'classify',
        name: '执行归类',
        method: 'POST',
        path: '/complaints/classify',
        description: '对未归类投诉执行向量归类（相似度 ≥ 当前阈值），返回各类别数量与占比',
    },
    {
        id: 'settings',
        name: '归类设置',
        method: 'GET',
        path: '/complaints/settings',
        description: '获取投诉向量归类统一阈值（默认 0.65）',
    },
    {
        id: 'settings',
        name: '更新归类设置',
        method: 'PUT',
        path: '/complaints/settings',
        description: '更新投诉向量归类阈值，影响新增、造数、批量归类',
        formParams: [
            { name: 'classify_threshold', label: '归类阈值', type: 'number', default: 0.65, min: 0, max: 1 },
        ],
    },
    {
        id: 'categories',
        name: '分类列表',
        method: 'GET',
        path: '/complaints/categories',
        description: '查询 complaint_categories：名称、描述、种子句、投诉条数',
        queryParams: [
            { name: 'name', label: '分类名称', type: 'string', placeholder: '模糊匹配' },
        ],
    },
    {
        id: 'stats',
        name: '多维统计',
        method: 'GET',
        path: '/complaints/stats',
        description: '按类型、地区、时间聚合；传 q 时由 LLM 解析自然语言后带条件统计',
        queryParams: [
            { name: 'q', label: '自然语言查询', type: 'string', placeholder: '如：3月哪个区投诉最多' },
            { name: 'refresh', label: '强制刷新缓存', type: 'boolean' },
        ],
    },
    {
        id: 'create',
        name: '新增投诉',
        method: 'POST',
        path: '/complaints',
        description: '录入单条投诉：向量相似度 ≥ 当前阈值归入已有类，否则 LLM 自动新建类型',
        formParams: [
            { name: 'complaint_text', label: '投诉正文', type: 'string', required: true, placeholder: '至少 5 字' },
            { name: 'address', label: '地区', type: 'string', placeholder: '如：成都' },
            { name: 'complaint_time', label: '投诉时间', type: 'string', placeholder: 'ISO 时间，留空为当前' },
        ],
    },
    {
        id: 'samples',
        name: '样本列表',
        method: 'GET',
        path: '/complaints/samples',
        description: '按地址、时间搜索投诉样本；填写正文时按向量语义检索并按相似度排序',
        queryParams: [
            { name: 'address', label: '地区', type: 'string', placeholder: '模糊匹配地址' },
            { name: 'text', label: '正文', type: 'string', placeholder: '有值则语义检索' },
            { name: 'time_from', label: '开始日期', type: 'string', placeholder: 'YYYY-MM-DD' },
            { name: 'time_to', label: '结束日期', type: 'string', placeholder: 'YYYY-MM-DD' },
            { name: 'category_name', label: '分类名称', type: 'string', placeholder: '可选' },
            { name: 'is_classified', label: '是否已归类', type: 'boolean', placeholder: 'true/false，留空为全部' },
            { name: 'min_similarity', label: '最低相似度', type: 'number', min: 0, max: 1, placeholder: '有正文时过滤检索分' },
            { name: 'page', label: '页码', type: 'number', default: 1, min: 1 },
            { name: 'page_size', label: '每页条数', type: 'number', default: 10, min: 1, max: 100 },
        ],
        resultView: {
            mode: 'table',
            dataPath: 'items',
            pageSize: 10,
            columns: [
                { prop: 'id', label: 'ID', width: 70 },
                { prop: 'address', label: '地区', width: 100 },
                { prop: 'complaint_time', label: '投诉时间', width: 170 },
                { prop: 'category_name', label: '分类', width: 120 },
                { prop: 'complaint_text', label: '投诉内容', minWidth: 240, showOverflowTooltip: true },
                { prop: 'similarity', label: '相似度', width: 90 },
            ],
        },
    },
];

const documentChunkRowActions: ApiResultRowActions = {
    updatePath: '/documents/chunks/{id}',
    deletePath: '/documents/chunks/{id}',
    createPath: '/documents/chunks',
    editableFields: [
        { name: 'content', label: '正文', type: 'string', required: true },
        { name: 'section_title', label: '章节标题', type: 'string' },
        { name: 'section_path', label: '章节路径', type: 'string' },
    ],
    createFields: [
        { name: 'source_file', label: '文件名', type: 'string', required: true },
        { name: 'content', label: '正文', type: 'string', required: true },
        { name: 'section_title', label: '章节标题', type: 'string' },
        { name: 'section_path', label: '章节路径', type: 'string' },
        { name: 'chunk_index', label: '块序', type: 'string', placeholder: '留空自动递增' },
    ],
};

export const documentEndpoints: ApiEndpoint[] = [
    {
        id: 'import',
        name: '导入文档',
        method: 'POST',
        path: '/documents/import',
        description: '上传 UTF-8 文本文档并切块入库',
        formParams: [
            { name: 'file', label: '文档文件', type: 'file', required: true },
            { name: 'replace_existing', label: '覆盖同名文件', type: 'boolean', default: true },
            {
                name: 'max_chunk_len',
                label: '最大块长度',
                type: 'number',
                default: 300,
                min: 50,
                max: 2000,
                placeholder: '合并后单块上限（字符，建议300-500）',
            },
            {
                name: 'chunk_overlap',
                label: '块重叠长度',
                type: 'number',
                default: 50,
                min: 0,
                max: 500,
                placeholder: '前后切块重叠的字符数（建议50左右）',
            },
            {
                name: 'min_chunk_len',
                label: '最小块长度',
                type: 'number',
                default: 10,
                min: 5,
                max: 200,
                placeholder: '标点切分后合并的下限（字符）',
            },
        ],
    },
    {
        id: 'listByFile',
        name: '按文件名查',
        method: 'GET',
        path: '/documents/listByFile',
        description: '按文件名查询文档切块',
        queryParams: [
            {
                name: 'source_file',
                label: '文件名',
                type: 'string',
                placeholder: '留空查全部；或填导入时的文件名，如休假规则',
            },
            { name: 'limit', label: '条数', type: 'number', default: 20, min: 1, max: 200 },
        ],
        resultView: {
            mode: 'table',
            pageSize: 10,
            columns: [
                { prop: 'id', label: 'ID', width: 70 },
                { prop: 'source_file', label: '文件', minWidth: 120, showOverflowTooltip: true },
                { prop: 'section_title', label: '章节', minWidth: 100, showOverflowTooltip: true },
                { prop: 'section_path', label: '路径', minWidth: 100, showOverflowTooltip: true },
                { prop: 'chunk_index', label: '块序', width: 70 },
                { prop: 'char_count', label: '字数', width: 70 },
                { prop: 'content', label: '内容', minWidth: 240, showOverflowTooltip: true },
            ],
            rowActions: documentChunkRowActions,
        },
    },
    {
        id: 'search',
        name: '向量检索',
        method: 'GET',
        path: '/documents/search',
        description: 'BGE 向量语义检索 top-k 片段',
        queryParams: [
            { name: 'q', label: '查询文本', type: 'string', placeholder: '例如：休假规则是什么？' },
            { name: 'limit', label: '条数', type: 'number', default: 5, min: 1, max: 50 },
            {
                name: 'min_similarity',
                label: '最低相似度',
                type: 'number',
                default: 0.55,
                min: 0,
                max: 1,
                step: 0.1,
                placeholder: '0～1，低于此值的结果丢弃',
            },
        ],
        resultView: {
            mode: 'table',
            pageSize: 5,
            columns: [
                { prop: 'id', label: 'ID', width: 70 },
                { prop: 'source_file', label: '文件', minWidth: 120, showOverflowTooltip: true },
                { prop: 'section_title', label: '章节', minWidth: 100, showOverflowTooltip: true },
                { prop: 'chunk_index', label: '块序', width: 70 },
                { prop: 'similarity', label: '相似度', width: 90 },
                { prop: 'content', label: '内容', minWidth: 240, showOverflowTooltip: true },
            ],
            rowActions: documentChunkRowActions,
        },
    },
    {
        id: 'search-and-llm',
        name: '搜索+LLM',
        method: 'GET',
        path: '/documents/search_and_llm',
        description: '向量检索 + 大模型润色，返回回答与原始出处',
        queryParams: [
            { name: 'q', label: '查询文本', type: 'string' },
            { name: 'limit', label: '条数', type: 'number', default: 5, min: 1, max: 50 },
            {
                name: 'min_similarity',
                label: '最低相似度',
                type: 'number',
                default: 0.55,
                min: 0,
                max: 1,
                step: 0.1,
                placeholder: '0～1，低于此值的结果丢弃',
            },
        ],
        resultView: {
            mode: 'table',
            dataPath: 'original_sources',
            pageSize: 5,
            highlightFields: [
                { key: 'query', label: '查询' },
                { key: 'polished_answer', label: '润色回答' },
            ],
            columns: [
                { prop: 'snippet_index', label: '片段', width: 70 },
                { prop: 'id', label: 'ID', width: 70 },
                { prop: 'source_label', label: '来源', minWidth: 140, showOverflowTooltip: true },
                { prop: 'similarity', label: '相似度', width: 90 },
                { prop: 'content', label: '原文', minWidth: 240, showOverflowTooltip: true },
            ],
            rowActions: documentChunkRowActions,
        },
    },
];

const DOCUMENT_EP_I18N_KEY: Record<string, string> = {
    import: 'import',
    listByFile: 'listByFile',
    search: 'search',
    'search-and-llm': 'searchAndLlm',
};

const DOCUMENT_QUERY_EXAMPLE_IDS: Record<string, string[]> = {
    'search-and-llm': ['leave', 'travelExpense'],
};

type TranslateFn = (key: string) => string;

const localizeParams = (
    params: ApiParam[] | undefined,
    epKey: string,
    t: TranslateFn,
    paramType: 'query' | 'form' | 'body',
): ApiParam[] | undefined => {
    if (!params) return undefined;
    return params.map((p) => {
        const base = `pages.rag.endpoints.${epKey}.${paramType}.${p.name}`;
        return {
            ...p,
            label: t(`${base}.label`),
            placeholder: p.placeholder ? t(`${base}.placeholder`) : undefined,
        };
    });
};

const localizeRowActions = (actions: ApiResultRowActions, t: TranslateFn): ApiResultRowActions => {
    const mapFields = (fields: ApiParam[]) =>
        fields.map((f) => ({
            ...f,
            label: t(`pages.rag.chunkFields.${f.name}.label`),
            placeholder: f.placeholder
                ? t(`pages.rag.chunkFields.${f.name}.placeholder`)
                : undefined,
        }));
    return {
        ...actions,
        editableFields: mapFields(actions.editableFields),
        createFields: mapFields(actions.createFields),
    };
};

export function getDocumentEndpoints(t: TranslateFn, te?: (key: string) => boolean): ApiEndpoint[] {
    return documentEndpoints.map((ep) => {
        const epKey = DOCUMENT_EP_I18N_KEY[ep.id] ?? ep.id;
        const localized: ApiEndpoint = {
            ...ep,
            name: t(`pages.rag.tabs.${epKey}`),
            description: ep.description ? t(`pages.rag.endpoints.${epKey}.description`) : undefined,
            queryParams: localizeParams(ep.queryParams, epKey, t, 'query'),
            formParams: localizeParams(ep.formParams, epKey, t, 'form'),
            bodyParams: localizeParams(ep.bodyParams, epKey, t, 'body'),
        };

        if (ep.resultView?.mode === 'table') {
            localized.resultView = {
                ...ep.resultView,
                highlightFields: ep.resultView.highlightFields?.map((field) => ({
                    ...field,
                    label: t(`pages.rag.highlights.${field.key}`),
                })),
                columns: ep.resultView.columns.map((col) => {
                    const specificKey = `pages.rag.endpoints.${epKey}.columns.${col.prop}`;
                    const label =
                        col.prop === 'id'
                            ? 'ID'
                            : te?.(specificKey)
                              ? t(specificKey)
                              : t(`pages.rag.columns.${col.prop}`);
                    return { ...col, label };
                }),
                rowActions: ep.resultView.rowActions
                    ? localizeRowActions(ep.resultView.rowActions, t)
                    : undefined,
            };
        }

        const exampleIds = DOCUMENT_QUERY_EXAMPLE_IDS[ep.id];
        if (exampleIds?.length) {
            localized.queryExamples = exampleIds.map((id) => ({
                label: t(`pages.rag.endpoints.${epKey}.examples.${id}.label`),
                query: { q: t(`pages.rag.endpoints.${epKey}.examples.${id}.q`) },
            }));
        }

        return localized;
    });
}

export const meetingEndpoints: ApiEndpoint[] = [
    {
        id: 'organize',
        name: '会议整理',
        method: 'POST',
        path: '/meeting/organize',
        description: '将杂乱的会议记录整理为有条理、有结论的纪要',
        bodyParams: [
            {
                name: 'text',
                label: '原始文字',
                type: 'string',
                required: true,
                placeholder: '粘贴会议速记或语音转写内容',
            },
            {
                name: 'style',
                label: '整理风格',
                type: 'string',
                default: 'formal',
                placeholder: 'concise 精简版 / formal 正规版',
            },
            { name: 'temperature', label: '温度', type: 'number', default: 0.3, min: 0, max: 2 },
        ],
        resultView: {
            mode: 'content',
            contentField: 'organized_text',
            contentLabel: '整理结果',
        },
    },
];

export const chatEndpoints: ApiEndpoint[] = [
    {
        id: 'ask',
        name: 'AI 提问',
        method: 'POST',
        path: '/chat/ask',
        description: '调用大模型回答问题，支持系统提示词与多轮历史',
        bodyParams: [
            { name: 'question', label: '问题', type: 'string', required: true, placeholder: '输入你的问题' },
            {
                name: 'system_prompt',
                label: '系统提示词',
                type: 'string',
                placeholder: '可选，留空使用默认提示词',
            },
            {
                name: 'history',
                label: '对话历史 (JSON)',
                type: 'json',
                default: '[]',
                placeholder: '[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]',
            },
            { name: 'temperature', label: '温度', type: 'number', default: 0.7, min: 0, max: 2 },
        ],
        resultView: {
            mode: 'content',
            contentField: 'answer',
            contentLabel: '回答',
        },
    },
];

export const itemEndpoints: ApiEndpoint[] = [
    {
        id: 'list',
        name: '物品列表',
        method: 'GET',
        path: '/items/',
        description: '获取全部物品',
        resultView: {
            mode: 'table',
            pageSize: 10,
            columns: [
                { prop: 'id', label: 'ID', width: 80 },
                { prop: 'title', label: '标题', minWidth: 200, showOverflowTooltip: true },
            ],
        },
    },
    {
        id: 'create',
        name: '新增物品',
        method: 'POST',
        path: '/items/',
        description: '创建一条物品记录',
        bodyParams: [{ name: 'title', label: '标题', type: 'string', required: true }],
        resultView: {
            mode: 'table',
            pageSize: 1,
            columns: [
                { prop: 'id', label: 'ID', width: 80 },
                { prop: 'title', label: '标题', minWidth: 200, showOverflowTooltip: true },
            ],
        },
    },
];
