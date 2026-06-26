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
                        </span>
                    </template>

                    <div class="endpoint-header">
                        <code class="endpoint-path">{{ ep.path }}</code>
                        <p v-if="ep.description" class="endpoint-desc">{{ ep.description }}</p>
                    </div>

                    <el-form label-width="120px" class="param-form" @submit.prevent>
                        <template v-if="ep.pathParams?.length">
                            <div class="param-section-title">Path 参数</div>
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
                            <div class="param-section-title">Query 参数</div>
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
                            <div class="param-section-title">Body 参数</div>
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
                            <div class="param-section-title">Form 参数</div>
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
                                    <el-button size="small">选择文件</el-button>
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
                            发送
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
                                :width="col.width"
                                :min-width="col.minWidth"
                                :show-overflow-tooltip="col.showOverflowTooltip"
                            />
                        </el-table>

                        <el-pagination
                            v-if="tableState[ep.id].rows.length > (ep.resultView.pageSize ?? 10)"
                            class="result-pagination"
                            background
                            layout="total, prev, pager, next"
                            :total="tableState[ep.id].rows.length"
                            :page-size="ep.resultView.pageSize ?? 10"
                            v-model:current-page="tableState[ep.id].page"
                        />

                        <div v-if="ep.resultView.rowActions" class="row-actions-bar">
                            <span v-if="selectedRow[ep.id]" class="selected-hint">
                                已选 ID: {{ selectedRow[ep.id]?.[ep.resultView.rowActions.idField ?? 'id'] }}
                            </span>
                            <span v-else class="selected-hint muted">点击表格行以选中切块</span>
                            <div class="row-actions-btns">
                                <el-button
                                    size="small"
                                    type="warning"
                                    :disabled="!selectedRow[ep.id]"
                                    :loading="rowActionLoading[ep.id]"
                                    @click="openEditDialog(ep)"
                                >
                                    编辑选中
                                </el-button>
                                <el-button
                                    size="small"
                                    type="danger"
                                    :disabled="!selectedRow[ep.id]"
                                    :loading="rowActionLoading[ep.id]"
                                    @click="deleteSelectedRow(ep)"
                                >
                                    删除选中
                                </el-button>
                                <el-button
                                    size="small"
                                    type="primary"
                                    :loading="rowActionLoading[ep.id]"
                                    @click="openCreateDialog(ep)"
                                >
                                    新增切块
                                </el-button>
                            </div>
                        </div>
                    </div>

                    <div
                        v-if="ep.resultView?.mode === 'content' && contentState[ep.id]?.content"
                        class="highlight-block content-result-block"
                    >
                        <div class="highlight-label">{{ ep.resultView.contentLabel ?? '正文' }}</div>
                        <div class="highlight-content">{{ contentState[ep.id].content }}</div>
                    </div>

                    <div
                        v-if="ep.resultView?.mode === 'content' && responses[ep.id]"
                        class="param-section-title"
                    >
                        元数据
                    </div>
                    <el-input
                        v-model="responses[ep.id]"
                        type="textarea"
                        :rows="ep.resultView?.mode === 'table' || ep.resultView?.mode === 'content' ? 12 : 28"
                        readonly
                        :placeholder="ep.resultView?.mode === 'content' ? '响应元数据 JSON 将显示在这里' : '响应 JSON 将显示在这里'"
                        class="response-box"
                    />
                </el-tab-pane>
            </el-tabs>
        </el-card>

        <el-dialog
            v-model="dialogVisible"
            :title="dialogMode === 'edit' ? '编辑切块' : '新增切块'"
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
                <el-button @click="dialogVisible = false">取消</el-button>
                <el-button type="primary" :loading="dialogSubmitting" @click="submitDialog">
                    确定
                </el-button>
            </template>
        </el-dialog>
    </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { UploadFile } from 'element-plus';
import type { AxiosError } from 'axios';
import request from '@/utils/request';
import type { ApiEndpoint, ApiParam } from '@/config/api-endpoints';

const props = defineProps<{
    endpoints: ApiEndpoint[];
}>();

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

    formState[ep.id] = state;
    responses[ep.id] = '';
    tableState[ep.id] = { rows: [], highlights: {}, page: 1 };
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
        tableState[ep.id] = { rows: [], highlights: {}, page: 1 };
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

    tableState[ep.id] = { rows, highlights, page: 1 };
};

const pagedRows = (ep: ApiEndpoint) => {
    const state = tableState[ep.id];
    if (!state || !ep.resultView) return [];
    const pageSize = ep.resultView.pageSize ?? 10;
    const start = (state.page - 1) * pageSize;
    return state.rows.slice(start, start + pageSize);
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
    dialogVisible.value = true;
};

const submitDialog = async () => {
    const ep = dialogEp.value;
    const actions = ep?.resultView?.rowActions;
    if (!ep || !actions) return;

    dialogSubmitting.value = true;
    rowActionLoading[ep.id] = true;
    try {
        if (dialogMode.value === 'edit') {
            const row = selectedRow[ep.id];
            const idField = actions.idField ?? 'id';
            const chunkId = row?.[idField];
            if (chunkId === undefined || chunkId === null) {
                ElMessage.warning('请先选中一条切块');
                return;
            }
            const body = buildFieldsBody(actions.editableFields, dialogForm);
            const path = replacePathId(actions.updatePath, chunkId as number | string);
            await request.put(path, body);
            ElMessage.success('已更新');
        } else {
            const body = buildFieldsBody(actions.createFields, dialogForm);
            if (!body.source_file || !body.content) {
                ElMessage.warning('文件名和正文为必填');
                return;
            }
            if (body.chunk_index !== undefined) {
                body.chunk_index = Number(body.chunk_index);
            }
            await request.post(actions.createPath, body);
            ElMessage.success('已新增');
        }
        dialogVisible.value = false;
        await sendRequest(ep);
    } catch (err) {
        const axiosErr = err as AxiosError;
        const detail = axiosErr.response?.data;
        ElMessage.error(typeof detail === 'object' && detail && 'detail' in detail
            ? String((detail as { detail: unknown }).detail)
            : '操作失败');
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
        await ElMessageBox.confirm(`确定删除切块 ID ${chunkId}？`, '删除确认', {
            type: 'warning',
            confirmButtonText: '删除',
            cancelButtonText: '取消',
        });
    } catch {
        return;
    }

    rowActionLoading[ep.id] = true;
    try {
        const path = replacePathId(actions.deletePath, chunkId as number | string);
        await request.delete(path);
        selectedRow[ep.id] = null;
        ElMessage.success('已删除');
        await sendRequest(ep);
    } catch (err) {
        const axiosErr = err as AxiosError;
        const detail = axiosErr.response?.data;
        ElMessage.error(typeof detail === 'object' && detail && 'detail' in detail
            ? String((detail as { detail: unknown }).detail)
            : '删除失败');
    } finally {
        rowActionLoading[ep.id] = false;
    }
};

const sendRequest = async (ep: ApiEndpoint) => {
    loading[ep.id] = true;
    statusInfo[ep.id] = { ok: true, text: '请求中...' };

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

        responses[ep.id] = ep.resultView?.mode === 'content'
            ? applyContentView(ep, res.data)
            : formatJson(res.data);
        applyResultView(ep, res.data);
        selectedRow[ep.id] = null;
        statusInfo[ep.id] = { ok: true, text: `HTTP ${res.status}` };
    } catch (err) {
        const axiosErr = err as AxiosError;
        const status = axiosErr.response?.status;
        const detail = axiosErr.response?.data ?? { message: axiosErr.message || '请求失败' };
        responses[ep.id] = formatJson(detail);
        tableState[ep.id] = { rows: [], highlights: {}, page: 1 };
        contentState[ep.id] = { content: '' };
        statusInfo[ep.id] = {
            ok: false,
            text: status ? `HTTP ${status}` : '网络错误',
        };
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

.content-result-block {
    margin-bottom: 12px;
}

.result-table {
    width: 100%;
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
