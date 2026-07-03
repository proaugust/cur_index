<template>
    <div class="container llm-usage-page">
        <el-card shadow="hover" class="mgb20">
            <template #header>
                <div class="page-header">
                    <span class="page-title">{{ t('pages.llmUsage.title') }}</span>
                    <div class="page-toolbar">
                        <span class="toolbar-label">{{ t('pages.llmUsage.rangeLabel') }}</span>
                        <el-select v-model="days" style="width: 120px" @change="loadStats">
                            <el-option :label="t('pages.llmUsage.daysAll')" :value="null" />
                            <el-option :label="t('pages.llmUsage.days7')" :value="7" />
                            <el-option :label="t('pages.llmUsage.days30')" :value="30" />
                            <el-option :label="t('pages.llmUsage.days90')" :value="90" />
                        </el-select>
                        <el-button type="primary" :loading="loading" @click="loadAll">{{ t('common.refresh') }}</el-button>
                    </div>
                </div>
            </template>

            <el-row :gutter="16" class="summary-row">
                <el-col :xs="12" :sm="6">
                    <el-statistic :title="t('pages.llmUsage.totalTokens')" :value="stats.total_tokens" />
                </el-col>
                <el-col :xs="12" :sm="6">
                    <el-statistic :title="t('pages.llmUsage.totalCalls')" :value="stats.total_calls" />
                </el-col>
                <el-col :xs="12" :sm="6">
                    <el-statistic :title="t('pages.llmUsage.promptTokens')" :value="stats.total_prompt_tokens" />
                </el-col>
                <el-col :xs="12" :sm="6">
                    <el-statistic :title="t('pages.llmUsage.completionTokens')" :value="stats.total_completion_tokens" />
                </el-col>
            </el-row>
        </el-card>

        <el-card shadow="hover" class="mgb20" v-loading="loading">
            <template #header>
                <span>{{ t('pages.llmUsage.byUser') }}</span>
            </template>
            <el-table :data="stats.by_user" stripe class="summary-table" :fit="false" :empty-text="t('pages.llmUsage.emptyData')">
                <el-table-column prop="username" :label="t('pages.llmUsage.user')" width="110" show-overflow-tooltip />
                <el-table-column prop="calls" :label="t('pages.llmUsage.calls')" width="96" align="right" />
                <el-table-column prop="prompt_tokens" label="Prompt" width="108" align="right" />
                <el-table-column prop="completion_tokens" label="Completion" width="120" align="right" />
                <el-table-column prop="total_tokens" :label="t('pages.llmUsage.totalTokens')" width="108" align="right" sortable />
                <el-table-column :label="t('pages.llmUsage.share')" width="80" align="right">
                    <template #default="{ row }">{{ row.share_percent }}%</template>
                </el-table-column>
            </el-table>
        </el-card>

        <el-card shadow="hover" class="mgb20" v-loading="loading">
            <template #header>
                <span>{{ t('pages.llmUsage.byCaller') }}</span>
            </template>
            <el-table :data="stats.by_caller" stripe class="summary-table" :fit="false" :empty-text="t('pages.llmUsage.emptyData')">
                <el-table-column prop="caller" :label="t('pages.llmUsage.caller')" width="220" show-overflow-tooltip />
                <el-table-column prop="calls" :label="t('pages.llmUsage.calls')" width="96" align="right" />
                <el-table-column prop="prompt_tokens" label="Prompt" width="108" align="right" />
                <el-table-column prop="completion_tokens" label="Completion" width="120" align="right" />
                <el-table-column prop="total_tokens" :label="t('pages.llmUsage.totalTokens')" width="108" align="right" sortable />
                <el-table-column :label="t('pages.llmUsage.share')" width="80" align="right">
                    <template #default="{ row }">{{ row.share_percent }}%</template>
                </el-table-column>
            </el-table>
        </el-card>

        <el-card shadow="hover" v-loading="recentLoading">
            <template #header>
                <span>{{ t('pages.llmUsage.recent') }}</span>
            </template>

            <el-form :inline="true" :model="recentQuery" class="recent-filter" @submit.prevent>
                <el-form-item :label="t('pages.llmUsage.scene')">
                    <el-input v-model="recentQuery.caller" clearable :placeholder="t('pages.llmUsage.filterCaller')" style="width: 160px" />
                </el-form-item>
                <el-form-item :label="t('pages.llmUsage.user')">
                    <el-input v-model="recentQuery.username" clearable :placeholder="t('pages.llmUsage.filterUsername')" style="width: 140px" />
                </el-form-item>
                <el-form-item :label="t('pages.llmUsage.engine')">
                    <el-input v-model="recentQuery.engine" clearable :placeholder="t('pages.llmUsage.filterEngine')" style="width: 120px" />
                </el-form-item>
                <el-form-item :label="t('pages.llmUsage.success')">
                    <el-select v-model="recentQuery.success" clearable style="width: 100px" :placeholder="t('pages.llmUsage.all')">
                        <el-option :label="t('pages.llmUsage.yes')" :value="true" />
                        <el-option :label="t('pages.llmUsage.no')" :value="false" />
                    </el-select>
                </el-form-item>
                <el-form-item :label="t('pages.llmUsage.rangeLabel')">
                    <el-select v-model="recentQuery.days" clearable style="width: 120px" :placeholder="t('pages.llmUsage.all')">
                        <el-option :label="t('pages.llmUsage.days7')" :value="7" />
                        <el-option :label="t('pages.llmUsage.days30')" :value="30" />
                        <el-option :label="t('pages.llmUsage.days90')" :value="90" />
                    </el-select>
                </el-form-item>
                <el-form-item label="request_id">
                    <el-input v-model="recentQuery.request_id" clearable style="width: 160px" />
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleRecentSearch">{{ t('common.search') }}</el-button>
                    <el-button @click="resetRecentQuery">{{ t('pages.llmUsage.reset') }}</el-button>
                </el-form-item>
            </el-form>

            <el-table :data="recentItems" stripe :empty-text="t('pages.llmUsage.emptyRecords')">
                <el-table-column prop="id" label="ID" width="70" />
                <el-table-column prop="created_at" :label="t('pages.llmUsage.time')" width="175">
                    <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
                </el-table-column>
                <el-table-column prop="caller" :label="t('pages.llmUsage.scene')" min-width="160" show-overflow-tooltip />
                <el-table-column prop="username" :label="t('pages.llmUsage.user')" width="120" show-overflow-tooltip>
                    <template #default="{ row }">
                        {{ row.username || (row.user_id ? t('pages.llmUsage.userId', { id: row.user_id }) : '—') }}
                    </template>
                </el-table-column>
                <el-table-column prop="engine" :label="t('pages.llmUsage.engine')" width="90" />
                <el-table-column prop="total_tokens" label="Token" width="90" align="right" />
                <el-table-column prop="latency_ms" :label="t('pages.llmUsage.latency')" width="100" align="right" />
                <el-table-column :label="t('pages.llmUsage.success')" width="70" align="center">
                    <template #default="{ row }">
                        <el-tag :type="row.success ? 'success' : 'danger'">
                            {{ row.success ? t('pages.llmUsage.yes') : t('pages.llmUsage.no') }}
                        </el-tag>
                    </template>
                </el-table-column>
                <el-table-column prop="request_id" label="request_id" min-width="140" show-overflow-tooltip />
            </el-table>

            <div class="recent-pagination">
                <el-pagination
                    v-model:current-page="recentPage.index"
                    v-model:page-size="recentPage.size"
                    :page-sizes="[50, 200, 500, 2000]"
                    :total="recentPage.total"
                    layout="total, sizes, prev, pager, next, jumper"
                    background
                    @current-change="loadRecent"
                    @size-change="handleRecentSizeChange"
                />
            </div>
        </el-card>
    </div>
</template>

<script setup lang="ts" name="system-llm-usage">
import { onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { fetchLlmUsageRecent, fetchLlmUsageStats } from '@/api';

const { t } = useI18n();

interface CallerStats {
    caller: string;
    calls: number;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    share_percent: number;
}

interface UserStats {
    user_id: number | null;
    username: string;
    calls: number;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    share_percent: number;
}

interface UsageStats {
    days: number | null;
    total_calls: number;
    total_prompt_tokens: number;
    total_completion_tokens: number;
    total_tokens: number;
    by_caller: CallerStats[];
    by_user: UserStats[];
}

interface UsageLogItem {
    id: number;
    caller: string;
    engine: string;
    model: string;
    request_id: string | null;
    user_id: number | null;
    username: string | null;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    latency_ms: number;
    success: boolean;
    created_at: string;
}

const loading = ref(false);
const recentLoading = ref(false);
const days = ref<number | null>(null);
const stats = reactive<UsageStats>({
    days: null,
    total_calls: 0,
    total_prompt_tokens: 0,
    total_completion_tokens: 0,
    total_tokens: 0,
    by_caller: [],
    by_user: [],
});
const recentItems = ref<UsageLogItem[]>([]);
const recentQuery = reactive({
    caller: '',
    username: '',
    engine: '',
    success: null as boolean | null,
    request_id: '',
    days: null as number | null,
});
const recentPage = reactive({
    index: 1,
    size: 200,
    total: 0,
});

const formatTime = (value: string) => {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
};

const buildRecentParams = () => {
    const params: Record<string, unknown> = {
        page: recentPage.index,
        page_size: recentPage.size,
        exclude_warmup: true,
    };
    if (recentQuery.caller.trim()) params.caller = recentQuery.caller.trim();
    if (recentQuery.username.trim()) params.username = recentQuery.username.trim();
    if (recentQuery.engine.trim()) params.engine = recentQuery.engine.trim();
    if (recentQuery.request_id.trim()) params.request_id = recentQuery.request_id.trim();
    if (recentQuery.success !== null) params.success = recentQuery.success;
    if (recentQuery.days !== null) params.days = recentQuery.days;
    return params;
};

const loadStats = async () => {
    loading.value = true;
    try {
        const params: { exclude_warmup: boolean; days?: number } = { exclude_warmup: true };
        if (days.value !== null) params.days = days.value;
        const res = await fetchLlmUsageStats(params);
        Object.assign(stats, res.data);
    } catch {
        ElMessage.error(t('pages.llmUsage.loadStatsFailed'));
    } finally {
        loading.value = false;
    }
};

const loadRecent = async () => {
    recentLoading.value = true;
    try {
        const res = await fetchLlmUsageRecent(buildRecentParams());
        recentItems.value = res.data.items ?? [];
        recentPage.total = res.data.total ?? 0;
    } catch {
        ElMessage.error(t('pages.llmUsage.loadRecentFailed'));
    } finally {
        recentLoading.value = false;
    }
};

const handleRecentSearch = () => {
    recentPage.index = 1;
    loadRecent();
};

const handleRecentSizeChange = () => {
    recentPage.index = 1;
    loadRecent();
};

const resetRecentQuery = () => {
    recentQuery.caller = '';
    recentQuery.username = '';
    recentQuery.engine = '';
    recentQuery.success = null;
    recentQuery.request_id = '';
    recentQuery.days = null;
    handleRecentSearch();
};

const loadAll = async () => {
    await Promise.all([loadStats(), loadRecent()]);
};

onMounted(() => {
    loadAll();
});
</script>

<style scoped>
.llm-usage-page {
    --el-font-size-extra-small: 13px;
    --el-font-size-small: 14px;
    --el-font-size-base: 15px;
    --el-font-size-medium: 17px;
    --el-font-size-large: 19px;
    --el-font-size-extra-large: 21px;
}

.llm-usage-page .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
}

.page-title {
    font-size: 18px;
    font-weight: 600;
}

.page-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
}

.toolbar-label {
    color: var(--el-text-color-secondary);
    font-size: 14px;
}

.summary-row {
    margin-top: 4px;
}

.summary-table {
    width: auto !important;
    max-width: 100%;
}

.recent-filter {
    margin-bottom: 12px;
}

.recent-pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
}

.mgb20 {
    margin-bottom: 20px;
}
</style>
