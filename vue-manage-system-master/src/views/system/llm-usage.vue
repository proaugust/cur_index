<template>
    <div class="container llm-usage-page">
        <el-card shadow="hover" class="mgb20">
            <template #header>
                <div class="page-header">
                    <span class="page-title">{{ t('pages.llmUsage.title') }}</span>
                    <div class="page-toolbar">
                        <span class="toolbar-label">{{ t('pages.llmUsage.rangeLabel') }}</span>
                        <el-select v-model="days" style="width: 120px" @change="loadStats">
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
            <el-table :data="stats.by_user" stripe size="small" :empty-text="t('pages.llmUsage.emptyData')">
                <el-table-column prop="username" :label="t('pages.llmUsage.user')" min-width="140" show-overflow-tooltip />
                <el-table-column prop="calls" :label="t('pages.llmUsage.calls')" width="100" align="right" />
                <el-table-column prop="prompt_tokens" label="Prompt" width="110" align="right" />
                <el-table-column prop="completion_tokens" label="Completion" width="120" align="right" />
                <el-table-column prop="total_tokens" :label="t('pages.llmUsage.totalTokens')" width="110" align="right" sortable />
                <el-table-column :label="t('pages.llmUsage.share')" width="90" align="right">
                    <template #default="{ row }">{{ row.share_percent }}%</template>
                </el-table-column>
            </el-table>
        </el-card>

        <el-card shadow="hover" class="mgb20" v-loading="loading">
            <template #header>
                <span>{{ t('pages.llmUsage.byCaller') }}</span>
            </template>
            <el-table :data="stats.by_caller" stripe size="small" :empty-text="t('pages.llmUsage.emptyData')">
                <el-table-column prop="caller" :label="t('pages.llmUsage.caller')" min-width="220" show-overflow-tooltip />
                <el-table-column prop="calls" :label="t('pages.llmUsage.calls')" width="100" align="right" />
                <el-table-column prop="prompt_tokens" label="Prompt" width="110" align="right" />
                <el-table-column prop="completion_tokens" label="Completion" width="120" align="right" />
                <el-table-column prop="total_tokens" :label="t('pages.llmUsage.totalTokens')" width="110" align="right" sortable />
                <el-table-column :label="t('pages.llmUsage.share')" width="90" align="right">
                    <template #default="{ row }">{{ row.share_percent }}%</template>
                </el-table-column>
            </el-table>
        </el-card>

        <el-card shadow="hover" v-loading="recentLoading">
            <template #header>
                <span>{{ t('pages.llmUsage.recent') }}</span>
            </template>
            <el-table :data="recentItems" stripe size="small" :empty-text="t('pages.llmUsage.emptyRecords')">
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
                        <el-tag :type="row.success ? 'success' : 'danger'" size="small">
                            {{ row.success ? t('pages.llmUsage.yes') : t('pages.llmUsage.no') }}
                        </el-tag>
                    </template>
                </el-table-column>
                <el-table-column prop="request_id" label="request_id" min-width="140" show-overflow-tooltip />
            </el-table>
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
    days: number;
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
const days = ref(7);
const stats = reactive<UsageStats>({
    days: 7,
    total_calls: 0,
    total_prompt_tokens: 0,
    total_completion_tokens: 0,
    total_tokens: 0,
    by_caller: [],
    by_user: [],
});
const recentItems = ref<UsageLogItem[]>([]);

const formatTime = (value: string) => {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
};

const loadStats = async () => {
    loading.value = true;
    try {
        const res = await fetchLlmUsageStats({ days: days.value, exclude_warmup: true });
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
        const res = await fetchLlmUsageRecent({ limit: 50 });
        recentItems.value = res.data.items ?? [];
    } catch {
        ElMessage.error(t('pages.llmUsage.loadRecentFailed'));
    } finally {
        recentLoading.value = false;
    }
};

const loadAll = async () => {
    await Promise.all([loadStats(), loadRecent()]);
};

onMounted(() => {
    loadAll();
});
</script>

<style scoped>
.llm-usage-page .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
}

.page-title {
    font-size: 16px;
    font-weight: 600;
}

.page-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
}

.toolbar-label {
    color: var(--el-text-color-secondary);
    font-size: 13px;
}

.summary-row {
    margin-top: 4px;
}

.mgb20 {
    margin-bottom: 20px;
}
</style>
