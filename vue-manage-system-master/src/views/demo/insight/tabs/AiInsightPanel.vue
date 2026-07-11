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
            <span v-if="lastRun" class="run-result">
                {{ t('pages.insight.ai.runDone', {
                    date: lastRun.snapshot_date,
                    model: lastRun.model_version,
                    ms: lastRun.elapsed_ms,
                }) }}
                <template v-if="lastRun.mode"> · {{ lastRun.mode }}</template>
            </span>
        </div>

        <el-table v-if="lastRun?.steps?.length" :data="lastRun.steps" border stripe class="mgb20">
            <el-table-column prop="label" :label="t('pages.insight.ai.stepName')" width="140" />
            <el-table-column prop="step" label="Step ID" width="160" />
            <el-table-column prop="output_count" :label="t('pages.insight.ai.outputCount')" width="110" />
            <el-table-column prop="elapsed_ms" :label="t('pages.insight.ai.elapsedMs')" width="110" />
        </el-table>

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

interface PipelineStep {
    step: string;
    label: string;
    output_count: number;
    elapsed_ms: number;
}

interface NightlyRunResult {
    snapshot_date: string;
    steps: PipelineStep[];
    snapshots_upserted: number;
    region_metrics_upserted: number;
    analysis_log_id: number;
    elapsed_ms: number;
    model_version: string;
    mode?: 'incremental' | 'full';
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
const lastRun = ref<NightlyRunResult | null>(null);
const logs = ref<LogRow[]>([]);
const page = reactive({ index: 1, size: 10, total: 0 });

async function handleTrain() {
    training.value = true;
    try {
        const { data } = await postInsightTrainModel();
        ElMessage.success(t('pages.insight.action.trainDone', { version: data.model_version }));
    } finally {
        training.value = false;
    }
}

async function handleRun(mode: 'incremental' | 'full' = 'incremental') {
    const loadingRef = mode === 'full' ? runningFull : running;
    loadingRef.value = true;
    try {
        const { data } = await postInsightNightlyRun(undefined, false, mode);
        lastRun.value = data;
        ElMessage.success(t('pages.insight.ai.runSuccess'));
        page.index = 1;
        await loadLogs();
        emit('refreshed');
    } catch (error: unknown) {
        const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        ElMessage.error(detail || t('pages.insight.ai.runFailed'));
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
    } catch {
        logs.value = [];
        page.total = 0;
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
