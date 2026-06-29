<template>
    <div class="container cobol-migrate-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <div class="page-title-row">
                        <span class="page-title">{{ t('pages.cobolMigrate.title') }}</span>
                        <FeatureIntroIcon
                            page-key="cobol-migrate"
                            section-key="page"
                            :intros="intros"
                            :title="t('pages.cobolMigrate.title')"
                            @saved="setIntro"
                        />
                    </div>
                    <p class="page-subtitle">{{ t('pages.cobolMigrate.subtitle') }}</p>
                </div>
            </template>

            <ModeIntro :title="t('pages.cobolMigrate.flowTitle')" :nodes="flowNodes" />

            <el-steps :active="activeStep" finish-status="success" align-center class="wizard-steps">
                <el-step
                    v-for="(item, index) in stepDefs"
                    :key="item.key"
                    :title="item.title"
                    :description="item.desc"
                    :status="stepStatus(index)"
                    class="wizard-step-item"
                    @click="selectStep(index)"
                />
            </el-steps>

            <div class="action-bar">
                <el-button
                    type="primary"
                    :loading="loading"
                    :disabled="loading"
                    @click="runCurrentStep"
                >
                    {{ t('pages.cobolMigrate.runStep', { n: activeStep + 1 }) }}
                </el-button>
                <el-button type="success" :loading="pipelineLoading" :disabled="loading || pipelineLoading" @click="runPipeline">
                    {{ t('pages.cobolMigrate.runPipeline') }}
                </el-button>
                <el-button :disabled="loading || pipelineLoading" @click="resetAll">
                    {{ t('pages.cobolMigrate.reset') }}
                </el-button>
            </div>

            <div v-if="viewResult" class="payload-section">
                <div class="section-label">
                    {{ t('pages.cobolMigrate.stepResult', { n: viewResult.step, name: viewResult.step_name }) }}
                </div>

                <!-- Step 1: scan -->
                <template v-if="viewResult.step === 1">
                    <el-alert
                        :title="t('pages.cobolMigrate.scanSummary', {
                            total: viewResult.payload.total_files,
                            cbl: viewResult.payload.cbl_count,
                            cpy: viewResult.payload.cpy_count,
                        })"
                        type="info"
                        :closable="false"
                        show-icon
                        class="mgb12"
                    />
                    <el-table :data="viewResult.payload.files" stripe size="small" max-height="320">
                        <el-table-column prop="name" :label="t('pages.cobolMigrate.colFile')" min-width="140" />
                        <el-table-column prop="path" :label="t('pages.cobolMigrate.colPath')" min-width="260" show-overflow-tooltip />
                        <el-table-column prop="lines" :label="t('pages.cobolMigrate.colLines')" width="80" align="right" />
                        <el-table-column prop="ext" :label="t('pages.cobolMigrate.colExt')" width="72" />
                    </el-table>
                </template>

                <!-- Step 2: classify -->
                <template v-else-if="viewResult.step === 2">
                    <el-table :data="viewResult.payload.classifications" stripe size="small" max-height="320">
                        <el-table-column prop="file" :label="t('pages.cobolMigrate.colFile')" min-width="140" />
                        <el-table-column prop="type" :label="t('pages.cobolMigrate.colType')" width="120" />
                        <el-table-column :label="t('pages.cobolMigrate.colTags')" min-width="160">
                            <template #default="{ row }">
                                <el-tag v-for="tag in row.tags" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column :label="t('pages.cobolMigrate.colConfidence')" width="100" align="right">
                            <template #default="{ row }">{{ (row.confidence * 100).toFixed(0) }}%</template>
                        </el-table-column>
                    </el-table>
                </template>

                <!-- Step 3: RAG -->
                <template v-else-if="viewResult.step === 3">
                    <el-alert
                        :title="t('pages.cobolMigrate.ragSummary', {
                            count: viewResult.payload.chunk_count,
                            dim: viewResult.payload.embedding_dim,
                        })"
                        type="success"
                        :closable="false"
                        show-icon
                        class="mgb12"
                    />
                    <el-table :data="viewResult.payload.samples" stripe size="small">
                        <el-table-column prop="file" :label="t('pages.cobolMigrate.colFile')" width="130" />
                        <el-table-column prop="chunk_id" label="Chunk ID" width="130" />
                        <el-table-column prop="text" :label="t('pages.cobolMigrate.colSnippet')" min-width="280" show-overflow-tooltip />
                    </el-table>
                </template>

                <!-- Step 4: graph -->
                <template v-else-if="viewResult.step === 4">
                    <el-alert
                        :title="t('pages.cobolMigrate.graphSummary', {
                            nodes: viewResult.payload.node_count,
                            edges: viewResult.payload.edge_count,
                        })"
                        type="info"
                        :closable="false"
                        show-icon
                        class="mgb12"
                    />
                    <CallGraph
                        :nodes="(viewResult.payload.nodes as GraphNode[]) ?? []"
                        :edges="(viewResult.payload.edges as GraphEdge[]) ?? []"
                    />
                </template>

                <!-- Step 5: translate -->
                <template v-else-if="viewResult.step === 5">
                    <el-alert
                        :title="t('pages.cobolMigrate.translateSummary', {
                            template: viewResult.payload.template,
                            count: viewResult.payload.java_file_count,
                        })"
                        type="success"
                        :closable="false"
                        show-icon
                        class="mgb12"
                    />
                    <TranslateReport
                        :project-tree="(viewResult.payload.project_tree as TreeNode[]) ?? []"
                        :mappings="(viewResult.payload.mappings as MappingRow[]) ?? []"
                        :code-pairs="(viewResult.payload.code_pairs as CodePair[]) ?? []"
                    />
                </template>

                <!-- Step 6: validate -->
                <template v-else-if="viewResult.step === 6">
                    <el-alert
                        :title="viewResult.payload.summary as string"
                        :type="viewResult.payload.overall === 'pass' ? 'success' : 'warning'"
                        :closable="false"
                        show-icon
                        class="mgb12"
                    />
                    <ValidateReport
                        :business-chains="(viewResult.payload.business_chains as ChainRow[]) ?? []"
                        :items="(viewResult.payload.items as CheckItem[]) ?? []"
                    />
                </template>

                <!-- Step 7: test -->
                <template v-else-if="viewResult.step === 7">
                    <TestReport
                        :results="(viewResult.payload.results as TestResult[]) ?? []"
                        :stats="{
                            total: viewResult.payload.total as number,
                            passed: viewResult.payload.passed as number,
                            warned: viewResult.payload.warned as number,
                            skipped: viewResult.payload.skipped as number,
                        }"
                    />
                </template>
            </div>
            <el-empty
                v-else
                :description="t('pages.cobolMigrate.emptyPayload')"
                :image-size="72"
                class="payload-empty"
            />

            <el-divider />

            <div class="timeline-section">
                <div class="section-label">{{ t('pages.cobolMigrate.agentTimeline') }}</div>
                <div v-if="timelineSteps.length" class="steps-timeline">
                    <div
                        v-for="(step, i) in timelineSteps"
                        :key="i"
                        class="step-card"
                        :class="step.status"
                    >
                        <div class="step-header">
                            <el-tag :type="agentStatusTag(step.status)" size="small" effect="plain">
                                {{ agentStatusLabel(step.status) }}
                            </el-tag>
                            <span class="step-agent">{{ step.agent }}</span>
                            <span class="step-role">{{ step.role }}</span>
                            <span v-if="step.meta" class="step-meta">{{ step.meta }}</span>
                        </div>
                        <div v-if="step.input" class="step-block">
                            <div class="block-label">{{ t('pages.agent.input') }}</div>
                            <div class="block-content input-content">{{ step.input }}</div>
                        </div>
                        <div v-if="step.output" class="step-block">
                            <div class="block-label">{{ t('pages.agent.output') }}</div>
                            <div class="block-content output-content">{{ step.output }}</div>
                        </div>
                    </div>
                </div>
                <el-empty v-else :description="t('pages.cobolMigrate.emptyTimeline')" :image-size="72" />
            </div>
        </el-card>
    </div>
</template>

<script setup lang="ts" name="demo-cobol-migrate">
import { computed, defineAsyncComponent, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import { useFeatureIntros } from '@/composables/useFeatureIntros';
import { useCachedRef } from '@/composables/useFormCache';
import { runCobolMigratePipeline, runCobolMigrateStep } from '@/api';
import type { AgentStep } from './agent/types';

const ModeIntro = defineAsyncComponent(() => import('./agent/mode-intro.vue'));
const CallGraph = defineAsyncComponent(() => import('./cobol-migrate/call-graph.vue'));
const TranslateReport = defineAsyncComponent(() => import('./cobol-migrate/translate-report.vue'));
const ValidateReport = defineAsyncComponent(() => import('./cobol-migrate/validate-report.vue'));
const TestReport = defineAsyncComponent(() => import('./cobol-migrate/test-report.vue'));

interface GraphNode {
    id: string;
    name: string;
    category: string;
    symbol_size?: number;
}

interface GraphEdge {
    source: string;
    target: string;
    relation: string;
}

interface TreeNode {
    label: string;
    children?: TreeNode[];
}

interface MappingRow {
    cobol: string;
    java: string;
    layer: string;
}

interface CodePair {
    cobol_file: string;
    java_file: string;
    cobol_snippet: string;
    java_snippet: string;
}

interface ChainRow {
    name: string;
    status: string;
    nodes: string[];
    gap?: string;
}

interface CheckItem {
    item: string;
    status: string;
    detail: string;
}

interface TestResult {
    java_class: string;
    method: string;
    status: string;
    duration_ms: number;
    message?: string;
    snippet?: string;
}

interface CobolMigrateStepResult {
    step: number;
    step_name: string;
    steps: AgentStep[];
    payload: Record<string, unknown>;
}

const { t } = useI18n();
const { intros, setIntro } = useFeatureIntros('cobol-migrate');

const activeStep = useCachedRef('cobol-migrate:activeStep', 0);
const loading = ref(false);
const pipelineLoading = ref(false);
const stepResults = reactive<Record<number, CobolMigrateStepResult>>({});
const viewStep = ref<number | null>(null);
const timelineSteps = ref<AgentStep[]>([]);

const stepDefs = computed(() => [
    { key: 'scan', title: t('pages.cobolMigrate.step1Title'), desc: t('pages.cobolMigrate.step1Desc') },
    { key: 'classify', title: t('pages.cobolMigrate.step2Title'), desc: t('pages.cobolMigrate.step2Desc') },
    { key: 'rag', title: t('pages.cobolMigrate.step3Title'), desc: t('pages.cobolMigrate.step3Desc') },
    { key: 'graph', title: t('pages.cobolMigrate.step4Title'), desc: t('pages.cobolMigrate.step4Desc') },
    { key: 'translate', title: t('pages.cobolMigrate.step5Title'), desc: t('pages.cobolMigrate.step5Desc') },
    { key: 'validate', title: t('pages.cobolMigrate.step6Title'), desc: t('pages.cobolMigrate.step6Desc') },
    { key: 'test', title: t('pages.cobolMigrate.step7Title'), desc: t('pages.cobolMigrate.step7Desc') },
]);

const flowNodes = computed(() => [
    t('pages.cobolMigrate.flowScan'),
    t('pages.cobolMigrate.flowClassify'),
    t('pages.cobolMigrate.flowRag'),
    t('pages.cobolMigrate.flowGraph'),
    t('pages.cobolMigrate.flowTranslate'),
    t('pages.cobolMigrate.flowValidate'),
    t('pages.cobolMigrate.flowTest'),
    t('pages.cobolMigrate.flowTarget'),
]);

const viewResult = computed(() => {
    const n = viewStep.value ?? (activeStep.value + 1);
    return stepResults[n] ?? null;
});

const stepStatus = (index: number) => {
    const n = index + 1;
    if (stepResults[n]) return 'success';
    if (loading.value && activeStep.value === index) return 'process';
    if (pipelineLoading.value && !stepResults[n] && index <= activeStep.value) return 'process';
    return 'wait';
};

const selectStep = (index: number) => {
    activeStep.value = index;
    const n = index + 1;
    if (stepResults[n]) {
        viewStep.value = n;
        timelineSteps.value = stepResults[n].steps ?? [];
    }
};

const agentStatusTag = (status: AgentStep['status']) => {
    if (status === 'done') return 'success';
    if (status === 'running') return 'warning';
    if (status === 'error') return 'danger';
    return 'info';
};

const agentStatusLabel = (status: AgentStep['status']) => {
    const map: Record<AgentStep['status'], string> = {
        pending: t('pages.agent.statusPending'),
        running: t('pages.agent.statusRunning'),
        done: t('pages.agent.statusDone'),
        error: t('pages.agent.statusError'),
    };
    return map[status];
};

const applyStepResult = (data: CobolMigrateStepResult) => {
    stepResults[data.step] = data;
    viewStep.value = data.step;
    timelineSteps.value = data.steps ?? [];
    activeStep.value = Math.min(data.step, 6);
};

const runCurrentStep = async () => {
    const n = activeStep.value + 1;
    loading.value = true;
    try {
        const res = await runCobolMigrateStep(n);
        applyStepResult(res.data);
        ElMessage.success(t('pages.cobolMigrate.stepDone', { n }));
    } catch {
        ElMessage.error(t('pages.cobolMigrate.runFailed'));
    } finally {
        loading.value = false;
    }
};

const runPipeline = async () => {
    pipelineLoading.value = true;
    timelineSteps.value = [];
    try {
        const res = await runCobolMigratePipeline();
        const allSteps: AgentStep[] = [];
        for (const item of res.data.results ?? []) {
            stepResults[item.step] = item;
            allSteps.push(...(item.steps ?? []));
        }
        timelineSteps.value = allSteps;
        viewStep.value = 7;
        activeStep.value = 6;
        ElMessage.success(t('pages.cobolMigrate.pipelineDone'));
    } catch {
        ElMessage.error(t('pages.cobolMigrate.runFailed'));
    } finally {
        pipelineLoading.value = false;
    }
};

const resetAll = () => {
    for (const key of Object.keys(stepResults)) {
        delete stepResults[Number(key)];
    }
    timelineSteps.value = [];
    viewStep.value = null;
    activeStep.value = 0;
};
</script>

<style scoped>
.cobol-migrate-page {
    min-height: calc(100vh - 140px);
}

.page-title-row {
    display: inline-flex;
    align-items: center;
}

.page-title {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
}

.page-subtitle {
    margin: 6px 0 0;
    font-size: 13px;
    color: #909399;
    line-height: 1.5;
    max-width: 720px;
}

.wizard-steps {
    margin: 20px 0;
}

.wizard-step-item {
    cursor: pointer;
}

.action-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 20px;
}

.section-label {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 12px;
}

.mgb12 {
    margin-bottom: 12px;
}

.tag-item {
    margin-right: 4px;
}

.payload-section {
    margin-top: 8px;
}

.payload-empty {
    padding: 12px 0;
}

.timeline-section {
    margin-top: 8px;
}

.steps-timeline {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.step-card {
    border: 1px solid #ebeef5;
    border-radius: 6px;
    padding: 12px 14px;
    background: #fafafa;
}

.step-card.done {
    border-color: #e1f3d8;
    background: #f9fef5;
}

.step-header {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;
}

.step-agent {
    font-weight: 600;
    font-size: 13px;
    color: #303133;
}

.step-role {
    font-size: 12px;
    color: #909399;
}

.step-meta {
    font-size: 12px;
    color: #c0c4cc;
}

.step-block {
    margin-top: 8px;
}

.block-label {
    font-size: 12px;
    color: #909399;
    margin-bottom: 4px;
}

.block-content {
    font-size: 13px;
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
}

.input-content {
    color: #606266;
}

.output-content {
    color: #303133;
}
</style>
