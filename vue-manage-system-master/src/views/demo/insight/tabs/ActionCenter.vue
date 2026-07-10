<template>
    <div class="action-tab">
        <el-alert :title="t('pages.insight.action.hint')" type="info" show-icon :closable="false" class="mgb20" />

        <el-row :gutter="16" class="mgb20">
            <el-col :xs="12" :sm="6">
                <el-card shadow="hover"><el-statistic :title="t('pages.insight.action.modelVersion')" :value="dashboard?.model_version || '-'" /></el-card>
            </el-col>
            <el-col :xs="12" :sm="6">
                <el-card shadow="hover"><el-statistic :title="t('pages.insight.action.highRisk')" :value="dashboard?.high_risk_total || 0" /></el-card>
            </el-col>
            <el-col :xs="12" :sm="6">
                <el-card shadow="hover"><el-statistic :title="t('pages.insight.action.snapshotTotal')" :value="dashboard?.snapshot_total || 0" /></el-card>
            </el-col>
            <el-col :xs="12" :sm="6">
                <el-card shadow="hover">
                    <el-statistic :title="t('pages.insight.action.trained')">
                        <template #default>
                            <el-tag :type="dashboard?.has_trained_model ? 'success' : 'warning'" size="small">
                                {{ dashboard?.has_trained_model ? t('pages.insight.action.yes') : t('pages.insight.action.no') }}
                            </el-tag>
                        </template>
                    </el-statistic>
                </el-card>
            </el-col>
        </el-row>

        <div class="toolbar mgb20">
            <el-button type="primary" :loading="training" @click="handleTrain">{{ t('pages.insight.action.trainModel') }}</el-button>
            <el-button @click="loadAll">{{ t('common.refresh') }}</el-button>
        </div>

        <el-row :gutter="16">
            <el-col :xs="24" :lg="14">
                <el-card shadow="never" class="mgb20">
                    <template #header>{{ t('pages.insight.action.recommendTitle') }}</template>
                    <el-table :data="recommendations" v-loading="loadingRec" border stripe>
                        <el-table-column prop="user_id" :label="t('pages.insight.profile.userId')" width="110" />
                        <el-table-column prop="name" :label="t('pages.insight.profile.name')" width="90" />
                        <el-table-column :label="t('pages.insight.profile.riskScore')" width="150">
                            <template #default="{ row }">{{ Number(row.risk_score).toFixed(4) }} ({{ row.churn_risk_level }})</template>
                        </el-table-column>
                        <el-table-column prop="suggested_action" :label="t('pages.insight.action.suggestedAction')" min-width="220" show-overflow-tooltip />
                    </el-table>
                </el-card>
            </el-col>
            <el-col :xs="24" :lg="10">
                <el-card shadow="never" class="mgb20">
                    <template #header>{{ t('pages.insight.action.simulateTitle') }}</template>
                    <el-form label-width="120px">
                        <el-form-item :label="t('pages.insight.profile.userId')">
                            <el-input v-model="simulate.user_id" placeholder="10000001" />
                        </el-form-item>
                        <el-form-item :label="t('pages.insight.action.adjustSatisfaction')">
                            <el-slider v-model="simulate.satisfaction" :min="1" :max="5" :step="0.5" show-input />
                        </el-form-item>
                        <el-form-item :label="t('pages.insight.action.adjustComplaints')">
                            <el-input-number v-model="simulate.complaints" :min="0" :max="10" />
                        </el-form-item>
                        <el-form-item>
                            <el-button type="primary" :loading="simulating" @click="handleSimulate">{{ t('pages.insight.action.runSimulate') }}</el-button>
                        </el-form-item>
                    </el-form>
                    <el-descriptions v-if="simulateResult" :column="1" border size="small">
                        <el-descriptions-item :label="t('pages.insight.action.baseline')">
                            {{ Number(simulateResult.baseline_risk).toFixed(4) }} ({{ simulateResult.baseline_level }})
                        </el-descriptions-item>
                        <el-descriptions-item :label="t('pages.insight.action.scenario')">
                            {{ Number(simulateResult.scenario_risk).toFixed(4) }} ({{ simulateResult.scenario_level }})
                        </el-descriptions-item>
                        <el-descriptions-item :label="t('pages.insight.action.delta')">
                            <span :class="deltaClass(simulateResult.delta_risk)">{{ formatDelta(simulateResult.delta_risk) }}</span>
                        </el-descriptions-item>
                    </el-descriptions>
                </el-card>
                <el-card shadow="never">
                    <template #header>{{ t('pages.insight.action.weightsTitle') }}</template>
                    <el-table :data="dashboard?.simulation_weights || []" size="small" border>
                        <el-table-column prop="feature_name" :label="t('pages.insight.action.feature')" min-width="140" />
                        <el-table-column prop="base_importance" label="Importance" width="110" />
                        <el-table-column prop="impact_coefficient" :label="t('pages.insight.action.coef')" width="90" />
                    </el-table>
                </el-card>
            </el-col>
        </el-row>
    </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import {
    getInsightDecisionDashboard,
    getInsightDecisionRecommendations,
    postInsightDecisionSimulate,
    postInsightTrainModel,
} from '@/api';

const { t } = useI18n();
const loadingRec = ref(false);
const training = ref(false);
const simulating = ref(false);
const dashboard = ref<Record<string, any> | null>(null);
const recommendations = ref<Record<string, unknown>[]>([]);
const simulateResult = ref<Record<string, any> | null>(null);
const simulate = reactive({ user_id: '10000001', satisfaction: 4, complaints: 0 });

async function loadDashboard() {
    const { data } = await getInsightDecisionDashboard();
    dashboard.value = data;
}

async function loadRecommendations() {
    loadingRec.value = true;
    try {
        const { data } = await getInsightDecisionRecommendations({ limit: 15 });
        recommendations.value = data;
    } finally {
        loadingRec.value = false;
    }
}

async function loadAll() {
    await Promise.all([loadDashboard(), loadRecommendations()]);
}

async function handleTrain() {
    training.value = true;
    try {
        const { data } = await postInsightTrainModel();
        ElMessage.success(t('pages.insight.action.trainDone', { version: data.model_version }));
        await loadAll();
    } finally {
        training.value = false;
    }
}

async function handleSimulate() {
    if (!simulate.user_id?.trim()) return;
    simulating.value = true;
    try {
        const { data } = await postInsightDecisionSimulate({
            user_id: simulate.user_id.trim(),
            adjustments: {
                avg_satisfaction: simulate.satisfaction,
                complaint_cnt: simulate.complaints,
                survey_customer_service: simulate.satisfaction,
                survey_loyalty_retention: simulate.satisfaction,
            },
        });
        simulateResult.value = data;
    } finally {
        simulating.value = false;
    }
}

function formatDelta(value: unknown) {
    const num = Number(value);
    return `${num >= 0 ? '+' : ''}${num.toFixed(4)}`;
}

function deltaClass(value: unknown) {
    return Number(value) < 0 ? 'delta-good' : Number(value) > 0 ? 'delta-bad' : '';
}

onMounted(loadAll);
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; flex-wrap: wrap; }
.mgb20 { margin-bottom: 20px; }
.delta-good { color: var(--el-color-success); font-weight: 600; }
.delta-bad { color: var(--el-color-danger); font-weight: 600; }
</style>
