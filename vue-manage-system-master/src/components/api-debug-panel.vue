<template>
    <div class="api-debug-panel">
        <el-card shadow="hover">
            <el-tabs v-model="activeTab" type="border-card">
                <el-tab-pane v-for="ep in endpoints" :key="ep.id" :name="ep.id">
                    <template #label>
                        <span class="tab-label">
                            <el-tag :type="methodTagType(ep.method)" size="small" class="method-tag">
                                {{ ep.method }}
                            </el-tag>
                            <span>{{ ep.name }}</span>
                            <FeatureIntroIcon
                                v-if="introPageKey"
                                :page-key="introPageKey"
                                :section-key="ep.id"
                                :intros="intros"
                                :title="ep.name"
                                @saved="onIntroSaved"
                            />
                        </span>
                    </template>

                    <div class="endpoint-header">
                        <code class="endpoint-path">{{ ep.path }}</code>
                        <p v-if="ep.description" class="endpoint-desc">{{ ep.description }}</p>
                    </div>

                    <slot v-if="hasPanelSlot(ep.id)" :name="`panel-${ep.id}`" />
                    <template v-else>
                    <div v-if="ep.queryExamples?.length" class="example-list">
                        <div class="param-section-title">{{ t('apiDebug.exampleQueries') }}</div>
                        <div
                            v-for="item in ep.queryExamples"
                            :key="item.label"
                            class="example-item"
                            :class="{ active: isActiveExample(ep, item) }"
                        >
                            <div class="example-item-bar">
                                <el-tag size="small">{{ item.label }}</el-tag>
                                <el-button
                                    size="small"
                                    link
                                    type="primary"
                                    :disabled="loading[ep.id]"
                                    @click="applyQueryExample(ep, item)"
                                >
                                    {{ t('apiDebug.fillExample') }}
                                </el-button>
                            </div>
                            <p class="example-text">{{ item.query.q }}</p>
                        </div>
                    </div>

                    <el-form label-width="120px" class="param-form" @submit.prevent>
                        <template v-if="ep.pathParams?.length">
                            <div class="param-section-title">{{ t('apiDebug.pathParams') }}</div>
                            <el-form-item
                                v-for="param in ep.pathParams"
                                :key="param.name"
                                :label="param.label"
                                :required="param.required"
                            >
                                <el-input-number
                                    v-if="param.type === 'number'"
                                    v-model="formState[ep.id].path[param.name] as number"
                                    :min="param.min"
                                    :max="param.max"
                                    style="width: 200px"
                                />
                                <el-input
                                    v-else
                                    v-model="formState[ep.id].path[param.name] as string"
                                    :placeholder="param.placeholder"
                                    clearable
                                />
                            </el-form-item>
                        </template>

                        <template v-if="ep.queryParams?.length">
                            <div class="param-section-title">{{ t('apiDebug.queryParams') }}</div>
                            <el-form-item
                                v-for="param in ep.queryParams"
                                :key="param.name"
                                :label="param.label"
                                :required="param.required"
                            >
                                <el-input-number
                                    v-if="param.type === 'number'"
                                    v-model="formState[ep.id].query[param.name] as number"
                                    :min="param.min"
                                    :max="param.max"
                                    :step="param.step ?? 1"
                                    style="width: 200px"
                                />
                                <el-switch
                                    v-else-if="param.type === 'boolean'"
                                    v-model="formState[ep.id].query[param.name] as boolean"
                                />
                                <el-input
                                    v-else
                                    v-model="formState[ep.id].query[param.name] as string"
                                    :placeholder="param.placeholder"
                                    clearable
                                />
                            </el-form-item>
                        </template>

                        <template v-if="ep.bodyParams?.length">
                            <div class="param-section-title">{{ t('apiDebug.bodyParams') }}</div>
                            <el-form-item
                                v-for="param in ep.bodyParams"
                                :key="param.name"
                                :label="param.label"
                                :required="param.required"
                            >
                                <el-input-number
                                    v-if="param.type === 'number'"
                                    v-model="formState[ep.id].body[param.name] as number"
                                    :min="param.min"
                                    :max="param.max"
                                    :step="0.1"
                                    style="width: 200px"
                                />
                                <el-input
                                    v-else-if="param.type === 'json'"
                                    v-model="formState[ep.id].body[param.name] as string"
                                    type="textarea"
                                    :rows="8"
                                    :placeholder="param.placeholder"
                                />
                                <el-input
                                    v-else
                                    v-model="formState[ep.id].body[param.name] as string"
                                    :placeholder="param.placeholder"
                                    clearable
                                />
                            </el-form-item>
                        </template>

                        <template v-if="ep.formParams?.length">
                            <div class="param-section-title">{{ t('apiDebug.formParams') }}</div>
                            <el-form-item
                                v-for="param in ep.formParams"
                                :key="param.name"
                                :label="param.label"
                                :required="param.required"
                            >
                                <el-upload
                                    v-if="param.type === 'file'"
                                    :auto-upload="false"
                                    :show-file-list="true"
                                    :limit="1"
                                    accept=".txt,.md"
                                    :on-change="(f: UploadFile) => onFileChange(ep.id, param.name, f)"
                                >
                                    <el-button size="small">{{ t('apiDebug.selectFile') }}</el-button>
                                </el-upload>
                                <el-switch
                                    v-else-if="param.type === 'boolean'"
                                    v-model="formState[ep.id].form[param.name] as boolean"
                                />
                                <el-input-number
                                    v-else-if="param.type === 'number'"
                                    v-model="formState[ep.id].form[param.name] as number"
                                    :min="param.min"
                                    :max="param.max"
                                    style="width: 200px"
                                />
                                <el-input
                                    v-else
                                    v-model="formState[ep.id].form[param.name] as string"
                                    :placeholder="param.placeholder"
                                    clearable
                                />
                            </el-form-item>
                        </template>
                    </el-form>

                    <div class="send-row">
                        <el-button type="primary" :loading="loading[ep.id]" @click="sendRequest(ep)">
                            {{ t('common.send') }}
                        </el-button>
                        <span
                            v-if="statusInfo[ep.id]"
                            class="status-info"
                            :class="statusInfo[ep.id].ok ? 'ok' : 'err'"
                        >
                            {{ statusInfo[ep.id].text }}
                        </span>
                    </div>

                    <div v-if="ep.resultView?.mode === 'table' && tableState[ep.id]?.rows.length" class="result-table-wrap">
                        <template v-for="field in ep.resultView.highlightFields ?? []" :key="field.key">
                            <div v-if="tableState[ep.id].highlights[field.key]" class="highlight-block">
                                <div class="highlight-label">{{ field.label }}</div>
                                <div class="highlight-content">{{ tableState[ep.id].highlights[field.key] }}</div>
                            </div>
                        </template>

                        <div
                            v-if="ep.resultView.contentField"
                            class="result-content-list"
                        >
                            <div class="param-section-title">
                                {{ ep.resultView.contentLabel ?? t('apiDebug.contentLabel') }}
                            </div>
                            <div
                                v-for="(row, idx) in pagedRows(ep)"
                                :key="`content-${ep.id}-${row.id ?? idx}`"
                                class="highlight-block result-content-item"
                            >
                                <div class="highlight-label">
                                    <span v-if="row.similarity != null">相似度 {{ row.similarity }}</span>
                                    <span v-if="row.source_file || row.source_label">
                                        · {{ row.source_file || row.source_label }}
                                    </span>
                                    <span v-if="row.section_title"> · {{ row.section_title }}</span>
                                    <span v-if="row.id != null"> · #{{ row.id }}</span>
                                </div>
                                <div class="highlight-content">{{ row[ep.resultView.contentField] }}</div>
                            </div>
                        </div>

                        <el-table
                            :data="pagedRows(ep)"
                            border
                            stripe
                            size="small"
                            class="result-table"
                            highlight-current-row
                            @current-change="(row) => onRowSelect(ep, row)"
                        >
                            <el-table-column
                                v-for="col in ep.resultView.columns"
                                :key="col.prop"
                                :prop="col.prop"
                                :label="col.label"
                                :min-width="col.minWidth ?? col.width"
                                :class-name="col.minWidth && !col.width ? 'col-fill' : 'col-fit'"
                                :label-class-name="col.minWidth && !col.width ? 'col-fill' : 'col-fit'"
                                :show-overflow-tooltip="col.showOverflowTooltip"
                            />
                        </el-table>

                        <el-pagination
                            v-if="showPagination(ep)"
                            class="result-pagination"
                            background
                            layout="total, prev, pager, next"
                            :total="tableTotal(ep)"
                            :page-size="tablePageSize(ep)"
                            :current-page="tableState[ep.id].page"
                            @current-change="(p: number) => onTablePageChange(ep, p)"
                        />

                        <div v-if="ep.resultView.rowActions" class="row-actions-bar">
                            <span v-if="selectedRow[ep.id]" class="selected-hint">
                                {{ t('apiDebug.selectedId', { id: selectedRow[ep.id]?.[ep.resultView.rowActions.idField ?? 'id'] }) }}
                            </span>
                            <span v-else class="selected-hint muted">{{ t('apiDebug.selectRowHint') }}</span>
                            <div class="row-actions-btns">
                                <el-button
                                    size="small"
                                    type="warning"
                                    :disabled="!selectedRow[ep.id]"
                                    :loading="rowActionLoading[ep.id]"
                                    @click="openEditDialog(ep)"
                                >
                                    {{ t('apiDebug.editSelected') }}
                                </el-button>
                                <el-button
                                    size="small"
                                    type="danger"
                                    :disabled="!selectedRow[ep.id]"
                                    :loading="rowActionLoading[ep.id]"
                                    @click="deleteSelectedRow(ep)"
                                >
                                    {{ t('apiDebug.deleteSelected') }}
                                </el-button>
                                <el-button
                                    size="small"
                                    type="primary"
                                    :loading="rowActionLoading[ep.id]"
                                    @click="openCreateDialog(ep)"
                                >
                                    {{ t('apiDebug.addChunk') }}
                                </el-button>
                            </div>
                        </div>
                    </div>

                    <div
                        v-if="ep.resultView?.mode === 'content' && contentState[ep.id]?.content"
                        class="highlight-block content-result-block"
                    >
                        <div class="highlight-label">{{ ep.resultView.contentLabel ?? t('apiDebug.contentLabel') }}</div>
                        <div class="highlight-content">{{ contentState[ep.id].content }}</div>
                    </div>

                    <div
                        v-if="ep.resultView?.mode === 'content' && responses[ep.id]"
                        class="param-section-title"
                    >
                        {{ t('apiDebug.metadata') }}
                    </div>
                    <el-input
                        v-model="responses[ep.id]"
                        type="textarea"
                        :rows="ep.resultView?.mode === 'table' || ep.resultView?.mode === 'content' ? 12 : 28"
                        readonly
                        :placeholder="ep.resultView?.mode === 'content' ? t('apiDebug.responseMetaPh') : t('apiDebug.responseJsonPh')"
                        class="response-box"
                    />
                    </template>
                </el-tab-pane>
            </el-tabs>
        </el-card>

        <el-dialog
            v-model="dialogVisible"
            :title="dialogMode === 'edit' ? t('apiDebug.editChunk') : t('apiDebug.addChunkTitle')"
            width="560px"
            destroy-on-close
            @closed="resetDialog"
        >
            <el-form label-width="100px">
                <el-form-item
                    v-for="field in dialogFields"
                    :key="field.name"
                    :label="field.label"
                    :required="field.required"
                >
                    <el-input-number
                        v-if="field.type === 'number'"
                        v-model="dialogForm[field.name] as number | undefined"
                        :min="field.min"
                        :max="field.max"
                        :placeholder="field.placeholder"
                        style="width: 200px"
                    />
                    <el-input
                        v-else
                        v-model="dialogForm[field.name] as string"
                        :type="field.name === 'content' ? 'textarea' : 'text'"
                        :rows="field.name === 'content' ? 6 : undefined"
                        :placeholder="field.placeholder"
                        clearable
                    />
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
                <el-button type="primary" :loading="dialogSubmitting" @click="submitDialog">
                    {{ t('apiDebug.confirm') }}
                </el-button>
            </template>
        </el-dialog>
    </div>
</template>

<script setup lang="ts">
import { reactive, ref, useSlots, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { UploadFile } from 'element-plus';
import type { AxiosError } from 'axios';
import request from '@/utils/request';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import { readDemoCache, writeDemoCache } from '@/composables/useFormCache';
import type { FeatureIntroMap } from '@/composables/useFeatureIntros';
import type { ApiAsyncJobConfig, ApiEndpoint, ApiParam, ApiQueryExample } from '@/config/api-endpoints';

const { t } = useI18n();
const slots = useSlots();
const hasPanelSlot = (id: string) => Boolean(slots[`panel-${id}`]);

const props = withDefaults(
    defineProps<{
        endpoints: ApiEndpoint[];
        introPageKey?: string;
        intros?: FeatureIntroMap;
    }>(),
    {
        intros: () => ({}),
    },
);

const emit = defineEmits<{
    'intro-saved': [sectionKey: string, content: string];
}>();

const onIntroSaved = (sectionKey: string, content: string) => {
    emit('intro-saved', sectionKey, content);
};

type FormValue = string | number | boolean | File | null;

interface EndpointFormState {
    path: Record<string, FormValue>;
    query: Record<string, FormValue>;
    body: Record<string, FormValue>;
    form: Record<string, FormValue>;
}

interface TableState {
    rows: Record<string, unknown>[];
    highlights: Record<string, string>;
    page: number;
    total: number;
    serverPaging: boolean;
}

interface ContentState {
    content: string;
}

const activeTab = ref('');
const formState = reactive<Record<string, EndpointFormState>>({});
const responses = reactive<Record<string, string>>({});
const tableState = reactive<Record<string, TableState>>({});
const contentState = reactive<Record<string, ContentState>>({});
const loading = reactive<Record<string, boolean>>({});
const statusInfo = reactive<Record<string, { ok: boolean; text: string }>>({});
const selectedRow = reactive<Record<string, Record<string, unknown> | null>>({});
const rowActionLoading = reactive<Record<string, boolean>>({});

const dialogVisible = ref(false);
const dialogMode = ref<'edit' | 'create'>('edit');
const dialogEp = ref<ApiEndpoint | null>(null);
const dialogFields = ref<ApiParam[]>([]);
const dialogForm = reactive<Record<string, FormValue>>({});
const dialogSubmitting = ref(false);

const initDefault = (param: ApiParam): FormValue => {
    if (param.type === 'file') return null;
    if (param.type === 'boolean') return param.default ?? false;
    if (param.type === 'number') return param.default ?? 0;
    if (param.type === 'json') return String(param.default ?? '[]');
    return String(param.default ?? '');
};

const serializeFormForCache = (state: EndpointFormState): EndpointFormState => {
    const sections = ['path', 'query', 'body', 'form'] as const;
    const result = { path: {}, query: {}, body: {}, form: {} } as EndpointFormState;
    for (const section of sections) {
        for (const [name, value] of Object.entries(state[section])) {
            result[section][name] = value instanceof File ? null : value;
        }
    }
    return result;
};

const mergeCachedForm = (target: EndpointFormState, cached: EndpointFormState) => {
    const sections = ['path', 'query', 'body', 'form'] as const;
    for (const section of sections) {
        for (const [name, value] of Object.entries(cached[section] ?? {})) {
            if (name in target[section] && !(value instanceof File)) {
                target[section][name] = value;
            }
        }
    }
};

const initEndpointState = (ep: ApiEndpoint) => {
    if (formState[ep.id]) return;

    const state: EndpointFormState = { path: {}, query: {}, body: {}, form: {} };
    ep.pathParams?.forEach((p) => {
        state.path[p.name] = initDefault(p);
    });
    ep.queryParams?.forEach((p) => {
        state.query[p.name] = initDefault(p);
    });
    ep.bodyParams?.forEach((p) => {
        state.body[p.name] = initDefault(p);
    });
    ep.formParams?.forEach((p) => {
        state.form[p.name] = initDefault(p);
    });

    const cached = readDemoCache<EndpointFormState | null>(`api-debug:${ep.id}`, null);
    if (cached) {
        mergeCachedForm(state, cached);
    }

    formState[ep.id] = state;
    responses[ep.id] = '';
    tableState[ep.id] = { rows: [], highlights: {}, page: 1, total: 0, serverPaging: false };
    contentState[ep.id] = { content: '' };
    loading[ep.id] = false;
    selectedRow[ep.id] = null;
};

watch(
    () => props.endpoints,
    (eps) => {
        eps.forEach(initEndpointState);
        if (!activeTab.value && eps.length) {
            activeTab.value = eps[0].id;
        }
    },
    { immediate: true, deep: true }
);

watch(
    formState,
    () => {
        props.endpoints.forEach((ep) => {
            const state = formState[ep.id];
            if (state) {
                writeDemoCache(`api-debug:${ep.id}`, serializeFormForCache(state));
            }
        });
    },
    { deep: true },
);

const methodTagType = (method: string) => {
    const map: Record<string, 'success' | 'primary' | 'warning' | 'danger' | 'info'> = {
        GET: 'success',
        POST: 'primary',
        PUT: 'warning',
        DELETE: 'danger',
    };
    return map[method] || 'info';
};

const onFileChange = (epId: string, paramName: string, file: UploadFile) => {
    formState[epId].form[paramName] = file.raw ?? null;
};

const applyQueryExample = (ep: ApiEndpoint, example: ApiQueryExample) => {
    Object.entries(example.query).forEach(([name, value]) => {
        if (name in formState[ep.id].query) {
            formState[ep.id].query[name] = value;
        }
    });
};

const isActiveExample = (ep: ApiEndpoint, example: ApiQueryExample) =>
    Object.entries(example.query).every(([name, value]) => formState[ep.id].query[name] === value);

const buildQueryParams = (ep: ApiEndpoint) => {
    const params: Record<string, string | number | boolean> = {};
    ep.queryParams?.forEach((p) => {
        const raw = formState[ep.id].query[p.name];
        if (raw === '' || raw === null || raw === undefined) return;
        if (p.type === 'number') {
            params[p.name] = Number(raw);
        } else if (p.type === 'boolean') {
            params[p.name] = Boolean(raw);
        } else {
            params[p.name] = String(raw);
        }
    });
    return params;
};

/** 行级 CUD 时从当前接口表单 query 带上指定参数（如 corpus_name） */
const buildCarryQuery = (ep: ApiEndpoint, names?: string[]) => {
    const params: Record<string, string> = {};
    if (!names?.length) return params;
    const query = formState[ep.id]?.query ?? {};
    for (const name of names) {
        const raw = query[name];
        if (raw === '' || raw === null || raw === undefined) continue;
        params[name] = String(raw);
    }
    return params;
};

const buildPath = (ep: ApiEndpoint) => {
    let path = ep.path;
    ep.pathParams?.forEach((p) => {
        const raw = formState[ep.id].path[p.name];
        const value = p.type === 'number' ? String(Number(raw)) : String(raw ?? '');
        path = path.replace(`{${p.name}}`, value);
    });
    return path;
};

const getByPath = (data: unknown, path?: string): unknown => {
    if (!path) return data;
    return path.split('.').reduce<unknown>((acc, key) => {
        if (acc && typeof acc === 'object' && key in (acc as Record<string, unknown>)) {
            return (acc as Record<string, unknown>)[key];
        }
        return undefined;
    }, data);
};

const applyContentView = (ep: ApiEndpoint, data: unknown): string => {
    if (ep.resultView?.mode !== 'content' || !data || typeof data !== 'object') {
        contentState[ep.id] = { content: '' };
        return formatJson(data);
    }

    const obj = { ...(data as Record<string, unknown>) };
    const field = ep.resultView.contentField;
    const rawContent = obj[field];
    contentState[ep.id] = {
        content: rawContent !== null && rawContent !== undefined ? String(rawContent) : '',
    };
    delete obj[field];
    return formatJson(obj);
};

const applyResultView = (ep: ApiEndpoint, data: unknown) => {
    if (!ep.resultView || ep.resultView.mode !== 'table') {
        tableState[ep.id] = { rows: [], highlights: {}, page: 1, total: 0, serverPaging: false };
        return;
    }

    const highlights: Record<string, string> = {};
    ep.resultView.highlightFields?.forEach((field) => {
        if (data && typeof data === 'object' && field.key in (data as Record<string, unknown>)) {
            const value = (data as Record<string, unknown>)[field.key];
            if (value !== null && value !== undefined) {
                highlights[field.key] = String(value);
            }
        }
    });

    const rawRows = getByPath(data, ep.resultView.dataPath);
    const rows = Array.isArray(rawRows)
        ? rawRows.filter((row): row is Record<string, unknown> => !!row && typeof row === 'object')
        : [];

    const serverPaging = !!ep.resultView.serverPaging;
    let page = 1;
    let total = rows.length;
    if (serverPaging && data && typeof data === 'object') {
        const obj = data as Record<string, unknown>;
        page = Number(obj.page ?? formState[ep.id]?.query?.page ?? 1) || 1;
        total = Number(obj.total ?? rows.length) || 0;
        if (formState[ep.id]?.query && 'page' in formState[ep.id].query) {
            formState[ep.id].query.page = page;
        }
    }

    tableState[ep.id] = { rows, highlights, page, total, serverPaging };
};

const tablePageSize = (ep: ApiEndpoint) => {
    if (ep.resultView?.mode === 'table' && ep.resultView.serverPaging) {
        const raw = formState[ep.id]?.query?.page_size;
        const n = Number(raw);
        if (Number.isFinite(n) && n > 0) return n;
    }
    return ep.resultView?.mode === 'table' ? (ep.resultView.pageSize ?? 10) : 10;
};

const tableTotal = (ep: ApiEndpoint) => {
    const state = tableState[ep.id];
    if (!state) return 0;
    return state.serverPaging ? state.total : state.rows.length;
};

const showPagination = (ep: ApiEndpoint) => {
    const state = tableState[ep.id];
    if (!state || !ep.resultView || ep.resultView.mode !== 'table') return false;
    return tableTotal(ep) > tablePageSize(ep);
};

const pagedRows = (ep: ApiEndpoint) => {
    const state = tableState[ep.id];
    if (!state || !ep.resultView) return [];
    if (state.serverPaging) return state.rows;
    const pageSize = tablePageSize(ep);
    const start = (state.page - 1) * pageSize;
    return state.rows.slice(start, start + pageSize);
};

const onTablePageChange = (ep: ApiEndpoint, page: number) => {
    const state = tableState[ep.id];
    if (!state) return;
    state.page = page;
    if (!state.serverPaging) return;
    if (formState[ep.id]?.query) {
        formState[ep.id].query.page = page;
    }
    void sendRequest(ep);
};

const buildBody = (ep: ApiEndpoint) => {
    const body: Record<string, unknown> = {};
    ep.bodyParams?.forEach((p) => {
        const raw = formState[ep.id].body[p.name];
        if (p.type === 'json') {
            const text = String(raw ?? '[]').trim();
            body[p.name] = text ? JSON.parse(text) : [];
            return;
        }
        if (raw === '' || raw === null || raw === undefined) return;
        if (p.type === 'number') {
            body[p.name] = Number(raw);
        } else if (p.type === 'boolean') {
            body[p.name] = Boolean(raw);
        } else {
            body[p.name] = String(raw);
        }
    });
    return body;
};

const buildFormData = (ep: ApiEndpoint) => {
    const form = new FormData();
    ep.formParams?.forEach((p) => {
        const raw = formState[ep.id].form[p.name];
        if (p.type === 'file') {
            if (raw instanceof File) form.append(p.name, raw);
            return;
        }
        if (p.type === 'boolean') {
            form.append(p.name, String(Boolean(raw)));
        } else if (p.type === 'number') {
            if (raw !== null && raw !== undefined && raw !== '') {
                form.append(p.name, String(Number(raw)));
            }
        } else if (raw !== null && raw !== undefined && raw !== '') {
            form.append(p.name, String(raw));
        }
    });
    return form;
};

const formatJson = (data: unknown) => JSON.stringify(data, null, 2);

const onRowSelect = (ep: ApiEndpoint, row: Record<string, unknown> | null | undefined) => {
    selectedRow[ep.id] = row ?? null;
};

const replacePathId = (path: string, id: number | string) =>
    path.replace('{id}', String(id)).replace('{chunk_id}', String(id));

const buildFieldsBody = (fields: ApiParam[], form: Record<string, FormValue>) => {
    const body: Record<string, unknown> = {};
    fields.forEach((field) => {
        const raw = form[field.name];
        if (raw === '' || raw === null || raw === undefined) return;
        if (field.type === 'number') {
            body[field.name] = Number(raw);
        } else {
            body[field.name] = String(raw);
        }
    });
    return body;
};

const resetDialog = () => {
    dialogEp.value = null;
    dialogFields.value = [];
    Object.keys(dialogForm).forEach((k) => delete dialogForm[k]);
};

const openEditDialog = (ep: ApiEndpoint) => {
    const row = selectedRow[ep.id];
    const actions = ep.resultView?.rowActions;
    if (!row || !actions) return;

    dialogMode.value = 'edit';
    dialogEp.value = ep;
    dialogFields.value = actions.editableFields;
    actions.editableFields.forEach((field) => {
        const val = row[field.name];
        if (field.type === 'number') {
            dialogForm[field.name] = val !== undefined && val !== null ? Number(val) : 0;
        } else {
            dialogForm[field.name] = val !== undefined && val !== null ? String(val) : '';
        }
    });
    dialogVisible.value = true;
};

const openCreateDialog = (ep: ApiEndpoint) => {
    const actions = ep.resultView?.rowActions;
    if (!actions) return;

    dialogMode.value = 'create';
    dialogEp.value = ep;
    dialogFields.value = actions.createFields;
    actions.createFields.forEach((field) => {
        if (field.type === 'number') {
            dialogForm[field.name] = field.default !== undefined ? Number(field.default) : undefined;
        } else {
            dialogForm[field.name] = String(field.default ?? '');
        }
    });
    const row = selectedRow[ep.id];
    if (row?.source_file) {
        dialogForm.source_file = String(row.source_file);
    }
    const carried = buildCarryQuery(ep, actions.carryQueryParams);
    Object.entries(carried).forEach(([k, v]) => {
        if (k in dialogForm || actions.createFields.some((f) => f.name === k)) {
            dialogForm[k] = v;
        }
    });
    dialogVisible.value = true;
};

const submitDialog = async () => {
    const ep = dialogEp.value;
    const actions = ep?.resultView?.rowActions;
    if (!ep || !actions) return;

    dialogSubmitting.value = true;
    rowActionLoading[ep.id] = true;
    try {
        const carry = buildCarryQuery(ep, actions.carryQueryParams);
        if (dialogMode.value === 'edit') {
            const row = selectedRow[ep.id];
            const idField = actions.idField ?? 'id';
            const chunkId = row?.[idField];
            if (chunkId === undefined || chunkId === null) {
                ElMessage.warning(t('apiDebug.selectChunkFirst'));
                return;
            }
            if (actions.carryQueryParams?.includes('corpus_name') && !carry.corpus_name) {
                ElMessage.warning(t('pages.rag.corporaBrowse.corpusRequired'));
                return;
            }
            const body = buildFieldsBody(actions.editableFields, dialogForm);
            const path = replacePathId(actions.updatePath, chunkId as number | string);
            await request.put(path, body, { params: carry });
            ElMessage.success(t('apiDebug.updated'));
        } else {
            const body = buildFieldsBody(actions.createFields, dialogForm);
            if (!body.source_file || !body.content) {
                ElMessage.warning(t('apiDebug.fileContentRequired'));
                return;
            }
            if (actions.carryQueryParams?.includes('corpus_name') && !body.corpus_name && !carry.corpus_name) {
                ElMessage.warning(t('pages.rag.corporaBrowse.corpusRequired'));
                return;
            }
            if (!body.corpus_name && carry.corpus_name) {
                body.corpus_name = carry.corpus_name;
            }
            if (body.chunk_index !== undefined) {
                body.chunk_index = Number(body.chunk_index);
            }
            await request.post(actions.createPath, body);
            ElMessage.success(t('apiDebug.added'));
        }
        dialogVisible.value = false;
        await sendRequest(ep);
    } catch (err) {
        const axiosErr = err as AxiosError;
        const detail = axiosErr.response?.data;
        ElMessage.error(typeof detail === 'object' && detail && 'detail' in detail
            ? String((detail as { detail: unknown }).detail)
            : t('apiDebug.opFailed'));
    } finally {
        dialogSubmitting.value = false;
        rowActionLoading[ep.id] = false;
    }
};

const deleteSelectedRow = async (ep: ApiEndpoint) => {
    const actions = ep.resultView?.rowActions;
    const row = selectedRow[ep.id];
    if (!actions || !row) return;

    const idField = actions.idField ?? 'id';
    const chunkId = row[idField];
    if (chunkId === undefined || chunkId === null) return;

    try {
        await ElMessageBox.confirm(t('apiDebug.deleteConfirm', { id: chunkId }), t('apiDebug.deleteConfirmTitle'), {
            type: 'warning',
            confirmButtonText: t('common.delete'),
            cancelButtonText: t('common.cancel'),
        });
    } catch {
        return;
    }

    rowActionLoading[ep.id] = true;
    try {
        const carry = buildCarryQuery(ep, actions.carryQueryParams);
        if (actions.carryQueryParams?.includes('corpus_name') && !carry.corpus_name) {
            ElMessage.warning(t('pages.rag.corporaBrowse.corpusRequired'));
            return;
        }
        const path = replacePathId(actions.deletePath, chunkId as number | string);
        await request.delete(path, { params: carry });
        selectedRow[ep.id] = null;
        ElMessage.success(t('apiDebug.deleted'));
        await sendRequest(ep);
    } catch (err) {
        const axiosErr = err as AxiosError;
        const detail = axiosErr.response?.data;
        ElMessage.error(typeof detail === 'object' && detail && 'detail' in detail
            ? String((detail as { detail: unknown }).detail)
            : t('apiDebug.deleteFailed'));
    } finally {
        rowActionLoading[ep.id] = false;
    }
};

type AsyncJobStatus = {
    job_id: string;
    status: 'pending' | 'running' | 'done' | 'failed';
    files_done?: number;
    files_total?: number;
    chunks?: number;
    error?: string | null;
    result?: unknown;
};

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

const pollAsyncJob = async (
    ep: ApiEndpoint,
    cfg: ApiAsyncJobConfig,
    jobId: string,
): Promise<AsyncJobStatus> => {
    const interval = cfg.pollIntervalMs ?? 1500;
    const timeout = cfg.timeoutMs ?? 600_000;
    const started = Date.now();
    while (Date.now() - started < timeout) {
        const statusPath = cfg.statusPath.replace('{job_id}', encodeURIComponent(jobId));
        const { data } = await request.get<AsyncJobStatus>(statusPath);
        responses[ep.id] = formatJson(data);
        const done = data.files_done ?? 0;
        const total = data.files_total ?? 0;
        statusInfo[ep.id] = {
            ok: true,
            text: t('apiDebug.asyncJobPolling', {
                status: data.status,
                progress: total > 0 ? `${done}/${total}` : data.status,
            }),
        };
        if (data.status === 'done' || data.status === 'failed') {
            return data;
        }
        await sleep(interval);
    }
    throw new Error('job_timeout');
};

const formatErrorDetail = (data: unknown): string => {
    if (typeof data === 'string' && data.trim()) return data;
    if (data && typeof data === 'object') {
        if ('detail' in data) {
            const detail = (data as { detail: unknown }).detail;
            if (typeof detail === 'string' && detail.trim()) return detail;
            if (Array.isArray(detail)) {
                const parts = detail.map((item) => {
                    if (typeof item === 'string') return item;
                    if (item && typeof item === 'object' && 'msg' in item) {
                        return String((item as { msg: unknown }).msg);
                    }
                    return '';
                }).filter(Boolean);
                if (parts.length) return parts.join('；');
            }
            if (detail != null) return String(detail);
        }
        if ('message' in data && (data as { message: unknown }).message != null) {
            return String((data as { message: unknown }).message);
        }
    }
    return t('apiDebug.networkError');
};

const isBlank = (v: FormValue) => v === null || v === undefined || v === '';

const validateRequest = (ep: ApiEndpoint): string | null => {
    for (const p of ep.pathParams ?? []) {
        if (p.required && isBlank(formState[ep.id].path[p.name])) {
            return `请填写${p.label}`;
        }
    }
    for (const p of ep.queryParams ?? []) {
        if (p.required && isBlank(formState[ep.id].query[p.name])) {
            return `请填写${p.label}`;
        }
    }
    for (const p of ep.bodyParams ?? []) {
        if (p.required && isBlank(formState[ep.id].body[p.name])) {
            return `请填写${p.label}`;
        }
    }
    if (ep.id === 'corpora-import') {
        const file = formState[ep.id].form.file;
        if (!(file instanceof File)) {
            return '请上传文档/.zip';
        }
    }
    for (const p of ep.formParams ?? []) {
        if (!p.required) continue;
        const raw = formState[ep.id].form[p.name];
        if (p.type === 'file') {
            if (!(raw instanceof File)) return `请选择${p.label}`;
        } else if (isBlank(raw)) {
            return `请填写${p.label}`;
        }
    }
    return null;
};

const sendRequest = async (ep: ApiEndpoint) => {
    const invalid = validateRequest(ep);
    if (invalid) {
        ElMessage.warning(invalid);
        statusInfo[ep.id] = { ok: false, text: invalid };
        return;
    }

    loading[ep.id] = true;
    statusInfo[ep.id] = { ok: true, text: t('apiDebug.requesting') };

    try {
        let res;
        const method = ep.method.toLowerCase() as 'get' | 'post' | 'put' | 'delete';
        const path = buildPath(ep);

        if (ep.formParams?.length) {
            res = await request.post(path, buildFormData(ep));
        } else if (method === 'get' || method === 'delete') {
            res = await request[method](path, { params: buildQueryParams(ep) });
        } else {
            res = await request[method](path, buildBody(ep), { params: buildQueryParams(ep) });
        }

        let payload: unknown = res.data;
        const jobId =
            ep.asyncJob &&
            payload &&
            typeof payload === 'object' &&
            'job_id' in payload &&
            typeof (payload as { job_id: unknown }).job_id === 'string'
                ? (payload as { job_id: string }).job_id
                : null;

        if (ep.asyncJob && jobId) {
            ElMessage.info(t('apiDebug.asyncJobAccepted', { jobId }));
            responses[ep.id] = formatJson(payload);
            statusInfo[ep.id] = { ok: true, text: t('apiDebug.asyncJobSubmitted') };
            const final = await pollAsyncJob(ep, ep.asyncJob, jobId);
            payload = final;
            if (final.status === 'done') {
                ElMessage.success(
                    t('apiDebug.asyncJobDone', {
                        files: final.files_done ?? 0,
                        chunks: final.chunks ?? 0,
                    }),
                );
            } else {
                ElMessage.error(final.error || t('apiDebug.asyncJobFailed'));
            }
        }

        responses[ep.id] = ep.resultView?.mode === 'content'
            ? applyContentView(ep, payload)
            : formatJson(payload);
        applyResultView(ep, payload);
        selectedRow[ep.id] = null;
        const failed =
            payload &&
            typeof payload === 'object' &&
            'status' in payload &&
            (payload as { status: string }).status === 'failed';
        statusInfo[ep.id] = {
            ok: !failed,
            text: failed
                ? t('apiDebug.asyncJobFailed')
                : `HTTP ${res.status}${jobId ? ` · ${t('apiDebug.asyncJobFinished')}` : ''}`,
        };
    } catch (err) {
        if (err instanceof Error && err.message === 'job_timeout') {
            responses[ep.id] = formatJson({ error: t('apiDebug.asyncJobTimeout') });
            statusInfo[ep.id] = { ok: false, text: t('apiDebug.asyncJobTimeout') };
            ElMessage.error(t('apiDebug.asyncJobTimeout'));
            return;
        }
        const axiosErr = err as AxiosError;
        const status = axiosErr.response?.status;
        const detail = axiosErr.response?.data ?? { message: axiosErr.message || '请求失败' };
        const errMsg = formatErrorDetail(detail);
        responses[ep.id] = formatJson(detail);
        tableState[ep.id] = { rows: [], highlights: {}, page: 1, total: 0, serverPaging: false };
        contentState[ep.id] = { content: '' };
        statusInfo[ep.id] = {
            ok: false,
            text: status ? `HTTP ${status} · ${errMsg}` : errMsg,
        };
        ElMessage.error(errMsg);
    } finally {
        loading[ep.id] = false;
    }
};
</script>

<style scoped>
.api-debug-panel {
    width: 100%;
}

.tab-label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.method-tag {
    font-weight: 600;
}

.endpoint-header {
    margin-bottom: 16px;
}

.endpoint-path {
    font-size: 13px;
    color: #606266;
    background: #f5f7fa;
    padding: 4px 10px;
    border-radius: 4px;
    display: inline-block;
}

.endpoint-desc {
    margin: 8px 0 0;
    color: #909399;
    font-size: 13px;
}

.example-list {
    margin-bottom: 12px;
}

.example-item {
    margin-bottom: 10px;
    padding: 10px 12px;
    background: #f5f7fa;
    border: 1px solid #ebeef5;
    border-radius: 4px;
}

.example-item.active {
    border-color: #409eff;
    background: #ecf5ff;
}

.example-item-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}

.example-text {
    margin: 0;
    font-size: 13px;
    line-height: 1.6;
    color: #303133;
    white-space: pre-wrap;
    word-break: break-word;
    user-select: all;
    cursor: text;
}

.param-section-title {
    font-size: 13px;
    color: #909399;
    margin: 8px 0 4px;
    padding-bottom: 4px;
    border-bottom: 1px solid #ebeef5;
}

.param-form {
    margin-bottom: 12px;
}

.send-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
}

.status-info {
    font-size: 13px;
}

.status-info.ok {
    color: #67c23a;
}

.status-info.err {
    color: #f56c6c;
}

.result-table-wrap {
    margin-bottom: 12px;
}

.highlight-block {
    margin-bottom: 12px;
    padding: 10px 12px;
    background: #f5f7fa;
    border-radius: 4px;
}

.highlight-label {
    font-size: 13px;
    color: #909399;
    margin-bottom: 6px;
}

.highlight-content {
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 13px;
    line-height: 1.6;
    color: #303133;
}

.result-content-list {
    margin-bottom: 12px;
}

.result-content-item {
    margin-bottom: 10px;
}

.content-result-block {
    margin-bottom: 12px;
}

.result-table {
    width: 100%;
}

.result-table :deep(.el-table__header),
.result-table :deep(.el-table__body),
.result-table :deep(table) {
    table-layout: auto !important;
    width: 100% !important;
}

.result-table :deep(.el-table__cell) {
    text-align: left;
}

/* 前面列：按内容撑开、单行不折 */
.result-table :deep(th.col-fit),
.result-table :deep(td.col-fit) {
    width: 1%;
    white-space: nowrap;
}

.result-table :deep(th.col-fit .cell),
.result-table :deep(td.col-fit .cell) {
    white-space: nowrap;
}

/* 最后列：吃掉剩余宽度，长文本省略（悬停仍看全文） */
.result-table :deep(th.col-fill),
.result-table :deep(td.col-fill) {
    width: 99%;
}

.result-table :deep(td.col-fill .cell) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.result-pagination {
    margin-top: 12px;
    justify-content: flex-end;
}

.row-actions-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
    padding: 10px 12px;
    background: #fafafa;
    border: 1px solid #ebeef5;
    border-radius: 4px;
}

.selected-hint {
    font-size: 13px;
    color: #606266;
}

.selected-hint.muted {
    color: #909399;
}

.row-actions-btns {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.response-box :deep(textarea) {
    font-family: Consolas, Monaco, 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.5;
}

:deep(.el-tabs__content) {
    padding: 16px 4px 4px;
}
</style>

<!-- tooltip 挂到 body，需非 scoped -->
<style>
.api-debug-long-tooltip {
    width: min(800px, 90vw) !important;
    max-width: min(800px, 90vw) !important;
    height: auto;
    max-height: 70vh;
    overflow: auto;
    white-space: pre-wrap !important;
    word-break: break-word;
    line-height: 1.55;
    font-size: 13px;
}
</style>
