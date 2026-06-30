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
                        <div>美国 AI 指数 (2026)</div>
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
                        <div>全球 AI 投资 (十亿美元)</div>
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
                        <div>全球发表论文 (千篇)</div>
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
                        <div>{{ summary.countryCount }} 国平均 AI 指数</div>
                    </div>
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" class="mgb20">
            <el-col :span="16">
                <el-card shadow="hover">
                    <div class="card-header">
                        <p class="card-header-title">全球 AI 指数趋势</p>
                        <p class="card-header-desc">2015–2026 年 14 国/地区 AI_Index_Score 多线对比</p>
                    </div>
                    <v-chart class="chart" :option="indexTrendOption" autoresize />
                </el-card>
            </el-col>
            <el-col :span="8">
                <el-card shadow="hover">
                    <div class="card-header">
                        <p class="card-header-title">2026 投资占比</p>
                        <p class="card-header-desc">AI 投资 Top6 + 其他地区（十亿美元）</p>
                    </div>
                    <v-chart class="chart" :option="investmentPieOption" autoresize />
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" class="mgb20">
            <el-col :span="24">
                <el-card shadow="hover">
                    <div class="card-header">
                        <p class="card-header-title">2026 全球 AI 指数分布</p>
                        <p class="card-header-desc">14 国/地区有数据（有颜色的区域）；其余国家悬停显示「暂无数据」</p>
                    </div>
                    <v-chart class="chart chart-map" :option="worldMapOption" autoresize />
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" class="mgb20">
            <el-col :span="24">
                <el-card shadow="hover">
                    <div class="card-header">
                        <p class="card-header-title">全球 AI 投资动态排行</p>
                        <p class="card-header-desc">2015–2026 年各国投资金额动态条形图（自动播放，可点击时间轴切换年份）</p>
                    </div>
                    <v-chart class="chart chart-tall" :option="barRaceOption" autoresize />
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" class="mgb20">
            <el-col :span="24">
                <el-card shadow="hover">
                    <div class="card-header">
                        <p class="card-header-title">AI 智力提升趋势</p>
                        <p class="card-header-desc">2018–2026 年模型在阅读理解、数学推理、代码生成、复杂推理（人类考试）四项能力得分</p>
                    </div>
                    <v-chart class="chart" :option="intelligenceTrendOption" autoresize />
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20">
            <el-col :span="10">
                <el-card shadow="hover" :body-style="{ height: '400px' }">
                    <div class="card-header">
                        <p class="card-header-title">发展里程碑</p>
                        <p class="card-header-desc">全球 AI 发展关键节点</p>
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
                        <p class="card-header-title">AI 指数排行</p>
                        <p class="card-header-desc">2026 年 AI 指数 Top5</p>
                    </div>
                    <div>
                        <div class="rank-item" v-for="(rank, index) in ranks" :key="rank.title">
                            <div class="rank-item-avatar">{{ index + 1 }}</div>
                            <div class="rank-item-content">
                                <div class="rank-item-top">
                                    <div class="rank-item-title">{{ rank.title }}</div>
                                    <div class="rank-item-desc">指数：{{ rank.value }}</div>
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
    aiMilestones,
    buildIndexTrendOption,
    buildInvestmentBarRaceOption,
    buildInvestmentPieOption,
    buildRegionRanks,
    buildSummaryCards,
    buildWorldMapOption,
} from './chart/ai-index-data';
import { buildIntelligenceTrendOption } from './chart/ai-intelligence-data';

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

const summary = buildSummaryCards();
const ranks = buildRegionRanks();
const indexTrendOption = computed(() => buildIndexTrendOption());
const investmentPieOption = computed(() => buildInvestmentPieOption());
const barRaceOption = computed(() => buildInvestmentBarRaceOption());
const worldMapOption = buildWorldMapOption();
const intelligenceTrendOption = buildIntelligenceTrendOption();
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
