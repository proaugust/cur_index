<template>
    <div class="container api-access-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <span class="page-title">{{ t('pages.apiAccess.title') }}</span>
                    <el-button type="primary" :loading="loading" @click="load(true)">{{ t('common.refresh') }}</el-button>
                </div>
            </template>

            <el-form :inline="true" :model="query" class="filter-form" @submit.prevent>
                <el-form-item :label="t('pages.apiAccess.username')">
                    <el-input v-model="query.username" clearable style="width: 140px" />
                </el-form-item>
                <el-form-item :label="t('pages.apiAccess.time')">
                    <el-date-picker
                        v-model="query.timeRange"
                        type="datetimerange"
                        value-format="YYYY-MM-DDTHH:mm:ss"
                        range-separator="至"
                        :start-placeholder="t('pages.apiAccess.time')"
                        :end-placeholder="t('pages.apiAccess.time')"
                        clearable
                    />
                </el-form-item>
                <el-form-item :label="t('pages.apiAccess.page')">
                    <el-input v-model="query.pageName" clearable style="width: 140px" />
                </el-form-item>
                <el-form-item :label="t('pages.apiAccess.path')">
                    <el-input v-model="query.path" clearable style="width: 160px" />
                </el-form-item>
                <el-form-item :label="t('pages.apiAccess.method')">
                    <el-select v-model="query.method" clearable style="width: 110px">
                        <el-option v-for="item in methods" :key="item" :label="item" :value="item" />
                    </el-select>
                </el-form-item>
                <el-form-item :label="t('pages.apiAccess.hits')">
                    <el-input v-model="query.hitCount" clearable style="width: 90px" />
                </el-form-item>
                <el-form-item :label="t('pages.apiAccess.status')">
                    <el-input v-model="query.statusCode" clearable style="width: 90px" />
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleSearch">{{ t('common.search') }}</el-button>
                </el-form-item>
            </el-form>

            <el-table :data="items" v-loading="loading" stripe :empty-text="t('pages.apiAccess.empty')">
                <el-table-column prop="username" :label="t('pages.apiAccess.username')" width="120" show-overflow-tooltip />
                <el-table-column :label="t('pages.apiAccess.time')" width="180">
                    <template #default="{ row }">{{ formatDateTime(row.last_at) }}</template>
                </el-table-column>
                <el-table-column :label="t('pages.apiAccess.page')" min-width="180" show-overflow-tooltip>
                    <template #default="{ row }">{{ pageText(row) }}</template>
                </el-table-column>
                <el-table-column prop="path" :label="t('pages.apiAccess.path')" min-width="180" show-overflow-tooltip />
                <el-table-column prop="method" :label="t('pages.apiAccess.method')" width="90" />
                <el-table-column prop="hit_count" :label="t('pages.apiAccess.hits')" width="80" />
                <el-table-column :label="t('pages.apiAccess.status')" min-width="140" show-overflow-tooltip>
                    <template #default="{ row }">{{ resultText(row.statuses) }}</template>
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
    </div>
</template>

<script setup lang="ts" name="system-api-access">
import { onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { fetchApiAccessStats } from '@/api';
import router from '@/router';
import { formatDateTime } from '@/utils';

interface AccessRow {
    user_id: number;
    username: string;
    page: string;
    tab: string;
    method: string;
    path: string;
    hit_count: number;
    statuses: Record<string, number>;
    last_at: string;
}

const { t } = useI18n();
const methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'];
const loading = ref(false);
const items = ref<AccessRow[]>([]);
const page = reactive({ index: 1, size: 50, total: 0 });

function pad(n: number) {
    return String(n).padStart(2, '0');
}

function formatInput(d: Date) {
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function defaultTimeRange(): [string, string] {
    const end = new Date();
    const start = new Date(end.getTime() - 30 * 24 * 60 * 60 * 1000);
    return [formatInput(start), formatInput(end)];
}

function optionalInt(value: string) {
    const text = value.trim();
    if (!text || !/^\d+$/.test(text)) return undefined;
    return Number(text);
}

const query = reactive({
    username: '',
    timeRange: defaultTimeRange() as [string, string] | null,
    pageName: '',
    path: '',
    method: '',
    hitCount: '',
    statusCode: '',
});

async function load(refresh = false) {
    loading.value = true;
    try {
        const range = query.timeRange;
        const { data } = await fetchApiAccessStats({
            page: page.index,
            page_size: page.size,
            username: query.username || undefined,
            start: range?.[0],
            end: range?.[1],
            page_name: query.pageName || undefined,
            path: query.path || undefined,
            method: query.method || undefined,
            hit_count: optionalInt(query.hitCount),
            status_code: optionalInt(query.statusCode),
            refresh: refresh || undefined,
        });
        items.value = data.items;
        page.total = data.total;
    } catch {
        items.value = [];
        page.total = 0;
        ElMessage.error(t('pages.apiAccess.loadFailed'));
    } finally {
        loading.value = false;
    }
}

function routeTitle(path?: string | null) {
    if (!path) return '';
    const meta = router.resolve(path).meta;
    if (typeof meta?.titleKey === 'string') {
        const label = t(meta.titleKey);
        if (label && label !== meta.titleKey) return label;
    }
    return typeof meta?.title === 'string' ? meta.title : '';
}

function pageText(row: AccessRow) {
    const name = routeTitle(row.page) || row.page;
    if (name && row.tab) return `${name} / ${row.tab}`;
    return name || row.tab || '—';
}

function resultText(statuses?: Record<string, number>) {
    if (!statuses) return '';
    return Object.keys(statuses)
        .sort((a, b) => Number(a) - Number(b))
        .map((code) => `${code}×${statuses[code]}`)
        .join(' ');
}

function handleSearch() {
    page.index = 1;
    load(true);
}

function changePage(val: number) {
    page.index = val;
    load(true);
}

onMounted(() => load(true));
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
</style>
