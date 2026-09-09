<template>
    <div class="epoch-board" v-loading="loading">
        <div class="epoch-header">
            <div>
                <p class="card-header-title">
                    <el-icon class="title-icon"><Histogram /></el-icon>
                    {{ t('pages.aiNews.epoch.title') }}
                </p>
                <p class="card-header-desc">
                    {{
                        t('pages.aiNews.epoch.desc', {
                            time: epochStats.updated_at || t('pages.aiNews.epoch.loading'),
                        })
                    }}
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
                <span>{{ t('pages.aiNews.epoch.countAll') }}: <strong class="c-blue">{{ epochStats.counts.all_models }}</strong></span>
                <span>{{ t('pages.aiNews.epoch.countNotable') }}: <strong class="c-gold">{{ epochStats.counts.notable_models }}</strong></span>
                <span>{{ t('pages.aiNews.epoch.countFrontier') }}: <strong class="c-red">{{ epochStats.counts.frontier_models }}</strong></span>
                <span>{{ t('pages.aiNews.epoch.countLarge') }}: <strong class="c-green">{{ epochStats.counts.large_scale_models }}</strong></span>
            </div>
        </div>

        <el-tabs v-model="activeEpochTab" type="border-card" class="epoch-tabs">
            <el-tab-pane :label="t('pages.aiNews.epoch.tabEvolution')" name="evolution">
                <div class="pane-pad">
                    <p class="pane-desc">
                        <strong>{{ t('pages.aiNews.epoch.chartNote') }}</strong>{{ t('pages.aiNews.epoch.evolutionDesc') }}
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

            <el-tab-pane :label="t('pages.aiNews.epoch.tabGlobal')" name="global">
                <el-row :gutter="20">
                    <el-col :span="16">
                        <div class="pane-pad">
                            <p class="pane-desc">
                                <strong>{{ t('pages.aiNews.epoch.globalTitle') }}</strong>{{ t('pages.aiNews.epoch.globalDesc') }}
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
                                <strong>{{ t('pages.aiNews.epoch.weightsTitle') }}</strong>
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

            <el-tab-pane :label="t('pages.aiNews.epoch.tabReleases')" name="releases">
                <div class="pane-pad">
                    <p class="pane-desc">
                        <strong>{{ t('pages.aiNews.epoch.releasesTitle') }}</strong>{{ t('pages.aiNews.epoch.releasesDesc') }}
                    </p>
                    <el-table :data="epochStats.latest_releases" style="width: 100%" size="default" border stripe>
                        <el-table-column prop="name" :label="t('pages.aiNews.epoch.colName')" min-width="150" show-overflow-tooltip>
                            <template #default="scope">
                                <span class="model-name">{{ scope.row.name }}</span>
                            </template>
                        </el-table-column>
                        <el-table-column prop="org" :label="t('pages.aiNews.epoch.colOrg')" min-width="150" show-overflow-tooltip />
                        <el-table-column prop="date" :label="t('pages.aiNews.epoch.colDate')" width="130" sortable />
                        <el-table-column prop="domain" :label="t('pages.aiNews.epoch.colDomain')" width="140" />
                        <el-table-column prop="parameters" :label="t('pages.aiNews.epoch.colParams')" width="150" show-overflow-tooltip>
                            <template #default="scope">
                                <span>{{ formatParams(parseFloat(scope.row.parameters)) || scope.row.parameters }}</span>
                            </template>
                        </el-table-column>
                        <el-table-column prop="accessibility" :label="t('pages.aiNews.epoch.colAccess')" min-width="150" show-overflow-tooltip />
                    </el-table>
                </div>
            </el-tab-pane>

            <el-tab-pane :label="t('pages.aiNews.epoch.tabCareer')" name="career-ai" lazy>
                <div class="pane-pad insight-image-wrap">
                    <el-image
                        src="/epoch-ai-insight.jpg"
                        :preview-src-list="['/epoch-ai-insight.jpg']"
                        fit="contain"
                        class="insight-image"
                    />
                </div>
            </el-tab-pane>
        </el-tabs>
    </div>
</template>

<script setup lang="ts" name="epoch-ai-board">
import { computed, onMounted, shallowRef, ref, type Component } from 'vue';
import { useI18n } from 'vue-i18n';
import { Histogram } from '@element-plus/icons-vue';
import { fetchEpochStats } from '@/api';

const { t, locale } = useI18n();
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
    if (!p) return t('pages.aiNews.epoch.unknown');
    if (p >= 1e12) return t('pages.aiNews.epoch.paramsT', { n: (p / 1e12).toFixed(1) });
    if (p >= 1e9) return t('pages.aiNews.epoch.paramsB', { n: (p / 1e9).toFixed(1) });
    if (p >= 1e6) return t('pages.aiNews.epoch.paramsM', { n: (p / 1e6).toFixed(1) });
    return p.toLocaleString();
}

function formatCompute(c: number | null | undefined): string {
    if (!c) return t('pages.aiNews.epoch.unknown');
    if (c >= 1e26) return `${(c / 1e26).toFixed(1)} YottaFLOPs`;
    if (c >= 1e23) return `${(c / 1e23).toFixed(1)} ZettaFLOPs (10^23)`;
    if (c >= 1e20) return `${(c / 1e20).toFixed(1)} ExaFLOPs (10^20)`;
    if (c >= 1e15) return `${(c / 1e15).toFixed(1)} PetaFLOPs`;
    return `${c.toExponential(2)} FLOPs`;
}

const epochScatterOption = computed(() => {
    void locale.value;
    const domains = ['Language', 'Vision', 'Multimodal', 'Speech/Audio', 'Robotics', 'Other'];
    const domainNames: Record<string, string> = {
        Language: t('pages.aiNews.epoch.domainLanguage'),
        Vision: t('pages.aiNews.epoch.domainVision'),
        Multimodal: t('pages.aiNews.epoch.domainMultimodal'),
        'Speech/Audio': t('pages.aiNews.epoch.domainSpeech'),
        Robotics: t('pages.aiNews.epoch.domainRobotics'),
        Other: t('pages.aiNews.epoch.domainOther'),
    };
    const colors = ['#2d8cf0', '#9b59b6', '#f25e43', '#e9a745', '#00bcd4', '#7f8c8d'];

    const series = domains.map((dom, idx) => {
        const filtered = epochStats.value.scatter_data.filter((d) => d.domain === dom && d.params);
        return {
            name: domainNames[dom],
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
                    ? `<span style="color:#f25e43;font-weight:bold;margin-left:5px;">${t('pages.aiNews.epoch.frontier')}</span>`
                    : '';
                return `<div style="padding: 5px; font-family: sans-serif; line-height: 1.6;">
                    <div style="font-size: 14px; font-weight: bold; color: #2d8cf0; margin-bottom: 5px;">${item[3]}${isFront}</div>
                    <span style="color: #999;">${t('pages.aiNews.epoch.org')}:</span> ${item[4]}<br/>
                    <span style="color: #999;">${t('pages.aiNews.epoch.publishDate')}:</span> ${item[0]}<br/>
                    <span style="color: #999;">${t('pages.aiNews.epoch.techDomain')}:</span> ${domainNames[item[5]] || item[5]}<br/>
                    <span style="color: #999;">${t('pages.aiNews.epoch.paramScale')}:</span> ${formatParams(item[1])}<br/>
                    <span style="color: #999;">${t('pages.aiNews.epoch.trainCompute')}:</span> ${formatCompute(item[2])}
                </div>`;
            },
        },
        legend: { type: 'scroll', top: 0 },
        grid: { top: '15%', left: '3%', right: '4%', bottom: '5%', containLabel: true },
        xAxis: { type: 'time', name: t('pages.aiNews.epoch.xPublishTime'), splitLine: { show: true } },
        yAxis: {
            type: 'log',
            name: t('pages.aiNews.epoch.yParamScale'),
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
    void locale.value;
    const years = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];
    const countries = ['United States', 'China', 'United Kingdom', 'France', 'Germany', 'Canada', 'Japan', 'Other'];
    const countryNames: Record<string, string> = {
        'United States': t('pages.aiNews.epoch.countryUS'),
        China: t('pages.aiNews.epoch.countryCN'),
        'United Kingdom': t('pages.aiNews.epoch.countryUK'),
        France: t('pages.aiNews.epoch.countryFR'),
        Germany: t('pages.aiNews.epoch.countryDE'),
        Canada: t('pages.aiNews.epoch.countryCA'),
        Japan: t('pages.aiNews.epoch.countryJP'),
        Other: t('pages.aiNews.epoch.countryOther'),
    };
    const colors = ['#2d8cf0', '#f25e43', '#64d572', '#e9a745', '#9b59b6', '#00bcd4', '#1abc9c', '#7f8c8d'];

    const series = countries.map((country, idx) => ({
        name: countryNames[country],
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
        xAxis: { type: 'category', data: years.map((y) => t('pages.aiNews.epoch.yearLabel', { y })) },
        yAxis: { type: 'value', name: t('pages.aiNews.epoch.yModelCount') },
        series,
    };
});

const epochWeightsOption = computed(() => {
    void locale.value;
    const ow = epochStats.value.open_weights;
    return {
        tooltip: {
            trigger: 'item',
            formatter: (p: { name: string; value: number; percent: number }) =>
                t('pages.aiNews.epoch.pieTooltip', { name: p.name, count: p.value, percent: p.percent }),
        },
        legend: { bottom: '0', left: 'center' },
        color: ['#64d572', '#f25e43', '#909399'],
        series: [
            {
                name: t('pages.aiNews.epoch.weightsSeries'),
                type: 'pie',
                radius: ['45%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
                label: { show: false },
                emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
                data: [
                    { value: ow.Yes || 0, name: t('pages.aiNews.epoch.openWeights') },
                    { value: ow.No || 0, name: t('pages.aiNews.epoch.closedWeights') },
                    { value: ow.Unknown || 0, name: t('pages.aiNews.epoch.unknownWeights') },
                ],
            },
        ],
    };
});

function sleep(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function todayIso(): string {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

function isReady(data: { status?: string } | null | undefined): boolean {
    return data?.status === 'success';
}

function isFresh(data: { updated_date?: string } | null | undefined): boolean {
    return Boolean(data?.updated_date && data.updated_date === todayIso());
}

async function fetchOnce() {
    const { data } = await fetchEpochStats();
    epochStats.value = data;
    return data;
}

/** 无种子时阻塞轮询；已有数据则后台刷新到当日 */
async function loadEpochStats() {
    const data = await fetchOnce();
    if (isReady(data) && isFresh(data)) {
        return;
    }
    if (!isReady(data)) {
        for (let i = 0; i < 7; i++) {
            await sleep(2000);
            const next = await fetchOnce();
            if (isReady(next)) {
                return;
            }
        }
        return;
    }
    // 有种子但非当日：不阻塞 UI，后台再拉几次
    void (async () => {
        for (let i = 0; i < 6; i++) {
            await sleep(3000);
            const next = await fetchOnce();
            if (isFresh(next)) {
                return;
            }
        }
    })();
}

onMounted(async () => {
    loading.value = true;
    try {
        await ensureCharts();
        await loadEpochStats();
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

.insight-image-wrap {
    text-align: center;
}

.insight-image {
    width: 100%;
    max-width: 1024px;
}
</style>
