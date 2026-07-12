<template>
    <div class="bi-tab">
        <el-alert
            :title="t('pages.insight.bi.hint')"
            type="info"
            show-icon
            :closable="false"
            class="mgb20"
        />

        <div class="toolbar mgb20">
            <el-button type="primary" :loading="building" @click="handleBuild('incremental')">
                {{ t('pages.insight.bi.buildIncremental') }}
            </el-button>
            <el-button :loading="buildingFull" @click="handleBuild('full')">
                {{ t('pages.insight.bi.buildFull') }}
            </el-button>
            <el-button @click="reloadAll">{{ t('common.refresh') }}</el-button>
            <span v-if="buildResult" class="build-result">
                {{ t('pages.insight.bi.buildDone', {
                    date: buildResult.snapshot_date,
                    snapshots: buildResult.snapshots_upserted,
                    regions: buildResult.region_metrics_upserted,
                    ms: buildResult.elapsed_ms,
                }) }}
                <template v-if="buildResult.mode"> · {{ buildResult.mode }}</template>
                <template v-if="buildResult.prev_snapshot_date">
                    · {{ t('pages.insight.bi.prevDayDone', {
                        date: buildResult.prev_snapshot_date,
                        snapshots: buildResult.prev_snapshots_upserted,
                    }) }}
                </template>
            </span>
        </div>

        <el-row :gutter="16" class="summary-row mgb20">
            <el-col :xs="12" :sm="6">
                <el-card shadow="hover" class="summary-card">
                    <el-statistic :title="t('pages.insight.bi.latestSnapshot')" :value="summary.snapshotDate || '—'" />
                </el-card>
            </el-col>
            <el-col :xs="12" :sm="6">
                <el-card shadow="hover" class="summary-card">
                    <el-statistic :title="t('pages.insight.bi.totalCustomersKanto')" :value="summary.totalCustomers" />
                </el-card>
            </el-col>
            <el-col :xs="12" :sm="6">
                <el-card shadow="hover" class="summary-card">
                    <el-statistic
                        :title="t('pages.insight.bi.avgHighRisk')"
                        :value="summary.avgHighRisk * 100"
                        :precision="2"
                        suffix="%"
                    />
                </el-card>
            </el-col>
            <el-col :xs="12" :sm="6">
                <el-card shadow="hover" class="summary-card">
                    <el-statistic :title="t('pages.insight.bi.activeRegions')">
                        <template #default>
                            <span class="metric-value">{{ summary.regionCount }} / {{ summary.cityCount }}</span>
                        </template>
                    </el-statistic>
                </el-card>
            </el-col>
        </el-row>

        <el-row :gutter="16" class="mgb20">
            <el-col :xs="24" :lg="15">
                <el-card shadow="hover" class="map-card">
                    <template #header>
                        <div class="card-header">
                            <span>{{ t('pages.insight.bi.mapTitle') }}</span>
                            <span class="card-desc">{{ t('pages.insight.bi.mapDesc') }}</span>
                        </div>
                    </template>
                    <component
                        :is="VChart"
                        v-if="VChart"
                        class="risk-map"
                        :option="mapOption"
                        autoresize
                        @click="handleMapClick"
                    />
                    <el-empty v-else-if="!mapLoading" :description="t('pages.insight.bi.mapLoading')" />
                </el-card>
            </el-col>
            <el-col :xs="24" :lg="9">
                <el-card shadow="hover" class="detail-card">
                    <template #header>
                        <span>{{ selectedRegion ? selectedRegion.region_l1 : t('pages.insight.bi.selectRegion') }}</span>
                    </template>
                    <template v-if="selectedRegion">
                        <div class="detail-metrics">
                            <div>
                                <div class="metric-label">{{ t('pages.insight.bi.totalCustomers') }}</div>
                                <div class="metric-value">{{ selectedRegion.total_customers }}</div>
                            </div>
                            <div>
                                <div class="metric-label">{{ t('pages.insight.bi.highRiskRatio') }}</div>
                                <div class="metric-value">{{ formatRatio(selectedRegion.high_risk_ratio) }}</div>
                            </div>
                            <div>
                                <div class="metric-label">{{ t('pages.insight.bi.riskMom') }}</div>
                                <div class="metric-value" :class="momClass(selectedRegion.risk_ratio_mom)">
                                    {{ formatMom(selectedRegion.risk_ratio_mom) }}
                                </div>
                            </div>
                        </div>
                        <el-table :data="selectedRegion.cities" size="small" stripe max-height="320">
                            <el-table-column prop="region_l2" :label="t('pages.insight.bi.regionL2')" min-width="120" />
                            <el-table-column prop="total_customers" :label="t('pages.insight.bi.totalCustomers')" width="88" />
                            <el-table-column :label="t('pages.insight.bi.highRiskRatio')" width="96">
                                <template #default="{ row }">{{ formatRatio(row.high_risk_ratio) }}</template>
                            </el-table-column>
                            <el-table-column :label="t('pages.insight.bi.riskMom')" width="88">
                                <template #default="{ row }">
                                    <span :class="momClass(row.risk_ratio_mom)">{{ formatMom(row.risk_ratio_mom) }}</span>
                                </template>
                            </el-table-column>
                        </el-table>
                    </template>
                    <el-empty v-else :description="t('pages.insight.bi.mapEmpty')" />
                </el-card>
            </el-col>
        </el-row>

        <el-table :data="rows" v-loading="loading" border stripe>
            <el-table-column prop="snapshot_date" :label="t('pages.insight.bi.snapshotDate')" width="120" />
            <el-table-column prop="region_l1" :label="t('pages.insight.bi.regionL1')" width="120" />
            <el-table-column prop="region_l2" :label="t('pages.insight.bi.regionL2')" width="140" />
            <el-table-column prop="total_customers" :label="t('pages.insight.bi.totalCustomers')" width="110" />
            <el-table-column :label="t('pages.insight.bi.highRiskRatio')" width="120">
                <template #default="{ row }">{{ formatRatio(row.high_risk_ratio) }}</template>
            </el-table-column>
            <el-table-column :label="t('pages.insight.bi.riskMom')" width="120">
                <template #default="{ row }">
                    <span :class="momClass(row.risk_ratio_mom)">{{ formatMom(row.risk_ratio_mom) }}</span>
                </template>
            </el-table-column>
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
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, shallowRef, type Component } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { getInsightJobLogs, getInsightRegionMetrics, postInsightBuildSnapshot } from '@/api';
import {
    aggregateByL1,
    buildRegionMapOption,
    buildSummary,
    pickLatestRows,
    type GeoFeatureCollection,
    type L1Aggregate,
    type RegionMetricRow,
} from '../chart/region-map';

interface BuildResult {
    snapshot_date: string;
    snapshots_upserted: number;
    region_metrics_upserted: number;
    elapsed_ms: number;
    mode?: 'incremental' | 'full';
    prev_snapshot_date?: string;
    prev_snapshots_upserted?: number;
    prev_region_metrics_upserted?: number;
}

const { t } = useI18n();
const VChart = shallowRef<Component | null>(null);
const echartsCore = shallowRef<typeof import('echarts/core') | null>(null);
const fullGeo = shallowRef<GeoFeatureCollection | null>(null);
const mapRows = ref<RegionMetricRow[]>([]);
const rows = ref<RegionMetricRow[]>([]);
const loading = ref(false);
const mapLoading = ref(false);
const building = ref(false);
const buildingFull = ref(false);
const buildResult = ref<BuildResult | null>(null);
const selectedL1 = ref<string | null>(null);
const page = reactive({ index: 1, size: 20, total: 0 });

const aggregates = computed(() => aggregateByL1(mapRows.value));
const summary = computed(() => {
    const latestRows = pickLatestRows(mapRows.value);
    const snapshotDate = latestRows[0]?.snapshot_date ?? null;
    return buildSummary(aggregates.value, snapshotDate);
});
const selectedRegion = computed<L1Aggregate | null>(() => {
    const found = aggregates.value.find((item) => item.region_l1 === selectedL1.value);
    if (found) return found;
    if (!selectedL1.value) return null;
    return {
        region_l1: selectedL1.value,
        total_customers: 0,
        high_risk_ratio: 0,
        risk_ratio_mom: 0,
        cities: [],
    };
});
const mapOption = computed(() =>
    buildRegionMapOption(aggregates.value, {
        highRisk: t('pages.insight.bi.mapHigh'),
        lowRisk: t('pages.insight.bi.mapLow'),
        customers: t('pages.insight.bi.totalCustomers'),
        mom: t('pages.insight.bi.riskMom'),
        noData: t('pages.insight.bi.mapNoData'),
    }, selectedL1.value),
);

function formatRatio(value: number) {
    return `${(Number(value) * 100).toFixed(2)}%`;
}

function formatMom(value: number) {
    const pct = Number(value) * 100;
    return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
}

function momClass(value: number) {
    const num = Number(value);
    if (num > 0) return 'mom-up';
    if (num < 0) return 'mom-down';
    return '';
}

function syncRegisteredMap() {
    if (!echartsCore.value || !fullGeo.value) return;
    // 始终注册关东及周边全量轮廓；无数据区域保持灰色底图
    echartsCore.value.registerMap(
        'insight-kanto',
        fullGeo.value as Parameters<typeof echartsCore.value.registerMap>[1],
    );
}

async function ensureMapChart() {
    if (VChart.value) return;
    const [core, charts, components, renderers, vueEcharts, geoJson] = await Promise.all([
        import('echarts/core'),
        import('echarts/charts'),
        import('echarts/components'),
        import('echarts/renderers'),
        import('vue-echarts'),
        import('../chart/kanto-geo.json'),
    ]);
    core.use([
        renderers.CanvasRenderer,
        charts.MapChart,
        components.TooltipComponent,
        components.VisualMapComponent,
        components.GeoComponent,
    ]);
    const mapData = ((geoJson as { default?: GeoFeatureCollection }).default ?? geoJson) as GeoFeatureCollection;
    echartsCore.value = core;
    fullGeo.value = mapData;
    syncRegisteredMap();
    VChart.value = vueEcharts.default;
}

async function loadMapMetrics() {
    mapLoading.value = true;
    try {
        const { data } = await getInsightRegionMetrics({ page: 1, page_size: 200 });
        mapRows.value = data.list;
        syncRegisteredMap();
        const active = aggregateByL1(mapRows.value);
        if (!selectedL1.value || !active.some((item) => item.region_l1 === selectedL1.value)) {
            selectedL1.value = active[0]?.region_l1 ?? null;
        }
    } finally {
        mapLoading.value = false;
    }
}

async function loadTableMetrics() {
    loading.value = true;
    try {
        const { data } = await getInsightRegionMetrics({ page: page.index, page_size: page.size });
        rows.value = data.list;
        page.total = data.pageTotal;
    } finally {
        loading.value = false;
    }
}

async function reloadAll() {
    await Promise.all([loadMapMetrics(), loadTableMetrics()]);
}

async function handleBuild(mode: 'incremental' | 'full' = 'incremental') {
    const loadingRef = mode === 'full' ? buildingFull : building;
    loadingRef.value = true;
    try {
        const { data } = await postInsightBuildSnapshot(undefined, false, mode);
        ElMessage.info(data.message || t('pages.insight.bi.buildAccepted'));
        const started = Date.now();
        let done = false;
        while (Date.now() - started < 600_000) {
            const { data: logs } = await getInsightJobLogs({ page: 1, page_size: 20 });
            const row = logs.list.find((item: { id: number; status: string }) => item.id === data.analysis_log_id);
            if (row && row.status !== 'running') {
                done = row.status === 'completed';
                if (!done) {
                    ElMessage.error(row.answer || t('pages.insight.bi.buildFailed'));
                }
                break;
            }
            await new Promise((r) => setTimeout(r, 2000));
        }
        if (!done && Date.now() - started >= 600_000) {
            ElMessage.error(t('pages.insight.bi.buildTimeout'));
            return;
        }
        if (done) {
            buildResult.value = {
                snapshot_date: data.snapshot_date,
                snapshots_upserted: 0,
                region_metrics_upserted: 0,
                elapsed_ms: 0,
                mode: data.mode,
            };
            selectedL1.value = null;
            ElMessage.success(t('pages.insight.bi.buildSuccess'));
            page.index = 1;
            await reloadAll();
        }
    } catch (error: unknown) {
        const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        ElMessage.error(detail || t('pages.insight.bi.buildFailed'));
    } finally {
        loadingRef.value = false;
    }
}

function changePage(val: number) {
    page.index = val;
    loadTableMetrics();
}

function handleMapClick(params: { name?: string }) {
    if (!params.name) return;
    selectedL1.value = params.name;
}

onMounted(async () => {
    await ensureMapChart();
    await reloadAll();
});
</script>

<style scoped>
.toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}
.build-result {
    color: var(--el-text-color-secondary);
    font-size: 13px;
}
.summary-row .summary-card {
    margin-bottom: 12px;
}
.card-header {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.card-desc {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    font-weight: normal;
}
.risk-map {
    width: 100%;
    height: 420px;
}
.detail-card {
    min-height: 500px;
}
.detail-metrics {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 16px;
}
.metric-label {
    font-size: 12px;
    color: var(--el-text-color-secondary);
}
.metric-value {
    margin-top: 4px;
    font-size: 20px;
    font-weight: 600;
}
.pager {
    justify-content: flex-end;
    margin-top: 16px;
}
.mom-up {
    color: var(--el-color-danger);
}
.mom-down {
    color: var(--el-color-success);
}
</style>
