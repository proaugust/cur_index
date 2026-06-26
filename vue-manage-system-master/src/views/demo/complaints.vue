<template>
    <div class="container complaints-page">
        <el-card class="mgb20 samples-card" shadow="hover" v-loading="samplesLoading">
            <template #header>
                <div class="stats-header">
                    <div>
                        <div class="content-title">投诉样本查询</div>
                        <p class="stats-desc">按地区、投诉时间、正文关键词检索</p>
                    </div>
                    <el-button type="primary" :loading="samplesLoading" @click="searchSamples">查询</el-button>
                </div>
            </template>

            <el-form :inline="true" class="samples-form" @submit.prevent="searchSamples">
                <el-form-item label="地区">
                    <el-input v-model="sampleQuery.address" placeholder="模糊匹配地址" clearable style="width: 160px" />
                </el-form-item>
                <el-form-item label="投诉时间">
                    <el-date-picker
                        v-model="sampleQuery.dateRange"
                        type="daterange"
                        range-separator="至"
                        start-placeholder="开始日期"
                        end-placeholder="结束日期"
                        value-format="YYYY-MM-DD"
                        style="width: 260px"
                    />
                </el-form-item>
                <el-form-item label="正文">
                    <el-input v-model="sampleQuery.text" placeholder="模糊匹配投诉内容" clearable style="width: 220px" />
                </el-form-item>
                <el-form-item label="分类">
                    <el-input v-model="sampleQuery.category_name" placeholder="可选" clearable style="width: 140px" />
                </el-form-item>
            </el-form>

            <el-table :data="sampleRows" stripe size="small" empty-text="暂无数据，点击「查询」加载">
                <el-table-column prop="id" label="ID" width="70" />
                <el-table-column prop="address" label="地区" width="100" show-overflow-tooltip />
                <el-table-column label="投诉时间" width="170">
                    <template #default="{ row }">
                        {{ formatComplaintTime(row.complaint_time) }}
                    </template>
                </el-table-column>
                <el-table-column prop="category_name" label="分类" width="120" show-overflow-tooltip />
                <el-table-column prop="complaint_text" label="投诉内容" min-width="260" show-overflow-tooltip />
                <el-table-column label="相似度" width="90" align="right">
                    <template #default="{ row }">
                        {{ row.similarity != null ? row.similarity.toFixed(4) : '—' }}
                    </template>
                </el-table-column>
            </el-table>

            <el-pagination
                v-if="sampleTotal > 0"
                class="samples-pagination"
                background
                layout="total, sizes, prev, pager, next"
                :total="sampleTotal"
                :page-size="samplePage.page_size"
                :page-sizes="[10, 20, 50]"
                v-model:current-page="samplePage.page"
                @size-change="onSamplePageSizeChange"
                @current-change="loadSamples"
            />
        </el-card>

        <el-card class="mgb20 stats-card" shadow="hover" v-loading="loading">
            <template #header>
                <div class="stats-header">
                    <div>
                        <div class="content-title">投诉多维统计</div>
                        <p class="stats-desc">按投诉类型、地区、投诉时间实时聚合</p>
                    </div>
                    <el-button type="primary" :loading="loading" @click="loadStats">刷新统计</el-button>
                </div>
            </template>

            <el-empty v-if="!stats && !loading" description="点击「刷新统计」加载数据" />

            <template v-if="stats">
                <el-row :gutter="20" class="summary-row">
                    <el-col v-for="card in summaryCards" :key="card.key" :xs="12" :sm="6">
                        <div class="summary-card" :class="card.bg">
                            <div class="summary-label">{{ card.label }}</div>
                            <countup class="summary-value" :end="card.value" />
                            <div v-if="card.extra" class="summary-extra">{{ card.extra }}</div>
                        </div>
                    </el-col>
                </el-row>

                <div class="overview-block">
                    <div class="section-title">三维度概览</div>
                    <el-row :gutter="16">
                        <el-col v-for="section in dimensionSections" :key="section.key" :xs="24" :lg="8">
                            <div class="overview-panel">
                                <div class="overview-head">
                                    <span class="overview-name">{{ section.title }}</span>
                                    <el-tag size="small" type="info">{{ section.items.length }} 项</el-tag>
                                </div>
                                <div v-if="section.topItem" class="overview-top">
                                    TOP：<strong>{{ section.topItem.label }}</strong>
                                    <span>{{ section.topItem.count }} 条 · {{ section.topItem.percentage }}%</span>
                                </div>
                                <component
                                    :is="VChart"
                                    v-if="VChart"
                                    class="overview-chart"
                                    :option="section.miniOption"
                                    autoresize
                                />
                            </div>
                        </el-col>
                    </el-row>
                </div>

                <div class="detail-block">
                    <div class="section-title">维度明细</div>
                    <el-tabs v-model="activeDimension" type="border-card">
                        <el-tab-pane
                            v-for="section in dimensionSections"
                            :key="section.key"
                            :label="section.title"
                            :name="section.key"
                        >
                            <el-row :gutter="16" class="dimension-metrics">
                                <el-col :xs="24" :sm="8">
                                    <el-statistic title="分组数量" :value="section.items.length" />
                                </el-col>
                                <el-col :xs="24" :sm="8">
                                    <el-statistic
                                        v-if="section.topItem"
                                        title="最高项"
                                        :value="section.topItem.count"
                                        :suffix="`条 · ${section.topItem.label}`"
                                    />
                                </el-col>
                                <el-col :xs="24" :sm="8">
                                    <el-statistic
                                        v-if="section.topItem"
                                        title="最高占比"
                                        :value="section.topItem.percentage"
                                        suffix="%"
                                    />
                                </el-col>
                            </el-row>

                            <el-row :gutter="16" class="dimension-content">
                                <el-col :xs="24" :xl="10">
                                    <el-table :data="section.items" stripe size="small" max-height="380">
                                        <el-table-column type="index" label="#" width="50" />
                                        <el-table-column prop="label" :label="section.columnLabel" min-width="120" />
                                        <el-table-column prop="count" label="数量" width="90" align="right" sortable />
                                        <el-table-column label="占比" min-width="160">
                                            <template #default="{ row }">
                                                <div class="pct-cell">
                                                    <el-progress
                                                        :percentage="row.percentage"
                                                        :stroke-width="10"
                                                        :color="section.color"
                                                    />
                                                    <span class="pct-text">{{ row.percentage }}%</span>
                                                </div>
                                            </template>
                                        </el-table-column>
                                    </el-table>
                                </el-col>
                                <el-col :xs="24" :xl="7">
                                    <component
                                        :is="VChart"
                                        v-if="VChart"
                                        class="stats-chart"
                                        :option="section.barOption"
                                        autoresize
                                    />
                                </el-col>
                                <el-col :xs="24" :xl="7">
                                    <component
                                        :is="VChart"
                                        v-if="VChart"
                                        class="stats-chart"
                                        :option="section.secondaryOption"
                                        autoresize
                                    />
                                </el-col>
                            </el-row>
                        </el-tab-pane>
                    </el-tabs>
                </div>
            </template>
        </el-card>

        <LazyApiDebugPanel endpoint-key="complaint" class="debug-panel" />
    </div>
</template>

<script setup lang="ts" name="demo-complaints">
import { computed, onMounted, ref, shallowRef, type Component } from 'vue';
import LazyApiDebugPanel from '@/components/lazy-api-debug-panel.vue';
import countup from '@/components/countup.vue';
import { getComplaintStats, getComplaintSamples } from '@/api';

type EChartsGraphic = typeof import('echarts/core').graphic;
let echartsGraphic: EChartsGraphic | null = null;
const VChart = shallowRef<Component | null>(null);

async function ensureCharts() {
    if (VChart.value) return;

    const [core, charts, components, renderers, vueEcharts] = await Promise.all([
        import('echarts/core'),
        import('echarts/charts'),
        import('echarts/components'),
        import('echarts/renderers'),
        import('vue-echarts'),
    ]);

    echartsGraphic = core.graphic;
    core.use([
        renderers.CanvasRenderer,
        charts.BarChart,
        charts.LineChart,
        charts.PieChart,
        components.GridComponent,
        components.TooltipComponent,
        components.LegendComponent,
    ]);
    VChart.value = vueEcharts.default;
}

interface ComplaintStatsCountItem {
    label: string;
    count: number;
    percentage: number;
}

interface ComplaintStatsReport {
    total: number;
    classified: number;
    unclassified: number;
    by_category: ComplaintStatsCountItem[];
    by_address: ComplaintStatsCountItem[];
    by_time: ComplaintStatsCountItem[];
}

type DimensionKey = 'category' | 'address' | 'time';

const DIMENSION_COLORS: Record<DimensionKey, string> = {
    category: '#009688',
    address: '#2d8cf0',
    time: '#f25e43',
};

const loading = ref(true);
const stats = ref<ComplaintStatsReport | null>(null);
const activeDimension = ref<DimensionKey>('category');

interface ComplaintSample {
    id: number;
    complaint_text: string;
    address: string | null;
    complaint_time: string | null;
    category_id: number | null;
    category_name: string | null;
    similarity: number | null;
}

interface ComplaintSamplesPage {
    items: ComplaintSample[];
    total: number;
    page: number;
    page_size: number;
}

const samplesLoading = ref(false);
const sampleRows = ref<ComplaintSample[]>([]);
const sampleTotal = ref(0);
const sampleQuery = ref({
    address: '',
    text: '',
    category_name: '',
    dateRange: null as [string, string] | null,
});
const samplePage = ref({ page: 1, page_size: 10 });

const classifiedRate = computed(() => {
    if (!stats.value?.total) return 0;
    return Math.round((stats.value.classified / stats.value.total) * 1000) / 10;
});

const summaryCards = computed(() => {
    if (!stats.value) return [];
    return [
        { key: 'total', label: '投诉总数', value: stats.value.total, bg: 'bg-total', extra: '全部明细记录' },
        { key: 'classified', label: '已归类', value: stats.value.classified, bg: 'bg-classified', extra: `归类率 ${classifiedRate.value}%` },
        { key: 'unclassified', label: '未归类', value: stats.value.unclassified, bg: 'bg-unclassified', extra: '待向量归类' },
        {
            key: 'categories',
            label: '投诉类型数',
            value: stats.value.by_category.length,
            bg: 'bg-types',
            extra: `地区 ${stats.value.by_address.length} · 日期 ${stats.value.by_time.length}`,
        },
    ];
});

function topItem(items: ComplaintStatsCountItem[]) {
    if (!items.length) return null;
    return items.reduce((best, item) => (item.count > best.count ? item : best), items[0]);
}

function buildBarOption(items: ComplaintStatsCountItem[], title: string, color: string, horizontal = false) {
    const labels = items.map((item) => item.label);
    const counts = items.map((item) => item.count);
    return {
        title: { text: `${title} · 数量`, left: 'center', textStyle: { fontSize: 14 } },
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: horizontal
            ? { type: 'value', minInterval: 1 }
            : { type: 'category', data: labels, axisLabel: { rotate: labels.length > 6 ? 30 : 0 } },
        yAxis: horizontal
            ? { type: 'category', data: [...labels].reverse(), inverse: true }
            : { type: 'value', minInterval: 1 },
        series: [
            {
                type: 'bar',
                data: horizontal ? [...counts].reverse() : counts,
                itemStyle: {
                    color: horizontal
                        ? new echartsGraphic!.LinearGradient(0, 0, 1, 0, [
                              { offset: 0, color: color },
                              { offset: 1, color: `${color}88` },
                          ])
                        : color,
                    borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0],
                },
            },
        ],
    };
}

function buildPieOption(items: ComplaintStatsCountItem[], title: string, donut = false) {
    return {
        title: { text: `${title} · 占比`, left: 'center', textStyle: { fontSize: 14 } },
        tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 条 ({d}%)' },
        legend: { type: 'scroll', bottom: 0 },
        series: [
            {
                type: 'pie',
                radius: donut ? ['42%', '62%'] : '58%',
                center: ['50%', '46%'],
                data: items.map((item) => ({ name: item.label, value: item.count })),
                emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.2)' } },
            },
        ],
    };
}

function buildLineOption(items: ComplaintStatsCountItem[], title: string, color: string) {
    const labels = items.map((item) => item.label);
    const counts = items.map((item) => item.count);
    return {
        title: { text: `${title} · 趋势`, left: 'center', textStyle: { fontSize: 14 } },
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'category', boundaryGap: false, data: labels, axisLabel: { rotate: labels.length > 10 ? 45 : 0, fontSize: 10 } },
        yAxis: { type: 'value', minInterval: 1 },
        series: [
            {
                type: 'line',
                smooth: true,
                data: counts,
                areaStyle: {
                    color: new echartsGraphic!.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: `${color}66` },
                        { offset: 1, color: `${color}08` },
                    ]),
                },
                lineStyle: { color, width: 3 },
                itemStyle: { color },
            },
        ],
    };
}

function buildMiniBarOption(items: ComplaintStatsCountItem[], color: string, limit = 6) {
    const top = items.slice(0, limit);
    return {
        tooltip: { trigger: 'axis', confine: true },
        grid: { left: 8, right: 8, top: 8, bottom: 8, containLabel: true },
        xAxis: { type: 'category', data: top.map((item) => item.label), show: top.length <= 4, axisLabel: { fontSize: 10 } },
        yAxis: { type: 'value', show: false },
        series: [
            {
                type: 'bar',
                data: top.map((item) => item.count),
                barMaxWidth: 18,
                itemStyle: { color, borderRadius: [3, 3, 0, 0] },
            },
        ],
    };
}

const dimensionSections = computed(() => {
    if (!stats.value) return [];
    const configs: Array<{
        key: DimensionKey;
        title: string;
        columnLabel: string;
        items: ComplaintStatsCountItem[];
        color: string;
        horizontalBar: boolean;
        useLineSecondary: boolean;
        miniLimit?: number;
    }> = [
        {
            key: 'category',
            title: '按投诉类型',
            columnLabel: '类型',
            items: stats.value.by_category,
            color: DIMENSION_COLORS.category,
            horizontalBar: true,
            useLineSecondary: false,
            miniLimit: 8,
        },
        {
            key: 'address',
            title: '按地区',
            columnLabel: '地区',
            items: stats.value.by_address,
            color: DIMENSION_COLORS.address,
            horizontalBar: false,
            useLineSecondary: false,
        },
        {
            key: 'time',
            title: '按时间（天）',
            columnLabel: '日期',
            items: stats.value.by_time,
            color: DIMENSION_COLORS.time,
            horizontalBar: false,
            useLineSecondary: true,
            miniLimit: 7,
        },
    ];

    return configs.map((config) => ({
        ...config,
        topItem: topItem(config.items),
        miniOption: buildMiniBarOption(config.items, config.color, config.miniLimit ?? 6),
        barOption: buildBarOption(config.items, config.title, config.color, config.horizontalBar),
        secondaryOption: config.useLineSecondary
            ? buildLineOption(config.items, config.title, config.color)
            : buildPieOption(config.items, config.title, config.key === 'category'),
    }));
});

async function loadStats() {
    loading.value = true;
    try {
        const { data } = await getComplaintStats();
        await ensureCharts();
        stats.value = data as ComplaintStatsReport;
    } finally {
        loading.value = false;
    }
}

onMounted(() => {
    loadStats();
});

function formatComplaintTime(value: string | null) {
    if (!value) return '—';
    return value.replace('T', ' ').slice(0, 19);
}

async function loadSamples() {
    samplesLoading.value = true;
    try {
        const [time_from, time_to] = sampleQuery.value.dateRange ?? [undefined, undefined];
        const { data } = await getComplaintSamples({
            address: sampleQuery.value.address || undefined,
            text: sampleQuery.value.text || undefined,
            category_name: sampleQuery.value.category_name || undefined,
            time_from,
            time_to,
            page: samplePage.value.page,
            page_size: samplePage.value.page_size,
        });
        const page = data as ComplaintSamplesPage;
        sampleRows.value = page.items;
        sampleTotal.value = page.total;
        samplePage.value.page = page.page;
        samplePage.value.page_size = page.page_size;
    } finally {
        samplesLoading.value = false;
    }
}

function searchSamples() {
    samplePage.value.page = 1;
    loadSamples();
}

function onSamplePageSizeChange(size: number) {
    samplePage.value.page_size = size;
    samplePage.value.page = 1;
    loadSamples();
}
</script>

<style scoped>
.stats-card {
    margin-top: 20px;
}

.debug-panel {
    margin-top: 20px;
}

.samples-form {
    margin-bottom: 12px;
}

.samples-pagination {
    margin-top: 16px;
    justify-content: flex-end;
}

.stats-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
}

.stats-desc {
    margin: 6px 0 0;
    color: #909399;
    font-size: 13px;
}

.content-title {
    font-size: 16px;
    font-weight: 600;
}

.summary-row {
    margin-bottom: 20px;
}

.summary-card {
    border-radius: 8px;
    padding: 18px 20px;
    color: #fff;
    min-height: 108px;
}

.summary-label {
    font-size: 13px;
    opacity: 0.92;
}

.summary-value {
    display: block;
    margin-top: 8px;
    font-size: 30px;
    font-weight: 700;
    line-height: 1.1;
}

.summary-extra {
    margin-top: 8px;
    font-size: 12px;
    opacity: 0.88;
}

.bg-total {
    background: linear-gradient(135deg, #2d8cf0, #57a3f3);
}

.bg-classified {
    background: linear-gradient(135deg, #009688, #26a69a);
}

.bg-unclassified {
    background: linear-gradient(135deg, #f25e43, #ff7a63);
}

.bg-types {
    background: linear-gradient(135deg, #9c27b0, #ba68c8);
}

.section-title {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 12px;
}

.overview-block,
.detail-block {
    margin-top: 8px;
}

.overview-panel {
    border: 1px solid #ebeef5;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 16px;
    background: #fafafa;
}

.overview-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
}

.overview-name {
    font-weight: 600;
}

.overview-top {
    font-size: 13px;
    color: #606266;
    margin-bottom: 4px;
}

.overview-top strong {
    color: #303133;
}

.overview-top span {
    margin-left: 8px;
    color: #909399;
}

.overview-chart {
    width: 100%;
    height: 160px;
}

.dimension-metrics {
    margin-bottom: 16px;
}

.dimension-content {
    margin-top: 4px;
}

.stats-chart {
    width: 100%;
    height: 380px;
    margin-top: 12px;
}

.pct-cell {
    display: flex;
    align-items: center;
    gap: 8px;
}

.pct-cell :deep(.el-progress) {
    flex: 1;
}

.pct-text {
    width: 48px;
    text-align: right;
    font-size: 12px;
    color: #606266;
}

@media (min-width: 1200px) {
    .stats-chart {
        margin-top: 0;
    }
}
</style>
