<template>
    <div class="epoch-board" v-loading="loading">
        <div class="epoch-header">
            <div>
                <p class="card-header-title">
                    <el-icon class="title-icon"><Histogram /></el-icon>
                    Epoch AI 全球大模型多维洞察看板
                </p>
                <p class="card-header-desc">
                    每日自动同步官方全量模型库，追踪 AI 算力与参数膨胀前沿规律（更新时间：{{
                        epochStats.updated_at || '加载中...'
                    }}）
                </p>
                <p class="quick-links">
                    <el-link
                        type="primary"
                        href="https://huggingface.co/papers/trending"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        Hugging Face Trending Papers
                    </el-link>
                </p>
            </div>
            <div class="epoch-counts">
                <span>模型总数: <strong class="c-blue">{{ epochStats.counts.all_models }}</strong></span>
                <span>显著里程碑: <strong class="c-gold">{{ epochStats.counts.notable_models }}</strong></span>
                <span>前沿标杆: <strong class="c-red">{{ epochStats.counts.frontier_models }}</strong></span>
                <span>超大规模: <strong class="c-green">{{ epochStats.counts.large_scale_models }}</strong></span>
            </div>
        </div>

        <el-tabs v-model="activeEpochTab" type="border-card" class="epoch-tabs">
            <el-tab-pane label="模型参数与算力演进（对数气泡图）" name="evolution">
                <div class="pane-pad">
                    <p class="pane-desc">
                        <strong>图表说明：</strong> X 轴为大模型发布时间，Y 轴为<strong>参数规模 (对数 Log10 刻度)</strong>。
                        气泡的大小代表<strong>训练算力 (Training FLOPs)</strong>，气泡越大表示训练该模型消耗的物理算力越恐怖。
                        可在上方图例点击筛选不同的技术领域。
                    </p>
                    <component
                        :is="VChart"
                        v-if="VChart"
                        class="chart"
                        :option="epochScatterOption"
                        autoresize
                        style="height: 450px"
                    />
                </div>
            </el-tab-pane>

            <el-tab-pane label="全球研发格局与开源比例分布" name="global">
                <el-row :gutter="20">
                    <el-col :span="16">
                        <div class="pane-pad">
                            <p class="pane-desc">
                                <strong>全球大模型年度发布趋势 (按国家/地区堆叠)</strong>：展示 2018-2026
                                年间，全球各大经济体发布主流大模型的数量分布演变。
                            </p>
                            <component
                                :is="VChart"
                                v-if="VChart"
                                class="chart"
                                :option="epochGlobalOption"
                                autoresize
                                style="height: 380px"
                            />
                        </div>
                    </el-col>
                    <el-col :span="8" class="weights-col">
                        <div class="pane-pad">
                            <p class="pane-desc pane-desc--center">
                                <strong>大模型权重开放度 (开源 vs 闭源比例)</strong>
                            </p>
                            <component
                                :is="VChart"
                                v-if="VChart"
                                class="chart"
                                :option="epochWeightsOption"
                                autoresize
                                style="height: 380px"
                            />
                        </div>
                    </el-col>
                </el-row>
            </el-tab-pane>

            <el-tab-pane label="全量最新收录大模型库" name="releases">
                <div class="pane-pad">
                    <p class="pane-desc">
                        <strong>最近发布的 15 个代表性大模型一览表</strong
                        >（数据自动同步自 Epoch AI 官方数据库，按发布日期降序排列）：
                    </p>
                    <el-table :data="epochStats.latest_releases" style="width: 100%" size="default" border stripe>
                        <el-table-column prop="name" label="模型名称 (Model)" min-width="150" show-overflow-tooltip>
                            <template #default="scope">
                                <span class="model-name">{{ scope.row.name }}</span>
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
    </div>
</template>

<script setup lang="ts" name="epoch-ai-board">
import { computed, onMounted, shallowRef, ref, type Component } from 'vue';
import { Histogram } from '@element-plus/icons-vue';
import { fetchEpochStats } from '@/api';

const VChart = shallowRef<Component | null>(null);
const loading = ref(false);
const activeEpochTab = ref('evolution');

const epochStats = ref({
    status: 'initializing',
    updated_at: '',
    counts: {
        all_models: 0,
        notable_models: 0,
        frontier_models: 0,
        large_scale_models: 0,
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
    }>,
});

async function ensureCharts() {
    if (VChart.value) return;
    const [core, charts, components, renderers, vueEcharts] = await Promise.all([
        import('echarts/core'),
        import('echarts/charts'),
        import('echarts/components'),
        import('echarts/renderers'),
        import('vue-echarts'),
    ]);
    core.use([
        renderers.CanvasRenderer,
        charts.BarChart,
        charts.PieChart,
        charts.ScatterChart,
        components.GridComponent,
        components.TooltipComponent,
        components.LegendComponent,
    ]);
    VChart.value = vueEcharts.default;
}

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

const epochScatterOption = computed(() => {
    const domains = ['Language', 'Vision', 'Multimodal', 'Speech/Audio', 'Robotics', 'Other'];
    const domainNamesZh: Record<string, string> = {
        Language: '语言模型 (Language)',
        Vision: '计算机视觉 (Vision)',
        Multimodal: '多模态 (Multimodal)',
        'Speech/Audio': '语音与音频 (Speech/Audio)',
        Robotics: '机器人 (Robotics)',
        Other: '其他领域 (Other)',
    };
    const colors = ['#2d8cf0', '#9b59b6', '#f25e43', '#e9a745', '#00bcd4', '#7f8c8d'];

    const series = domains.map((dom, idx) => {
        const filtered = epochStats.value.scatter_data.filter((d) => d.domain === dom && d.params);
        return {
            name: domainNamesZh[dom],
            type: 'scatter',
            itemStyle: { color: colors[idx] },
            data: filtered.map((d) => [d.date, d.params, d.compute, d.name, d.org, d.domain, d.is_frontier]),
            emphasis: { focus: 'series' },
        };
    });

    return {
        tooltip: {
            trigger: 'item',
            formatter: (params: any) => {
                const item = params.value;
                if (!item) return '';
                const isFront = item[6]
                    ? '<span style="color:#f25e43;font-weight:bold;margin-left:5px;">★ 前沿</span>'
                    : '';
                return `<div style="padding: 5px; font-family: sans-serif; line-height: 1.6;">
                    <div style="font-size: 14px; font-weight: bold; color: #2d8cf0; margin-bottom: 5px;">${item[3]}${isFront}</div>
                    <span style="color: #999;">研发机构:</span> ${item[4]}<br/>
                    <span style="color: #999;">发布日期:</span> ${item[0]}<br/>
                    <span style="color: #999;">技术领域:</span> ${domainNamesZh[item[5]] || item[5]}<br/>
                    <span style="color: #999;">参数规模:</span> ${formatParams(item[1])}<br/>
                    <span style="color: #999;">训练算力:</span> ${formatCompute(item[2])}
                </div>`;
            },
        },
        legend: { type: 'scroll', top: 0 },
        grid: { top: '15%', left: '3%', right: '4%', bottom: '5%', containLabel: true },
        xAxis: { type: 'time', name: '发布时间', splitLine: { show: true } },
        yAxis: {
            type: 'log',
            name: '参数规模',
            logBase: 10,
            splitLine: { show: true },
            axisLabel: { formatter: (value: number) => formatParams(value) },
        },
        series: series.map((s) => ({
            ...s,
            symbolSize: (data: any) => {
                const comp = data[2];
                if (!comp) return 10;
                const logComp = Math.log10(comp);
                if (logComp <= 15) return 10;
                if (logComp >= 26) return 40;
                return 10 + ((logComp - 15) / 11) * 30;
            },
        })),
    };
});

const epochGlobalOption = computed(() => {
    const years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
    const countries = ['United States', 'China', 'United Kingdom', 'France', 'Germany', 'Canada', 'Japan', 'Other'];
    const countryNamesZh: Record<string, string> = {
        'United States': '美国',
        China: '中国',
        'United Kingdom': '英国',
        France: '法国',
        Germany: '德国',
        Canada: '加拿大',
        Japan: '日本',
        Other: '其他国家/地区',
    };
    const colors = ['#2d8cf0', '#f25e43', '#64d572', '#e9a745', '#9b59b6', '#00bcd4', '#1abc9c', '#7f8c8d'];

    const series = countries.map((country, idx) => ({
        name: countryNamesZh[country],
        type: 'bar',
        stack: 'total',
        itemStyle: { color: colors[idx] },
        emphasis: { focus: 'series' },
        data: years.map((yr) => {
            const yrData = epochStats.value.yearly_countries.find((y) => y.year === yr);
            return yrData ? yrData.countries[country] || 0 : 0;
        }),
    }));

    return {
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        legend: { top: 0 },
        grid: { top: '15%', left: '3%', right: '3%', bottom: '5%', containLabel: true },
        xAxis: { type: 'category', data: years.map((y) => `${y}年`) },
        yAxis: { type: 'value', name: '发布大模型数量 (个)' },
        series,
    };
});

const epochWeightsOption = computed(() => {
    const ow = epochStats.value.open_weights;
    return {
        tooltip: { trigger: 'item', formatter: '{b}: {c} 个 ({d}%)' },
        legend: { bottom: '0', left: 'center' },
        color: ['#64d572', '#f25e43', '#909399'],
        series: [
            {
                name: '权重开放度',
                type: 'pie',
                radius: ['45%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
                label: { show: false },
                emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
                data: [
                    { value: ow.Yes || 0, name: '开源模型 (Open Weights)' },
                    { value: ow.No || 0, name: '闭源/API模型' },
                    { value: ow.Unknown || 0, name: '未公开/未知' },
                ],
            },
        ],
    };
});

onMounted(async () => {
    loading.value = true;
    try {
        await ensureCharts();
        const { data } = await fetchEpochStats();
        epochStats.value = data;
    } catch (err) {
        console.error('加载 Epoch AI 数据失败', err);
    } finally {
        loading.value = false;
    }
});
</script>

<style scoped>
.epoch-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
    gap: 16px;
    flex-wrap: wrap;
}

.card-header-title {
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 5px;
}

.title-icon {
    vertical-align: middle;
    margin-right: 8px;
}

.card-header-desc {
    font-size: 14px;
    color: #999;
}

.quick-links {
    margin-top: 8px;
    font-size: 13px;
}

.epoch-counts {
    font-size: 14px;
    color: #666;
    display: flex;
    gap: 15px;
    flex-wrap: wrap;
    background: #f5f7fa;
    padding: 10px 15px;
    border-radius: 8px;
}

.epoch-counts strong {
    font-size: 16px;
}

.c-blue {
    color: #2d8cf0;
}
.c-gold {
    color: #e9a745;
}
.c-red {
    color: #f25e43;
}
.c-green {
    color: #64d572;
}

.epoch-tabs {
    border-radius: 6px;
}

.pane-pad {
    padding: 10px 0;
}

.pane-desc {
    font-size: 13px;
    color: #7f8c8d;
    margin-bottom: 15px;
    line-height: 1.5;
}

.pane-desc--center {
    text-align: center;
}

.weights-col {
    border-left: 1px solid #f0f0f0;
}

.model-name {
    font-weight: bold;
    color: #2d8cf0;
}

.chart {
    width: 100%;
}
</style>
