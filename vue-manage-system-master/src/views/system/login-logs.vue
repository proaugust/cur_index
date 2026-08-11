<template>
    <div class="container login-logs-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <span class="page-title">{{ t('pages.loginLogs.title') }}</span>
                    <el-button type="primary" :loading="loading" @click="loadLogs">{{ t('common.refresh') }}</el-button>
                </div>
            </template>

            <el-form :inline="true" :model="query" class="filter-form" @submit.prevent>
                <el-form-item :label="t('pages.loginLogs.username')">
                    <el-input v-model="query.username" clearable style="width: 160px" />
                </el-form-item>
                <el-form-item :label="t('pages.loginLogs.range')">
                    <el-select v-model="query.days" clearable style="width: 120px">
                        <el-option :label="t('pages.loginLogs.days7')" :value="7" />
                        <el-option :label="t('pages.loginLogs.days30')" :value="30" />
                        <el-option :label="t('pages.loginLogs.days90')" :value="90" />
                    </el-select>
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleSearch">{{ t('common.search') }}</el-button>
                </el-form-item>
            </el-form>

            <el-table :data="items" v-loading="loading" stripe :empty-text="t('pages.loginLogs.empty')">
                <el-table-column prop="id" label="ID" width="70" />
                <el-table-column prop="username" :label="t('pages.loginLogs.username')" width="140" show-overflow-tooltip />
                <el-table-column prop="ip" :label="t('pages.loginLogs.ip')" width="150" show-overflow-tooltip />
                <el-table-column :label="t('pages.loginLogs.time')" width="180">
                    <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
                </el-table-column>
                <el-table-column prop="user_agent" :label="t('pages.loginLogs.userAgent')" min-width="240" show-overflow-tooltip />
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

<script setup lang="ts" name="system-login-logs">
import { onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { fetchLoginLogs } from '@/api';
import { formatDateTime } from '@/utils';

interface LoginRow {
    id: number;
    user_id?: number | null;
    username: string;
    ip: string;
    user_agent?: string | null;
    created_at: string;
}

const { t } = useI18n();
const loading = ref(false);
const items = ref<LoginRow[]>([]);
const page = reactive({ index: 1, size: 50, total: 0 });
const query = reactive({
    username: '',
    days: 30 as number | null,
});

async function loadLogs() {
    loading.value = true;
    try {
        const { data } = await fetchLoginLogs({
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
        ElMessage.error(t('pages.loginLogs.loadFailed'));
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
</style>
