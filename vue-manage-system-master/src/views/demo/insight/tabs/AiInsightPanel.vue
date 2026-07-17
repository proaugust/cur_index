<template>
    <div class="ai-tab">
        <el-alert
            :title="t('pages.insight.ai.hint')"
            type="info"
            show-icon
            :closable="false"
            class="mgb20"
        />

        <el-card shadow="never" class="mgb20">
            <template #header>{{ t('pages.insight.ai.pipeline') }}</template>
            <el-steps :active="3" align-center finish-status="success">
                <el-step :title="t('pages.insight.ai.stepAi')" :description="t('pages.insight.ai.stepAiDesc')" />
                <el-step :title="t('pages.insight.ai.stepSnap')" :description="t('pages.insight.ai.stepSnapDesc')" />
                <el-step :title="t('pages.insight.ai.stepRegion')" :description="t('pages.insight.ai.stepRegionDesc')" />
            </el-steps>
        </el-card>

        <div class="toolbar mgb20">
            <el-button type="primary" :loading="running" @click="handleRun('incremental')">
                {{ t('pages.insight.ai.runIncremental') }}
            </el-button>
            <el-button :loading="runningFull" @click="handleRun('full')">
                {{ t('pages.insight.ai.runFull') }}
            </el-button>
            <el-button :loading="training" @click="handleTrain">{{ t('pages.insight.action.trainModel') }}</el-button>
            <el-button @click="loadLogs">{{ t('common.refresh') }}</el-button>
            <span v-if="lastAccepted" class="run-result">
                {{ t('pages.insight.ai.accepted', {
                    id: lastAccepted.analysis_log_id,
                    date: lastAccepted.snapshot_date,
                    users: lastAccepted.pending_users,
                }) }}
                <template v-if="lastAccepted.mode"> · {{ lastAccepted.mode }}</template>
            </span>
        </div>

        <el-card shadow="never">
            <template #header>{{ t('pages.insight.ai.logTitle') }}</template>
            <el-table :data="logs" v-loading="loading" border stripe>
                <el-table-column prop="created_at" :label="t('pages.insight.ai.logTime')" width="180" />
                <el-table-column prop="answer" :label="t('pages.insight.ai.logSummary')" min-width="260" show-overflow-tooltip />
                <el-table-column prop="latency_ms" :label="t('pages.insight.ai.elapsedMs')" width="100" />
                <el-table-column prop="status" :label="t('pages.insight.ai.logStatus')" width="100" />
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

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { getInsightJobLogs, postInsightNightlyRun, postInsightTrainModel } from '@/api';

interface NightlyAccepted {
    analysis_log_id: number;
    snapshot_date: string;
    mode?: 'incremental' | 'full';
    pending_users: number;
    status: string;
    message?: string;
}

interface LogRow {
    id: number;
    answer: string;
    status: string;
    latency_ms: number;
    created_at: string;
}

const emit = defineEmits<{ refreshed: [] }>();
const { t } = useI18n();
const running = ref(false);
const runningFull = ref(false);
const training = ref(false);
const loading = ref(false);
const lastAccepted = ref<NightlyAccepted | null>(null);
const logs = ref<LogRow[]>([]);
const page = reactive({ index: 1, size: 10, total: 0 });

function sleep(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForJob(logId: number, timeoutMs = 600_000): Promise<LogRow> {
    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
        const { data } = await getInsightJobLogs({ page: 1, page_size: 20 });
        const row = (data.list as LogRow[]).find((item) => item.id === logId);
        if (row && row.status !== 'running') {
            return row;
        }
        await sleep(2000);
    }
    throw new Error('job_timeout');
}

async function handleTrain() {
    training.value = true;
    try {
        const { data } = await postInsightTrainModel();
        ElMessage.success(data.message || t('pages.insight.action.trainDone', { version: data.model_version }));
    } finally {
        training.value = false;
    }
}

async function handleRun(mode: 'incremental' | 'full' = 'incremental') {
    const loadingRef = mode === 'full' ? runningFull : running;
    loadingRef.value = true;
    try {
        const { data } = await postInsightNightlyRun(undefined, false, mode);
        lastAccepted.value = data;
        ElMessage.info(data.message || t('pages.insight.ai.runAccepted'));
        page.index = 1;
        await loadLogs();
        const row = await waitForJob(data.analysis_log_id);
        await loadLogs();
        if (row.status === 'completed') {
            ElMessage.success(t('pages.insight.ai.runSuccess'));
            emit('refreshed');
        } else {
            ElMessage.error(row.answer || t('pages.insight.ai.runFailed'));
        }
    } catch (error: unknown) {
        const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        const msg = (error as Error)?.message === 'job_timeout'
            ? t('pages.insight.ai.runTimeout')
            : (detail || t('pages.insight.ai.runFailed'));
        ElMessage.error(msg);
        await loadLogs();
    } finally {
        loadingRef.value = false;
    }
}

async function loadLogs() {
    loading.value = true;
    try {
        const { data } = await getInsightJobLogs({ page: page.index, page_size: page.size });
        logs.value = data.list;
        page.total = data.pageTotal;
    } catch (error: unknown) {
        logs.value = [];
        page.total = 0;
        const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        ElMessage.error(detail || t('pages.insight.ai.logLoadFailed'));
    } finally {
        loading.value = false;
    }
}

function changePage(val: number) {
    page.index = val;
    loadLogs();
}

onMounted(loadLogs);
</script>

<style scoped>
.toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}
.run-result {
    color: var(--el-text-color-secondary);
    font-size: 13px;
}
.pager {
    justify-content: flex-end;
    margin-top: 16px;
}
.mgb20 {
    margin-bottom: 20px;
}
</style>
