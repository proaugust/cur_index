<template>
    <div class="container api-access-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <span class="page-title">{{ t('pages.apiAccess.title') }}</span>
                    <el-button type="primary" :loading="loading" @click="loadStats">{{ t('common.refresh') }}</el-button>
                </div>
            </template>

            <el-form :inline="true" :model="query" class="filter-form" @submit.prevent>
                <el-form-item :label="t('pages.apiAccess.username')">
                    <el-input v-model="query.username" clearable style="width: 160px" />
                </el-form-item>
                <el-form-item :label="t('pages.apiAccess.range')">
                    <el-select v-model="query.days" clearable style="width: 120px">
                        <el-option :label="t('pages.apiAccess.days7')" :value="7" />
                        <el-option :label="t('pages.apiAccess.days30')" :value="30" />
                        <el-option :label="t('pages.apiAccess.days90')" :value="90" />
                    </el-select>
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleSearch">{{ t('common.search') }}</el-button>
                </el-form-item>
            </el-form>

            <el-table :data="items" v-loading="loading" stripe :empty-text="t('pages.apiAccess.empty')">
                <el-table-column prop="username" :label="t('pages.apiAccess.username')" width="140" show-overflow-tooltip />
                <el-table-column prop="method" :label="t('pages.apiAccess.method')" width="90" />
                <el-table-column prop="path" :label="t('pages.apiAccess.path')" min-width="240" show-overflow-tooltip />
                <el-table-column prop="hit_count" :label="t('pages.apiAccess.hits')" width="90" />
                <el-table-column prop="last_status" :label="t('pages.apiAccess.status')" width="90" />
                <el-table-column :label="t('pages.apiAccess.lastAt')" width="180">
                    <template #default="{ row }">{{ formatDateTime(row.last_at) }}</template>
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
import { formatDateTime } from '@/utils';

interface AccessRow {
    id: number;
    user_id: number;
    username: string;
    method: string;
    path: string;
    hit_count: number;
    last_status: number;
    last_at: string;
}

const { t } = useI18n();
const loading = ref(false);
const items = ref<AccessRow[]>([]);
const page = reactive({ index: 1, size: 50, total: 0 });
const query = reactive({
    username: '',
    days: 30 as number | null,
});

async function loadStats() {
    loading.value = true;
    try {
        const { data } = await fetchApiAccessStats({
            page: page.index,
            page_size: page.size,
            username: query.username || undefined,
            days: query.days,
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

function handleSearch() {
    page.index = 1;
    loadStats();
}

function changePage(val: number) {
    page.index = val;
    loadStats();
}

onMounted(loadStats);
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
