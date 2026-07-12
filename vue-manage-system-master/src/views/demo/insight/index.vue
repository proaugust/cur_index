<template>
    <div class="container insight-page">
        <el-card shadow="hover" class="mgb20">
            <template #header>
                <div class="page-header">
                    <div>
                        <div class="page-title">{{ t('pages.insight.title') }}</div>
                        <div class="page-subtitle">{{ t('pages.insight.subtitle') }}</div>
                    </div>
                    <el-tag type="info" size="large">Insight</el-tag>
                </div>
            </template>
            <el-row :gutter="16" class="status-row">
                <el-col :xs="12" :sm="8" :md="4" v-for="item in statusCards" :key="item.key">
                    <el-statistic :title="item.label" :value="status[item.key]" />
                </el-col>
            </el-row>
        </el-card>

        <el-card shadow="hover">
            <el-tabs v-model="activeTab" type="border-card">
                <el-tab-pane :label="t('pages.insight.tabs.seedCustomers')" name="seedCustomers" lazy>
                    <DataSeedCustomers :status="status" @refresh="loadStatus" />
                </el-tab-pane>
                <el-tab-pane :label="t('pages.insight.tabs.seedSamples')" name="seedSamples" lazy>
                    <DataSeedSamples :status="status" @refresh="loadStatus" />
                </el-tab-pane>
                <el-tab-pane :label="t('pages.insight.tabs.profile')" name="profile" lazy>
                    <CustomerProfile :initial-user-id="profileUserId" />
                </el-tab-pane>
                <el-tab-pane :label="t('pages.insight.tabs.bi')" name="bi" lazy>
                    <RegionBIMap />
                </el-tab-pane>
                <el-tab-pane :label="t('pages.insight.tabs.risk')" name="risk" lazy>
                    <RiskAnalysis @open-profile="openProfile" />
                </el-tab-pane>
                <el-tab-pane :label="t('pages.insight.tabs.aiInsight')" name="aiInsight" lazy>
                    <AiInsightPanel @refreshed="loadStatus" />
                </el-tab-pane>
                <el-tab-pane :label="t('pages.insight.tabs.action')" name="action" lazy>
                    <ActionCenter />
                </el-tab-pane>
            </el-tabs>
        </el-card>
    </div>
</template>

<script setup lang="ts" name="modules-insight">
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { getInsightSeedStatus } from '@/api';
import DataSeedCustomers from './tabs/DataSeedCustomers.vue';
import DataSeedSamples from './tabs/DataSeedSamples.vue';
import CustomerProfile from './tabs/CustomerProfile.vue';
import RegionBIMap from './tabs/RegionBIMap.vue';
import RiskAnalysis from './tabs/RiskAnalysis.vue';
import AiInsightPanel from './tabs/AiInsightPanel.vue';
import ActionCenter from './tabs/ActionCenter.vue';

const { t } = useI18n();
const activeTab = ref('seedCustomers');
const profileUserId = ref('');

function openProfile(userId: string) {
    profileUserId.value = userId;
    activeTab.value = 'profile';
}

const status = reactive({
    users: 0,
    complaints: 0,
    touchpoints: 0,
    samples: 0,
    snapshots: 0,
    region_metrics: 0,
    simulation_weights: 0,
    analysis_logs: 0,
});

const statusCards = computed(() => [
    { key: 'users' as const, label: t('pages.insight.status.users') },
    { key: 'complaints' as const, label: t('pages.insight.status.complaints') },
    { key: 'samples' as const, label: t('pages.insight.status.samples') },
    { key: 'snapshots' as const, label: t('pages.insight.status.snapshots') },
    { key: 'region_metrics' as const, label: t('pages.insight.status.regionMetrics') },
    { key: 'simulation_weights' as const, label: t('pages.insight.status.simulationWeights') },
    { key: 'analysis_logs' as const, label: t('pages.insight.status.logs') },
]);

async function loadStatus() {
    const { data } = await getInsightSeedStatus();
    Object.assign(status, data);
}

onMounted(() => {
    loadStatus();
});
</script>

<style scoped>
.insight-page .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}
.page-title {
    font-size: 18px;
    font-weight: 600;
}
.page-subtitle {
    margin-top: 4px;
    color: var(--el-text-color-secondary);
    font-size: 13px;
}
.status-row {
    margin-top: 4px;
}
</style>
