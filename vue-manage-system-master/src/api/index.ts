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

export const getComplaintStats = () =>
    request.get('/complaints/stats');

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
    classified?: boolean;
    page?: number;
    page_size?: number;
}) => request.get('/complaints/samples', { params });

export const createComplaint = (data: {
    complaint_text: string;
    address?: string;
    complaint_time?: string;
}) => request.post('/complaints', data);

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
