<template>
    <div class="container error-logs-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <span class="page-title">{{ t('pages.errorLogs.title') }}</span>
                    <el-button type="primary" :loading="loading" @click="loadLogs">{{ t('common.refresh') }}</el-button>
                </div>
            </template>

            <el-form :inline="true" :model="query" class="filter-form" @submit.prevent>
                <el-form-item :label="t('pages.errorLogs.source')">
                    <el-input v-model="query.source" clearable style="width: 160px" />
                </el-form-item>
                <el-form-item :label="t('pages.errorLogs.level')">
                    <el-select v-model="query.level" clearable style="width: 110px">
                        <el-option label="error" value="error" />
                        <el-option label="warning" value="warning" />
                    </el-select>
                </el-form-item>
                <el-form-item :label="t('pages.errorLogs.status')">
                    <el-select v-model="query.status" clearable style="width: 110px">
                        <el-option :label="t('pages.errorLogs.open')" value="open" />
                        <el-option :label="t('pages.errorLogs.resolved')" value="resolved" />
                    </el-select>
                </el-form-item>
                <el-form-item :label="t('pages.errorLogs.range')">
                    <el-select v-model="query.days" clearable style="width: 120px">
                        <el-option :label="t('pages.errorLogs.days7')" :value="7" />
                        <el-option :label="t('pages.errorLogs.days30')" :value="30" />
                        <el-option :label="t('pages.errorLogs.days90')" :value="90" />
                    </el-select>
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleSearch">{{ t('common.search') }}</el-button>
                </el-form-item>
            </el-form>

            <el-table :data="items" v-loading="loading" stripe :empty-text="t('pages.errorLogs.empty')">
                <el-table-column prop="id" label="ID" width="70" />
                <el-table-column prop="created_at" :label="t('pages.errorLogs.time')" width="175" />
                <el-table-column prop="level" :label="t('pages.errorLogs.level')" width="90" />
                <el-table-column prop="source" :label="t('pages.errorLogs.source')" width="150" show-overflow-tooltip />
                <el-table-column prop="error_type" :label="t('pages.errorLogs.errorType')" width="140" show-overflow-tooltip />
                <el-table-column prop="message" :label="t('pages.errorLogs.message')" min-width="220" show-overflow-tooltip />
                <el-table-column prop="path" :label="t('pages.errorLogs.path')" width="160" show-overflow-tooltip />
                <el-table-column prop="status" :label="t('pages.errorLogs.status')" width="100">
                    <template #default="{ row }">
                        <el-tag :type="row.status === 'resolved' ? 'success' : 'danger'">
                            {{ row.status === 'resolved' ? t('pages.errorLogs.resolved') : t('pages.errorLogs.open') }}
                        </el-tag>
                    </template>
                </el-table-column>
                <el-table-column :label="t('pages.errorLogs.actions')" width="160" fixed="right">
                    <template #default="{ row }">
                        <el-button link type="primary" @click="showDetail(row)">{{ t('pages.errorLogs.detail') }}</el-button>
                        <el-button
                            v-if="row.status === 'open'"
                            link
                            type="success"
                            @click="markResolved(row.id)"
                        >
                            {{ t('pages.errorLogs.markResolved') }}
                        </el-button>
                    </template>
                </el-table-column>
            </el-table>

            <el-pagination
                class="pager"
                background
                layout="total, prev, pager, next"
                :total="page.total"
                :page-size="page.size"
                :current-page="page.index"
                @current-change="changePage"
            />
        </el-card>

        <el-dialog v-model="detailVisible" :title="t('pages.errorLogs.detailTitle')" width="720px">
            <pre class="detail-pre">{{ detailText }}</pre>
        </el-dialog>
    </div>
</template>

<script setup lang="ts" name="system-error-logs">
import { onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { fetchAppErrorLogs, patchAppErrorLogStatus } from '@/api';

interface ErrorRow {
    id: number;
    created_at: string;
    level: string;
    source: string;
    error_type: string;
    message: string;
    detail?: string | null;
    path?: string | null;
    status: string;
}

const { t } = useI18n();
const loading = ref(false);
const items = ref<ErrorRow[]>([]);
const page = reactive({ index: 1, size: 50, total: 0 });
const query = reactive({
    source: '',
    level: '' as string | '',
    status: 'open' as string | '',
    days: 30 as number | null,
});
const detailVisible = ref(false);
const detailText = ref('');

async function loadLogs() {
    loading.value = true;
    try {
        const { data } = await fetchAppErrorLogs({
            page: page.index,
            page_size: page.size,
            source: query.source || undefined,
            level: query.level || undefined,
            status: query.status || undefined,
            days: query.days,
        });
        items.value = data.items;
        page.total = data.total;
    } catch {
        items.value = [];
        page.total = 0;
        ElMessage.error(t('pages.errorLogs.loadFailed'));
    } finally {
        loading.value = false;
    }
}

function handleSearch() {
    page.index = 1;
    loadLogs();
}

function changePage(val: number) {
    page.index = val;
    loadLogs();
}

function showDetail(row: ErrorRow) {
    detailText.value = row.detail || row.message || '—';
    detailVisible.value = true;
}

async function markResolved(id: number) {
    try {
        await patchAppErrorLogStatus(id, 'resolved');
        ElMessage.success(t('pages.errorLogs.resolveDone'));
        await loadLogs();
    } catch {
        ElMessage.error(t('pages.errorLogs.resolveFailed'));
    }
}

onMounted(loadLogs);
</script>

<style scoped>
.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.page-title {
    font-weight: 600;
}
.filter-form {
    margin-bottom: 12px;
}
.pager {
    margin-top: 16px;
    justify-content: flex-end;
}
.detail-pre {
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 480px;
    overflow: auto;
    font-size: 12px;
    line-height: 1.5;
}
</style>
