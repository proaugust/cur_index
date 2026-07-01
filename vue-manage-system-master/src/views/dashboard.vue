<template>
    <div>
        <el-row :gutter="20" class="mgb20">
            <el-col :span="6">
                <el-card shadow="hover" body-class="card-body">
                    <el-icon class="card-icon bg1">
                        <TrendCharts />
                    </el-icon>
                    <div class="card-content">
                        <countup class="card-num color1" :end="summary.usIndex" :options="{ decimalPlaces: 1 }" />
                        <div>{{ t('pages.dashboard.usIndex') }}</div>
                    </div>
                </el-card>
            </el-col>
            <el-col :span="6">
                <el-card shadow="hover" body-class="card-body">
                    <el-icon class="card-icon bg2">
                        <Coin />
                    </el-icon>
                    <div class="card-content">
                        <countup class="card-num color2" :end="summary.totalInvestment" :options="{ decimalPlaces: 1 }" />
                        <div>{{ t('pages.dashboard.globalInvestment') }}</div>
                    </div>
                </el-card>
            </el-col>
            <el-col :span="6">
                <el-card shadow="hover" body-class="card-body">
                    <el-icon class="card-icon bg3">
                        <Document />
                    </el-icon>
                    <div class="card-content">
                        <countup class="card-num color3" :end="summary.totalPapers" :options="{ decimalPlaces: 1 }" />
                        <div>{{ t('pages.dashboard.globalPapers') }}</div>
                    </div>
                </el-card>
            </el-col>
            <el-col :span="6">
                <el-card shadow="hover" body-class="card-body">
                    <el-icon class="card-icon bg4">
                        <DataAnalysis />
                    </el-icon>
                    <div class="card-content">
                        <countup class="card-num color4" :end="summary.avgScore" :options="{ decimalPlaces: 1 }" />
                        <div>{{ t('pages.dashboard.avgIndex', { count: summary.countryCount }) }}</div>
                    </div>
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" class="mgb20">
            <el-col :span="16">
                <el-card shadow="hover">
                    <div class="card-header">
                        <p class="card-header-title">{{ t('pages.dashboard.indexTrendTitle') }}</p>
                        <p class="card-header-desc">{{ t('pages.dashboard.indexTrendDesc') }}</p>
                    </div>
                    <v-chart class="chart" :option="indexTrendOption" autoresize />
                </el-card>
            </el-col>
            <el-col :span="8">
                <el-card shadow="hover">
                    <div class="card-header">
                        <p class="card-header-title">{{ t('pages.dashboard.investmentPieTitle') }}</p>
                        <p class="card-header-desc">{{ t('pages.dashboard.investmentPieDesc') }}</p>
                    </div>
                    <v-chart class="chart" :option="investmentPieOption" autoresize />
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" class="mgb20">
            <el-col :span="24">
                <el-card shadow="hover">
                    <div class="card-header">
                        <p class="card-header-title">{{ t('pages.dashboard.worldMapTitle') }}</p>
                        <p class="card-header-desc">{{ t('pages.dashboard.worldMapDesc') }}</p>
                    </div>
                    <v-chart class="chart chart-map" :option="worldMapOption" autoresize />
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" class="mgb20">
            <el-col :span="24">
                <el-card shadow="hover">
                    <div class="card-header">
                        <p class="card-header-title">{{ t('pages.dashboard.barRaceTitle') }}</p>
                        <p class="card-header-desc">{{ t('pages.dashboard.barRaceDesc') }}</p>
                    </div>
                    <v-chart class="chart chart-tall" :option="barRaceOption" autoresize />
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" class="mgb20">
            <el-col :span="24">
                <el-card shadow="hover">
                    <div class="card-header">
                        <p class="card-header-title">{{ t('pages.dashboard.intelligenceTitle') }}</p>
                        <p class="card-header-desc">{{ t('pages.dashboard.intelligenceDesc') }}</p>
                    </div>
                    <v-chart class="chart" :option="intelligenceTrendOption" autoresize />
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20">
            <el-col :span="10">
                <el-card shadow="hover" :body-style="{ height: '400px' }">
                    <div class="card-header">
                        <p class="card-header-title">{{ t('pages.dashboard.milestonesTitle') }}</p>
                        <p class="card-header-desc">{{ t('pages.dashboard.milestonesDesc') }}</p>
                    </div>
                    <el-timeline>
                        <el-timeline-item v-for="(activity, index) in aiMilestones" :key="index" :color="activity.color">
                            <div class="timeline-item">
                                <div>
                                    <p>{{ activity.content }}</p>
                                    <p class="timeline-desc">{{ activity.description }}</p>
                                </div>
                                <div class="timeline-time">{{ activity.timestamp }}</div>
                            </div>
                        </el-timeline-item>
                    </el-timeline>
                </el-card>
            </el-col>
            <el-col :span="14">
                <el-card shadow="hover" :body-style="{ height: '400px' }">
                    <div class="card-header">
                        <p class="card-header-title">{{ t('pages.dashboard.rankTitle') }}</p>
                        <p class="card-header-desc">{{ t('pages.dashboard.rankDesc') }}</p>
                    </div>
                    <div>
                        <div class="rank-item" v-for="(rank, index) in ranks" :key="rank.title">
                            <div class="rank-item-avatar">{{ index + 1 }}</div>
                            <div class="rank-item-content">
                                <div class="rank-item-top">
                                    <div class="rank-item-title">{{ rank.title }}</div>
                                    <div class="rank-item-desc">{{ t('pages.dashboard.rankScore', { value: rank.value }) }}</div>
                                </div>
                                <el-progress
                                    :show-text="false"
                                    striped
                                    :stroke-width="10"
                                    :percentage="rank.percent"
                                    :color="rank.color"
                                />
                            </div>
                        </div>
                    </div>
                </el-card>
            </el-col>
        </el-row>
    </div>
</template>

<script setup lang="ts" name="dashboard">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import countup from '@/components/countup.vue';
import { registerMap, use } from 'echarts/core';
import { BarChart, LineChart, MapChart, PieChart } from 'echarts/charts';
import {
    GridComponent,
    TooltipComponent,
    LegendComponent,
    TimelineComponent,
    VisualMapComponent,
    GeoComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import VChart from 'vue-echarts';
import worldJson from './chart/world.json';
import {
    buildIndexTrendOption,
    buildInvestmentBarRaceOption,
    buildInvestmentPieOption,
    buildRegionRanks,
    buildSummaryCards,
    buildWorldMapOption,
    type DashboardChartTexts,
} from './chart/ai-index-data';
import { buildIntelligenceTrendOption } from './chart/ai-intelligence-data';

const { t, tm } = useI18n();

use([
    CanvasRenderer,
    BarChart,
    GridComponent,
    LineChart,
    MapChart,
    PieChart,
    TooltipComponent,
    LegendComponent,
    TimelineComponent,
    VisualMapComponent,
    GeoComponent,
]);

registerMap('world', worldJson as Parameters<typeof registerMap>[1]);

const chartTexts = computed<DashboardChartTexts>(() => ({
    countryLabel: (country) => t(`pages.dashboard.countries.${country}`, country),
    aiIndex: t('pages.dashboard.mapIndex'),
    investmentBillion: t('pages.dashboard.investmentBillion'),
    investmentAxis: t('pages.dashboard.investmentAxis'),
    yearSuffix: t('pages.dashboard.yearSuffix'),
    othersRegion: t('pages.dashboard.othersRegion'),
    mapHigh: t('pages.dashboard.mapHigh'),
    mapLow: t('pages.dashboard.mapLow'),
    noData: t('pages.dashboard.noData'),
    formatTooltipIndex: (score) => t('pages.dashboard.tooltipIndex', { value: score }),
    formatTooltipInvestment: (v) => t('pages.dashboard.tooltipInvestment', { value: v }),
    formatTooltipPapers: (v) => t('pages.dashboard.tooltipPapers', { value: v }),
}));

const summary = buildSummaryCards();
const ranks = computed(() => buildRegionRanks(chartTexts.value));
const aiMilestones = computed(
    () => tm('pages.dashboard.milestones') as { content: string; description: string; timestamp: string; color: string }[],
);
const indexTrendOption = computed(() => buildIndexTrendOption(chartTexts.value));
const investmentPieOption = computed(() => buildInvestmentPieOption(chartTexts.value));
const barRaceOption = computed(() => buildInvestmentBarRaceOption(chartTexts.value));
const worldMapOption = computed(() => buildWorldMapOption(2026, chartTexts.value));
const intelligenceTrendOption = computed(() =>
    buildIntelligenceTrendOption(
        tm('pages.dashboard.intelligenceMetrics') as Record<string, string>,
        t('pages.dashboard.abilityScore'),
    ),
);
</script>

<style>
.card-body {
    display: flex;
    align-items: center;
    height: 100px;
    padding: 0;
}
</style>
<style scoped>
.card-content {
    flex: 1;
    text-align: center;
    font-size: 14px;
    color: #999;
    padding: 0 20px;
}

.card-num {
    font-size: 30px;
}

.card-icon {
    font-size: 50px;
    width: 100px;
    height: 100px;
    text-align: center;
    line-height: 100px;
    color: #fff;
}

.bg1 {
    background: #2d8cf0;
}

.bg2 {
    background: #64d572;
}

.bg3 {
    background: #f25e43;
}

.bg4 {
    background: #e9a745;
}

.color1 {
    color: #2d8cf0;
}

.color2 {
    color: #64d572;
}

.color3 {
    color: #f25e43;
}

.color4 {
    color: #e9a745;
}

.chart {
    width: 100%;
    height: 400px;
}

.chart-tall {
    height: 520px;
}

.chart-map {
    height: 480px;
}

.card-header {
    padding-left: 10px;
    margin-bottom: 20px;
}

.card-header-title {
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 5px;
}

.card-header-desc {
    font-size: 14px;
    color: #999;
}

.timeline-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 16px;
    color: #000;
}

.timeline-time,
.timeline-desc {
    font-size: 12px;
    color: #787878;
}

.rank-item {
    display: flex;
    align-items: center;
    margin-bottom: 20px;
}

.rank-item-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #f2f2f2;
    text-align: center;
    line-height: 40px;
    margin-right: 10px;
}

.rank-item-content {
    flex: 1;
}

.rank-item-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #343434;
    margin-bottom: 10px;
}

.rank-item-desc {
    font-size: 14px;
    color: #999;
}
</style>
