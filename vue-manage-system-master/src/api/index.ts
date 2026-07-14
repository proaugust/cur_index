import request from '../utils/request';

// --- complaints ---
export const initComplaintCategories = () =>
    request.post('/complaints/init-categories');

export const seedComplaints = (count = 500) =>
    request.post('/complaints/seed', null, { params: { count } });

export const embedComplaints = () =>
    request.post('/complaints/embed');

export const classifyComplaints = () =>
    request.post('/complaints/classify');

export const getComplaintStats = (params?: { q?: string; refresh?: boolean }) =>
    request.get('/complaints/stats', { params });

export const getComplaintCategories = (params?: { name?: string }) =>
    request.get('/complaints/categories', { params });

export const getComplaintSettings = () =>
    request.get('/complaints/settings');

export const updateComplaintSettings = (data: { classify_threshold: number }) =>
    request.put('/complaints/settings', data);

export const getComplaintSamples = (params?: {
    address?: string;
    text?: string;
    time_from?: string;
    time_to?: string;
    category_name?: string;
    is_classified?: boolean;
    min_similarity?: number;
    page?: number;
    page_size?: number;
}) => request.get('/complaints/samples', { params });

export const createComplaint = (data: {
    complaint_text: string;
    address?: string;
    complaint_time?: string;
}) => request.post('/complaints', data);

// --- insight ---
export const getInsightSeedStatus = () => request.get('/insight/seed/status');

export const getInsightSeedPresets = () => request.get('/insight/seed/presets');

export const postInsightSeedUsers = (preset: 'mini' | 'dev' | 'demo' | 'full' = 'demo') =>
    request.post('/insight/seed/users', null, { params: { preset } });

export const postInsightSeedSamples = (preset: 'mini' | 'dev' | 'demo' | 'full' = 'demo') =>
    request.post('/insight/seed/samples', null, { params: { preset } });

export const postInsightSeedResetUsers = () => request.post('/insight/seed/reset-users');

export const postInsightSeedResetSamples = () => request.post('/insight/seed/reset-samples');

export const getInsightSeedPreview = (count = 3) =>
    request.get('/insight/seed/preview', { params: { count } });

export const getInsightUsers = (params?: Record<string, unknown>) =>
    request.get('/insight/users', { params });

export const getInsightUserProfile = (userId: string) =>
    request.get(`/insight/users/${userId}/profile`);

export const createInsightUser = (data: Record<string, unknown>) =>
    request.post('/insight/users', data);

export const updateInsightUser = (userId: string, data: Record<string, unknown>) =>
    request.put(`/insight/users/${userId}`, data);

export const deleteInsightUser = (userId: string) =>
    request.delete(`/insight/users/${userId}`);

export const getInsightSamples = (params?: Record<string, unknown>) =>
    request.get('/insight/samples', { params });

/** @deprecated 使用 getInsightSamples */
export const getInsightTouchpoints = getInsightSamples;

export const postInsightNightlyRun = (
    snapshotDate?: string,
    withPrevDay = false,
    mode: 'incremental' | 'full' = 'incremental',
) =>
    request.post('/insight/jobs/nightly-run', null, {
        params: {
            ...(snapshotDate ? { snapshot_date: snapshotDate } : {}),
            with_prev_day: withPrevDay,
            mode,
        },
        timeout: 60000,
    });

export const getInsightJobLogs = (params?: Record<string, unknown>) =>
    request.get('/insight/jobs/logs', { params });

export const postInsightBuildSnapshot = (
    snapshotDate?: string,
    withPrevDay = false,
    mode: 'incremental' | 'full' = 'incremental',
) =>
    request.post('/insight/risk/build-snapshot', null, {
        params: {
            ...(snapshotDate ? { snapshot_date: snapshotDate } : {}),
            with_prev_day: withPrevDay,
            mode,
        },
        timeout: 60000,
    });

export const getInsightSnapshots = (params?: Record<string, unknown>) =>
    request.get('/insight/snapshots', { params });

export const getInsightRegionMetrics = (params?: Record<string, unknown>) =>
    request.get('/insight/region-metrics', { params });

export const getInsightSimulationWeights = () =>
    request.get('/insight/simulation-weights');

export const getInsightDecisionDashboard = () =>
    request.get('/insight/decision/dashboard');

export const getInsightDecisionRecommendations = (params?: Record<string, unknown>) =>
    request.get('/insight/decision/recommendations', { params });

export const postInsightDecisionSimulate = (data: Record<string, unknown>) =>
    request.post('/insight/decision/simulate', data);

export const postInsightTrainModel = () =>
    request.post('/insight/models/train');

export const getInsightComplaintCategories = () =>
    request.get('/insight/complaint-categories');

export const getInsightComplaints = (params?: Record<string, unknown>) =>
    request.get('/insight/complaints', { params });

export const createInsightComplaint = (data: Record<string, unknown>) =>
    request.post('/insight/complaints', data);

export const updateInsightComplaint = (complaintId: string, data: Record<string, unknown>) =>
    request.put(`/insight/complaints/${complaintId}`, data);

export const deleteInsightComplaint = (complaintId: string) =>
    request.delete(`/insight/complaints/${complaintId}`);

// --- documents / RAG ---
export const importDocument = (file: File, replaceExisting = true) => {
    const form = new FormData();
    form.append('file', file);
    form.append('replace_existing', String(replaceExisting));
    return request.post('/documents/import', form);
};

export const searchDocuments = (
    q: string,
    limit = 5,
    min_similarity = 0.55,
) => request.get('/documents/search', { params: { q, limit, min_similarity } });

export const searchDocumentsAndLlm = (
    q: string,
    limit = 5,
    min_similarity = 0.55,
) => request.get('/documents/search_and_llm', { params: { q, limit, min_similarity } });

/** @deprecated 使用 searchDocumentsAndLlm */
export const searchDocumentsPolished = searchDocumentsAndLlm;

export const listDocumentChunksByFile = (params?: { source_file?: string; limit?: number }) =>
    request.get('/documents/listByFile', { params });

/** @deprecated 使用 listDocumentChunksByFile */
export const listDocumentChunks = listDocumentChunksByFile;

export const createDocumentChunk = (data: {
    source_file: string;
    content: string;
    section_title?: string;
    section_path?: string;
    chunk_index?: number;
}) => request.post('/documents/chunks', data);

export const updateDocumentChunk = (
    chunkId: number,
    data: { content?: string; section_title?: string; section_path?: string },
) => request.put(`/documents/chunks/${chunkId}`, data);

export const deleteDocumentChunk = (chunkId: number) =>
    request.delete(`/documents/chunks/${chunkId}`);

/** 业务知识库：检索 / 检索+LLM / 清空切块 */
export const searchCorpus = (params: {
    corpus_name: string;
    q?: string;
    limit?: number;
    min_similarity?: number;
    source_file?: string;
    retrieve_mode?: string;
    expand_parent?: boolean;
}) => request.get('/documents/corpora/search', { params });

export const searchCorpusAndLlm = (params: {
    corpus_name: string;
    q?: string;
    limit?: number;
    min_similarity?: number;
    retrieve_mode?: string;
    expand_parent?: boolean;
}) => request.get('/documents/corpora/search_and_llm', { params });

export const clearCorpus = (params: { corpus_name: string }) =>
    request.delete('/documents/corpora', { params });

// --- meeting ---
export const organizeMeeting = (data: { text: string; style?: 'concise' | 'formal'; temperature?: number }) =>
    request.post('/meeting/organize', data);

// --- smart route ---
export const smartRouteDispatch = (data: { question: string }) =>
    request.post('/smart-route/dispatch', data);

// --- attendance ---
export const attendancePunch = (data: {
    descriptor: number[];
    match_threshold?: number;
    face_image?: string;
    face_score?: number;
    dedup_enabled?: boolean;
    dedup_seconds?: number;
}) => request.post('/attendance/punch', data);

export const listAttendancePunches = (params?: {
    user_id?: string;
    page?: number;
    page_size?: number;
}) =>
    request.get('/attendance/punches', {
        params: { ...params, _t: Date.now() },
        headers: { 'Cache-Control': 'no-cache' },
    });

export const listAttendancePersons = (params?: { user_id?: string }) =>
    request.get('/attendance/persons', {
        params: { ...params, _t: Date.now() },
        headers: { 'Cache-Control': 'no-cache' },
    });

export const deleteAttendancePunch = (punchId: number) =>
    request.delete(`/attendance/punches/${punchId}`);

export const deleteAttendancePerson = (personId: number) =>
    request.delete(`/attendance/persons/${personId}`);

// --- agent ---
export const runAgent = (data: {
    question: string;
    mode: 'single' | 'sequential' | 'routing' | 'reflection';
    engine?: 'native' | 'langchain';
    temperature?: number;
}) => request.post('/my_agent/run', data);

// --- COBOL migrate demo ---
export const runCobolMigrateStep = (step: number) =>
    request.post(`/cobol_migrate/step/${step}`);

export const runCobolMigratePipeline = () => request.post('/cobol_migrate/pipeline');

// --- AI chat ---
export const askChat = (data: {
    question: string;
    system_prompt?: string;
    history?: { role: 'user' | 'assistant'; content: string }[];
    temperature?: number;
}) => request.post('/chat/ask', data);

// --- zha jinhua ---
export const startZhaJinhuaGame = () => request.post('/game/start');

export const nextZhaJinhuaRound = () => request.post('/game/next-round');

export const redealZhaJinhuaRound = (mode: 'all_big' | 'all_small' | 'random') =>
    request.post('/game/redeal', { mode });

export const resetZhaJinhuaGame = () => request.post('/game/reset');

export const zhaJinhuaTurn = (playerId: string) =>
    request.post(`/game/turn/${playerId}`);

export const getZhaJinhuaReferee = () => request.get('/game/referee');

export const getZhaJinhuaStatus = () => request.get('/game/status');

export const setZhaJinhuaAccess = (enabled: boolean) =>
    request.post('/game/access', { enabled });

// --- feature intros ---
export interface FeatureIntroRow {
    page_key: string;
    section_key: string;
    title: string;
    content: string;
    updated_at: string;
}

export const getFeatureIntros = (pageKey?: string) =>
    request.get<FeatureIntroRow[]>('/feature-intros/', { params: pageKey ? { page_key: pageKey } : {} });

export const upsertFeatureIntro = (
    pageKey: string,
    sectionKey: string,
    data: { title?: string; content: string },
) => request.put(`/feature-intros/${pageKey}/${sectionKey}`, data);

export const seedFeatureIntros = () => request.post('/feature-intros/seed');

// --- AI news ---
export interface AiNewsLinkItem {
    id: number;
    slug: string | null;
    url: string;
    name: string;
    description: string;
    icon: string;
    letter: string;
    color: string;
    is_system: boolean;
}

export interface AiNewsBoard {
    international: AiNewsLinkItem[];
    domestic: AiNewsLinkItem[];
    favorites: AiNewsLinkItem[];
}

export interface AiNewsBoardUpdate {
    international: Array<Omit<AiNewsLinkItem, 'id' | 'is_system'>>;
    domestic: Array<Omit<AiNewsLinkItem, 'id' | 'is_system'>>;
    favorites: Array<Omit<AiNewsLinkItem, 'id' | 'is_system'>>;
}

export const getAiNewsBoard = () => request.get<AiNewsBoard>('/ai-news/board');

export const putAiNewsBoard = (data: AiNewsBoardUpdate) => request.put<AiNewsBoard>('/ai-news/board', data);

export const createAiNewsLink = (url: string) => request.post<AiNewsBoard>('/ai-news/links', { url });

// --- items ---
export const listItems = () => request.get('/items/');

export const createItem = (data: { title: string }) => request.post('/items/', data);

export const fetchData = () => {
    return request({
        url: './mock/table.json',
        method: 'get'
    });
};

// --- auth / rbac ---
export const login = (data: { username: string; password: string }) =>
    request.post('/auth/login', data);

export const fetchMe = () => request.get('/auth/me');

export const changePassword = (data: { old_password: string; new_password: string }) =>
    request.put('/auth/password', data);

export const fetchUserData = (params?: { name?: string; page?: number; page_size?: number }) =>
    request.get('/users/', { params });

export const createUser = (data: {
    name: string;
    password: string;
    email?: string;
    phone?: string;
    role_id: number;
}) => request.post('/users/', data);

export const updateUser = (
    id: number,
    data: {
        name?: string;
        password?: string;
        email?: string;
        phone?: string;
        role_id?: number;
        is_active?: boolean;
    },
) => request.put(`/users/${id}`, data);

export const deleteUser = (id: number) => request.delete(`/users/${id}`);

export const fetchRoleData = () => request.get('/roles/');

export const createRole = (data: {
    name: string;
    key: string;
    status?: boolean;
    level?: number;
    permiss?: string[];
}) => request.post('/roles/', data);

export const updateRole = (
    id: number,
    data: { name?: string; status?: boolean; level?: number; permiss?: string[] },
) => request.put(`/roles/${id}`, data);

export const updateRolePermissions = (id: number, permiss: string[]) =>
    request.put(`/roles/${id}/permissions`, { permiss });

export const deleteRole = (id: number) => request.delete(`/roles/${id}`);

export const fetchMenuData = () => request.get('/menus/');

export const createMenu = (data: {
    code: string;
    name: string;
    parent_code?: string;
    route_path?: string;
    icon?: string;
}) => request.post('/menus/', data);

export const updateMenu = (
    code: string,
    data: {
        name?: string;
        parent_code?: string;
        route_path?: string;
        icon?: string;
    },
) => request.put(`/menus/${code}`, data);

export const deleteMenu = (code: string) => request.delete(`/menus/${code}`);

export const fetchPermissionTree = () => request.get('/permissions/tree');

export const fetchLlmUsageStats = (params?: { days?: number | null; exclude_warmup?: boolean }) =>
    request.get('/llm-usage/stats', { params });

export interface LlmUsageRecentQuery {
    page?: number;
    page_size?: number;
    caller?: string;
    username?: string;
    user_id?: number;
    engine?: string;
    success?: boolean;
    request_id?: string;
    days?: number | null;
    exclude_warmup?: boolean;
}

export const fetchLlmUsageRecent = (params?: LlmUsageRecentQuery) =>
    request.get('/llm-usage/recent', { params });

export interface AppErrorLogQuery {
    page?: number;
    page_size?: number;
    source?: string;
    level?: string;
    status?: string;
    error_type?: string;
    request_id?: string;
    days?: number | null;
}

export const fetchAppErrorLogs = (params?: AppErrorLogQuery) =>
    request.get('/error-logs', { params });

export const patchAppErrorLogStatus = (errorId: number, status: 'open' | 'resolved') =>
    request.patch(`/error-logs/${errorId}/status`, { status });

export const fetchEpochStats = () =>
    request.get('/epoch/stats');

export const fetchAiTrendsStats = () =>
    request.get('/ai-trends/stats');
