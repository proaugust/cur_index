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
                        <p class="card-header-desc">
                            {{ t('pages.dashboard.indexTrendDesc') }}
                            <span v-if="trendsUpdatedAt" style="margin-left: 10px; font-size: 12px; color: #999;">(自动更新于: {{ trendsUpdatedAt }})</span>
                        </p>
                    </div>
                    <component :is="VChart" v-if="VChart" class="chart" :option="indexTrendOption" autoresize />
                </el-card>
            </el-col>
            <el-col :span="8">
                <el-card shadow="hover">
                    <div class="card-header">
                        <p class="card-header-title">{{ t('pages.dashboard.investmentPieTitle') }}</p>
                        <p class="card-header-desc">{{ t('pages.dashboard.investmentPieDesc') }}</p>
                    </div>
                    <component :is="VChart" v-if="VChart" class="chart" :option="investmentPieOption" autoresize />
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
                    <component :is="VChart" v-if="VChart" class="chart chart-map" :option="worldMapOption" autoresize />
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
                    <component :is="VChart" v-if="VChart" class="chart chart-tall" :option="barRaceOption" autoresize />
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="20" class="mgb20">
            <el-col :span="24">
                <el-card shadow="hover">
                    <div class="card-header">
                        <p class="card-header-title">{{ t('pages.dashboard.intelligenceTitle') }}</p>
                        <p class="card-header-desc">
                            {{ t('pages.dashboard.intelligenceDesc') }}
                            <span v-if="trendsUpdatedAt" style="margin-left: 10px; font-size: 12px; color: #999;">(自动更新于: {{ trendsUpdatedAt }})</span>
                        </p>
                    </div>
                    <component :is="VChart" v-if="VChart" class="chart" :option="intelligenceTrendOption" autoresize />
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

        <el-row :gutter="20" class="mgb20" style="margin-top: 20px;">
            <el-col :span="24">
                <el-card shadow="hover">
                    <div class="card-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <div>
                            <p class="card-header-title">
                                <el-icon style="vertical-align: middle; margin-right: 8px;"><Histogram /></el-icon>
                                Epoch AI 全球大模型多维洞察看板
                            </p>
                            <p class="card-header-desc">每日自动同步官方全量模型库，追踪 AI 算力与参数膨胀前沿规律（更新时间：{{ epochStats.updated_at || '加载中...' }}）</p>
                        </div>
                        <div style="font-size: 14px; color: #666; display: flex; gap: 15px; background: #f5f7fa; padding: 10px 15px; border-radius: 8px;">
                            <span>模型总数: <strong style="color: #2d8cf0; font-size: 16px;">{{ epochStats.counts.all_models }}</strong></span>
                            <span>显著里程碑: <strong style="color: #e9a745; font-size: 16px;">{{ epochStats.counts.notable_models }}</strong></span>
                            <span>前沿标杆: <strong style="color: #f25e43; font-size: 16px;">{{ epochStats.counts.frontier_models }}</strong></span>
                            <span>超大规模: <strong style="color: #64d572; font-size: 16px;">{{ epochStats.counts.large_scale_models }}</strong></span>
                        </div>
                    </div>

                    <el-tabs v-model="activeEpochTab" type="border-card" style="border-radius: 6px;">
                        <!-- Tab 1: 散点图演进 -->
                        <el-tab-pane label="模型参数与算力演进（对数气泡图）" name="evolution">
                            <div style="padding: 10px 0;">
                                <p style="font-size: 13px; color: #7f8c8d; margin-bottom: 15px; line-height: 1.5;">
                                    <strong>图表说明：</strong> X 轴为大模型发布时间，Y 轴为<strong>参数规模 (对数 Log10 刻度)</strong>。
                                    气泡的大小代表<strong>训练算力 (Training FLOPs)</strong>，气泡越大表示训练该模型消耗的物理算力越恐怖。
                                    可在上方图例点击筛选不同的技术领域。
                                </p>
                                <component :is="VChart" v-if="VChart" class="chart" :option="epochScatterOption" autoresize style="height: 450px;" />
                            </div>
                        </el-tab-pane>

                        <!-- Tab 2: 全球格局与开源 -->
                        <el-tab-pane label="全球研发格局与开源比例分布" name="global">
                            <el-row :gutter="20">
                                <el-col :span="16">
                                    <div style="padding: 10px 0;">
                                        <p style="font-size: 13px; color: #7f8c8d; margin-bottom: 15px;">
                                            <strong>全球大模型年度发布趋势 (按国家/地区堆叠)</strong>：展示 2018-2026 年间，全球各大经济体发布主流大模型的数量分布演变。
                                        </p>
                                        <component :is="VChart" v-if="VChart" class="chart" :option="epochGlobalOption" autoresize style="height: 380px;" />
                                    </div>
                                </el-col>
                                <el-col :span="8" style="border-left: 1px solid #f0f0f0;">
                                    <div style="padding: 10px 0;">
                                        <p style="font-size: 13px; color: #7f8c8d; margin-bottom: 15px; text-align: center;">
                                            <strong>大模型权重开放度 (开源 vs 闭源比例)</strong>
                                        </p>
                                        <component :is="VChart" v-if="VChart" class="chart" :option="epochWeightsOption" autoresize style="height: 380px;" />
                                    </div>
                                </el-col>
                            </el-row>
                        </el-tab-pane>

                        <!-- Tab 3: 最新发布大模型库 -->
                        <el-tab-pane label="全量最新收录大模型库" name="releases">
                            <div style="padding: 10px 0;">
                                <p style="font-size: 13px; color: #7f8c8d; margin-bottom: 15px;">
                                    <strong>最近发布的 15 个代表性大模型一览表</strong>（数据自动同步自 Epoch AI 官方数据库，按发布日期降序排列）：
                                </p>
                                <el-table :data="epochStats.latest_releases" style="width: 100%" size="default" border stripe>
                                    <el-table-column prop="name" label="模型名称 (Model)" min-width="150" show-overflow-tooltip>
                                        <template #default="scope">
                                            <span style="font-weight: bold; color: #2d8cf0;">{{ scope.row.name }}</span>
                                        </template>
                                    </el-table-column>
                                    <el-table-column prop="org" label="开发机构 (Organization)" min-width="150" show-overflow-tooltip />
                                    <el-table-column prop="date" label="发布日期" width="130" sortable />
                                    <el-table-column prop="domain" label="核心领域 (Domain)" width="140" />
                                    <el-table-column prop="parameters" label="参数规模 (Params)" width="150" show-overflow-tooltip>
                                        <template #default="scope">
                                            <span>{{ formatParams(parseFloat(scope.row.parameters)) || scope.row.parameters }}</span>
                                        </template>
                                    </el-table-column>
                                    <el-table-column prop="accessibility" label="可获取程度" min-width="150" show-overflow-tooltip />
                                </el-table>
                            </div>
                        </el-tab-pane>
                    </el-tabs>
                </el-card>
            </el-col>
        </el-row>
    </div>
</template>

<script setup lang="ts" name="dashboard">
import { computed, onMounted, shallowRef, ref, type Component } from 'vue';
import { useI18n } from 'vue-i18n';
import countup from '@/components/countup.vue';
import { fetchEpochStats, fetchAiTrendsStats } from '@/api';
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
const VChart = shallowRef<Component | null>(null);

async function ensureDashboardCharts() {
    if (VChart.value) return;

    const [core, charts, components, renderers, vueEcharts, worldJson] = await Promise.all([
        import('echarts/core'),
        import('echarts/charts'),
        import('echarts/components'),
        import('echarts/renderers'),
        import('vue-echarts'),
        import('./chart/world.json'),
    ]);

    core.use([
        renderers.CanvasRenderer,
        charts.BarChart,
        charts.LineChart,
        charts.MapChart,
        charts.PieChart,
        charts.ScatterChart,
        components.GridComponent,
        components.TooltipComponent,
        components.LegendComponent,
        components.TimelineComponent,
        components.VisualMapComponent,
        components.GeoComponent,
    ]);

    const worldMap = (worldJson as { default?: unknown }).default ?? worldJson;
    core.registerMap('world', worldMap as Parameters<typeof core.registerMap>[1]);
    VChart.value = vueEcharts.default;
}

const dynamicTrends = ref<any[] | undefined>(undefined);
const dynamicIntelligence = ref<any[] | undefined>(undefined);
const trendsUpdatedAt = ref<string>('');

onMounted(async () => {
    void ensureDashboardCharts();
    try {
        const [epochRes, trendsRes] = await Promise.all([
            fetchEpochStats(),
            fetchAiTrendsStats(),
        ]);
        epochStats.value = epochRes.data;
        if (trendsRes.data && trendsRes.data.status === 'success') {
            dynamicTrends.value = trendsRes.data.trends;
            dynamicIntelligence.value = trendsRes.data.intelligence;
            trendsUpdatedAt.value = trendsRes.data.updated_at;
        }
    } catch (err) {
        console.error('加载仪表盘数据失败', err);
    }
});

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

const summary = computed(() => buildSummaryCards(dynamicTrends.value));
const ranks = computed(() => buildRegionRanks(dynamicTrends.value, chartTexts.value));
const aiMilestones = computed(
    () => tm('pages.dashboard.milestones') as { content: string; description: string; timestamp: string; color: string }[],
);
const indexTrendOption = computed(() => buildIndexTrendOption(dynamicTrends.value, chartTexts.value));
const investmentPieOption = computed(() => buildInvestmentPieOption(dynamicTrends.value, chartTexts.value));
const barRaceOption = computed(() => buildInvestmentBarRaceOption(dynamicTrends.value, chartTexts.value));
const worldMapOption = computed(() => buildWorldMapOption(dynamicTrends.value, 2026, chartTexts.value));
const intelligenceTrendOption = computed(() =>
    buildIntelligenceTrendOption(
        dynamicIntelligence.value,
        tm('pages.dashboard.intelligenceMetrics') as Record<string, string>,
        t('pages.dashboard.abilityScore'),
    ),
);

const activeEpochTab = ref('evolution');

const epochStats = ref({
    status: 'initializing',
    updated_at: '',
    counts: {
        all_models: 0,
        notable_models: 0,
        frontier_models: 0,
        large_scale_models: 0
    },
    yearly_countries: [] as Array<{ year: number; countries: Record<string, number> }>,
    domains: {} as Record<string, number>,
    open_weights: { Yes: 0, No: 0, Unknown: 0 } as Record<string, number>,
    scatter_data: [] as Array<{
        name: string;
        date: string;
        org: string;
        params: number | null;
        compute: number | null;
        domain: string;
        is_frontier: boolean;
        is_notable: boolean;
    }>,
    latest_releases: [] as Array<{
        name: string;
        org: string;
        date: string;
        domain: string;
        parameters: string;
        accessibility: string;
    }>
});

function formatParams(p: number | null | undefined): string {
    if (!p) return '未知';
    if (p >= 1e12) return `${(p / 1e12).toFixed(1)}T (万亿)`;
    if (p >= 1e9) return `${(p / 1e9).toFixed(1)}B (十亿)`;
    if (p >= 1e6) return `${(p / 1e6).toFixed(1)}M (百万)`;
    return p.toLocaleString();
}

function formatCompute(c: number | null | undefined): string {
    if (!c) return '未知';
    if (c >= 1e26) return `${(c / 1e26).toFixed(1)} YottaFLOPs`;
    if (c >= 1e23) return `${(c / 1e23).toFixed(1)} ZettaFLOPs (10^23)`;
    if (c >= 1e20) return `${(c / 1e20).toFixed(1)} ExaFLOPs (10^20)`;
    if (c >= 1e15) return `${(c / 1e15).toFixed(1)} PetaFLOPs`;
    return `${c.toExponential(2)} FLOPs`;
}

// 散点图配置：X 轴为时间，Y 轴为参数量 (Log scale)，气泡大小为算力 FLOPs
const epochScatterOption = computed(() => {
    const domains = ['Language', 'Vision', 'Multimodal', 'Speech/Audio', 'Robotics', 'Other'];
    const domainNamesZh: Record<string, string> = {
        'Language': '语言模型 (Language)',
        'Vision': '计算机视觉 (Vision)',
        'Multimodal': '多模态 (Multimodal)',
        'Speech/Audio': '语音与音频 (Speech/Audio)',
        'Robotics': '机器人 (Robotics)',
        'Other': '其他领域 (Other)'
    };
    const colors = ['#2d8cf0', '#9b59b6', '#f25e43', '#e9a745', '#00bcd4', '#7f8c8d'];

    const series = domains.map((dom, idx) => {
        const filtered = epochStats.value.scatter_data.filter(d => d.domain === dom && d.params);
        return {
            name: domainNamesZh[dom],
            type: 'scatter',
            itemStyle: {
                color: colors[idx]
            },
            data: filtered.map(d => [d.date, d.params, d.compute, d.name, d.org, d.domain, d.is_frontier]),
            emphasis: {
                focus: 'series'
            }
        };
    });

    return {
        tooltip: {
            trigger: 'item',
            formatter: (params: any) => {
                const item = params.value;
                if (!item) return '';
                const name = item[3];
                const org = item[4];
                const pub_date = item[0];
                const dom = domainNamesZh[item[5]] || item[5];
                const p = item[1];
                const c = item[2];
                const is_front = item[6] ? '<span style="color:#f25e43;font-weight:bold;margin-left:5px;">★ 前沿</span>' : '';
                return `<div style="padding: 5px; font-family: sans-serif; line-height: 1.6;">
                    <div style="font-size: 14px; font-weight: bold; color: #2d8cf0; margin-bottom: 5px;">${name}${is_front}</div>
                    <span style="color: #999;">研发机构:</span> ${org}<br/>
                    <span style="color: #999;">发布日期:</span> ${pub_date}<br/>
                    <span style="color: #999;">技术领域:</span> ${dom}<br/>
                    <span style="color: #999;">参数规模:</span> ${formatParams(p)}<br/>
                    <span style="color: #999;">训练算力:</span> ${formatCompute(c)}
                </div>`;
            }
        },
        legend: {
            type: 'scroll',
            top: 0
        },
        grid: {
            top: '15%',
            left: '3%',
            right: '4%',
            bottom: '5%',
            containLabel: true
        },
        xAxis: {
            type: 'time',
            name: '发布时间',
            splitLine: { show: true }
        },
        yAxis: {
            type: 'log',
            name: '参数规模',
            logBase: 10,
            splitLine: { show: true },
            axisLabel: {
                formatter: (value: number) => formatParams(value)
            }
        },
        series: series.map((s, idx) => ({
            ...s,
            symbolSize: (data: any) => {
                const comp = data[2];
                if (!comp) return 10;
                const logComp = Math.log10(comp);
                const minLog = 15;
                const maxLog = 26;
                if (logComp <= minLog) return 10;
                if (logComp >= maxLog) return 40;
                return 10 + ((logComp - minLog) / (maxLog - minLog)) * 30;
            }
        }))
    };
});

// 全球研发格局配置（堆叠柱状图）
const epochGlobalOption = computed(() => {
    const years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
    const countries = ['United States', 'China', 'United Kingdom', 'France', 'Germany', 'Canada', 'Japan', 'Other'];
    const countryNamesZh: Record<string, string> = {
        'United States': '美国',
        'China': '中国',
        'United Kingdom': '英国',
        'France': '法国',
        'Germany': '德国',
        'Canada': '加拿大',
        'Japan': '日本',
        'Other': '其他国家/地区'
    };
    const colors = ['#2d8cf0', '#f25e43', '#64d572', '#e9a745', '#9b59b6', '#00bcd4', '#1abc9c', '#7f8c8d'];

    const series = countries.map((country, idx) => {
        const data = years.map(yr => {
            const yrData = epochStats.value.yearly_countries.find(y => y.year === yr);
            return yrData ? (yrData.countries[country] || 0) : 0;
        });
        return {
            name: countryNamesZh[country],
            type: 'bar',
            stack: 'total',
            itemStyle: { color: colors[idx] },
            emphasis: { focus: 'series' },
            data
        };
    });

    return {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' }
        },
        legend: {
            top: 0
        },
        grid: {
            top: '15%',
            left: '3%',
            right: '3%',
            bottom: '5%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: years.map(y => `${y}年`)
        },
        yAxis: {
            type: 'value',
            name: '发布大模型数量 (个)'
        },
        series
    };
});

// 开源权重比例饼图
const epochWeightsOption = computed(() => {
    const ow = epochStats.value.open_weights;
    return {
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} 个 ({d}%)'
        },
        legend: {
            bottom: '0',
            left: 'center'
        },
        color: ['#64d572', '#f25e43', '#909399'],
        series: [
            {
                name: '权重开放度',
                type: 'pie',
                radius: ['45%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
                label: { show: false },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 14,
                        fontWeight: 'bold'
                    }
                },
                data: [
                    { value: ow.Yes || 0, name: '开源模型 (Open Weights)' },
                    { value: ow.No || 0, name: '闭源/API模型' },
                    { value: ow.Unknown || 0, name: '未公开/未知' }
                ]
            }
        ]
    };
});
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
