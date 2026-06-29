<template>
    <div class="container complaints-page">
        <el-card class="mgb20 samples-card" shadow="hover" v-loading="samplesLoading">
            <template #header>
                <div class="stats-header">
                    <div>
                        <div class="content-title-row">
                            <span class="content-title">{{ t('pages.complaints.samplesTitle') }}</span>
                            <FeatureIntroIcon
                                page-key="complaints"
                                section-key="samples"
                                :intros="intros"
                                :title="t('pages.complaints.samplesTitle')"
                                @saved="setIntro"
                            />
                        </div>
                    </div>
                </div>
            </template>

            <el-form :inline="true" class="samples-form" @submit.prevent="searchSamples">
                <el-form-item :label="t('pages.complaints.region')">
                    <el-input v-model="sampleQuery.address" :placeholder="t('pages.complaints.regionPh')" clearable style="width: 160px" />
                </el-form-item>
                <el-form-item :label="t('pages.complaints.complaintTime')">
                    <el-date-picker
                        v-model="sampleQuery.dateRange"
                        type="daterange"
                        :range-separator="t('pages.complaints.dateSep')"
                        :start-placeholder="t('pages.complaints.dateStart')"
                        :end-placeholder="t('pages.complaints.dateEnd')"
                        value-format="YYYY-MM-DD"
                        style="width: 260px"
                    />
                </el-form-item>
                <el-form-item :label="t('pages.complaints.body')">
                    <el-input v-model="sampleQuery.text" :placeholder="t('pages.complaints.bodyPh')" clearable style="width: 220px" />
                </el-form-item>
                <el-form-item :label="t('pages.complaints.category')">
                    <el-input v-model="sampleQuery.category_name" :placeholder="t('pages.complaints.optional')" clearable style="width: 140px" />
                </el-form-item>
            </el-form>

            <div class="samples-toolbar">
                <el-button type="success" @click="openCreateDialog">{{ t('pages.complaints.createBtn') }}</el-button>
                <el-button type="primary" :loading="samplesLoading" @click="searchSamples">{{ t('common.query') }}</el-button>
            </div>

            <el-table :data="sampleRows" stripe size="small" :empty-text="t('pages.complaints.tableEmpty')">
                <el-table-column prop="id" label="ID" width="70" />
                <el-table-column prop="address" :label="t('pages.complaints.colRegion')" width="100" show-overflow-tooltip />
                <el-table-column :label="t('pages.complaints.colTime')" width="170">
                    <template #default="{ row }">
                        {{ formatComplaintTime(row.complaint_time) }}
                    </template>
                </el-table-column>
                <el-table-column prop="category_name" :label="t('pages.complaints.colCategory')" width="120" show-overflow-tooltip />
                <el-table-column prop="complaint_text" :label="t('pages.complaints.colContent')" min-width="260" show-overflow-tooltip />
                <el-table-column :label="t('pages.complaints.colSimilarity')" width="90" align="right">
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

        <el-dialog v-model="createVisible" :title="t('pages.complaints.createTitle')" width="640px" destroy-on-close @closed="resetCreateForm">
            <el-form label-width="88px" @submit.prevent="submitComplaint">
                <el-form-item :label="t('pages.complaints.body')" required>
                    <el-input
                        v-model="createForm.complaint_text"
                        type="textarea"
                        :rows="4"
                        :placeholder="t('pages.complaints.createTextPh')"
                        maxlength="2000"
                        show-word-limit
                    />
                </el-form-item>
                <el-form-item :label="t('pages.complaints.region')">
                    <el-input v-model="createForm.address" :placeholder="t('pages.complaints.createRegionPh')" clearable />
                </el-form-item>
                <el-form-item :label="t('pages.complaints.complaintTime')">
                    <el-date-picker
                        v-model="createForm.complaint_time"
                        type="datetime"
                        value-format="YYYY-MM-DDTHH:mm:ss"
                        :placeholder="t('pages.complaints.createTimePh')"
                        style="width: 100%"
                    />
                </el-form-item>
            </el-form>

            <div v-if="createResult" class="create-result">
                <el-alert
                    :title="t('pages.complaints.createSuccess')"
                    type="success"
                    :closable="false"
                    show-icon
                    class="create-alert"
                >
                    <template #default>
                        <div>
                            {{ t('pages.complaints.createAssigned') }}：
                            <strong>{{ createResult.assigned_category_name || '—' }}</strong>
                            <el-tag v-if="createResult.category_created" size="small" type="warning" class="create-tag">
                                {{ t('pages.complaints.createNewCategory') }}
                            </el-tag>
                        </div>
                        <div v-if="createResult.similarity != null">
                            {{ t('pages.complaints.createSimilarity') }}：{{ createResult.similarity.toFixed(4) }}
                        </div>
                    </template>
                </el-alert>

                <div v-if="createResult.category_scores.length" class="create-chart-wrap">
                    <div class="section-title">{{ t('pages.complaints.createScoreTitle') }}</div>
                    <component
                        :is="VChart"
                        v-if="VChart"
                        class="create-score-chart"
                        :option="createScoreOption"
                        autoresize
                    />
                </div>
            </div>

            <template #footer>
                <el-button @click="createVisible = false">{{ t('common.cancel') }}</el-button>
                <el-button type="primary" :loading="createLoading" @click="submitComplaint">
                    {{ t('pages.complaints.createSubmit') }}
                </el-button>
            </template>
        </el-dialog>

        <el-dialog v-model="categoriesVisible" :title="t('pages.complaints.categoriesTitle')" width="860px" destroy-on-close @open="loadCategories">
            <el-form :inline="true" class="categories-form" @submit.prevent="searchCategories">
                <el-form-item :label="t('pages.complaints.category')">
                    <el-input
                        v-model="categoryQuery.name"
                        :placeholder="t('pages.complaints.categoriesNamePh')"
                        clearable
                        style="width: 220px"
                        @keyup.enter="searchCategories"
                    />
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" :loading="categoriesLoading" @click="searchCategories">{{ t('common.query') }}</el-button>
                </el-form-item>
            </el-form>

            <el-table :data="categoryRows" stripe size="small" v-loading="categoriesLoading" :empty-text="t('pages.complaints.tableEmpty')">
                <el-table-column type="expand">
                    <template #default="{ row }">
                        <div class="category-expand">
                            <div class="category-expand-title">{{ t('pages.complaints.seedPhrasesTitle') }}</div>
                            <el-tag v-for="(phrase, index) in row.seed_phrases" :key="index" size="small" class="seed-tag">
                                {{ phrase }}
                            </el-tag>
                            <span v-if="!row.seed_phrases.length">—</span>
                        </div>
                    </template>
                </el-table-column>
                <el-table-column prop="id" label="ID" width="60" />
                <el-table-column prop="name" :label="t('pages.complaints.colType')" min-width="130" show-overflow-tooltip />
                <el-table-column prop="description" :label="t('pages.complaints.colDescription')" min-width="180" show-overflow-tooltip />
                <el-table-column :label="t('pages.complaints.colSeedCount')" width="88" align="right">
                    <template #default="{ row }">{{ row.seed_phrases.length }}</template>
                </el-table-column>
                <el-table-column prop="complaint_count" :label="t('pages.complaints.colComplaintCount')" width="80" align="right" />
                <el-table-column :label="t('pages.complaints.colHasEmbedding')" width="88" align="center">
                    <template #default="{ row }">
                        <el-tag :type="row.has_embedding ? 'success' : 'info'" size="small">
                            {{ row.has_embedding ? t('pages.complaints.yes') : t('pages.complaints.no') }}
                        </el-tag>
                    </template>
                </el-table-column>
                <el-table-column :label="t('pages.complaints.colAction')" width="100" fixed="right">
                    <template #default="{ row }">
                        <el-button type="primary" link size="small" @click="viewCategorySamples(row.name)">
                            {{ t('pages.complaints.viewSamples') }}
                        </el-button>
                    </template>
                </el-table-column>
            </el-table>
        </el-dialog>

        <el-card class="mgb20 stats-card" shadow="hover" v-loading="loading">
            <template #header>
                <div class="stats-header">
                    <div>
                        <div class="content-title">{{ t('pages.complaints.statsTitle') }}</div>
                    </div>
                    <div class="stats-header-actions">
                        <div class="threshold-setting">
                            <span class="threshold-label">{{ t('pages.complaints.classifyThreshold') }}</span>
                            <el-input-number
                                v-model="classifyThreshold"
                                :min="0"
                                :max="1"
                                :step="0.01"
                                :precision="2"
                                size="small"
                                :disabled="thresholdSaving"
                                controls-position="right"
                                @change="onThresholdChange"
                            />
                        </div>
                        <el-button type="primary" :loading="loading" @click="loadStats">{{ t('pages.complaints.refreshStats') }}</el-button>
                    </div>
                </div>
                <div class="threshold-hint">{{ t('pages.complaints.classifyThresholdHint') }}</div>
            </template>

            <el-empty v-if="!stats && !loading" :description="t('pages.complaints.statsEmpty')" />

            <template v-if="stats">
                <el-row :gutter="20" class="summary-row">
                    <el-col v-for="card in summaryCards" :key="card.key" :xs="12" :sm="6">
                        <div
                            class="summary-card"
                            :class="[card.bg, { 'summary-card-clickable': card.clickable }]"
                            @click="card.clickable ? onSummaryCardClick(card.key) : undefined"
                        >
                            <div class="summary-label">{{ card.label }}</div>
                            <countup class="summary-value" :end="card.value" />
                            <div v-if="card.extra" class="summary-extra">{{ card.extra }}</div>
                        </div>
                    </el-col>
                </el-row>

                <div class="overview-block">
                    <div class="section-title">{{ t('pages.complaints.overview') }}</div>
                    <el-row :gutter="16">
                        <el-col v-for="section in dimensionSections" :key="section.key" :xs="24" :lg="8">
                            <div class="overview-panel">
                                <div class="overview-head">
                                    <span class="overview-name">{{ section.title }}</span>
                                    <el-tag size="small" type="info">{{ section.items.length }} {{ t('common.items') }}</el-tag>
                                </div>
                                <div v-if="section.topItem" class="overview-top">
                                    {{ t('pages.complaints.topPrefix') }}<strong>{{ section.topItem.label }}</strong>
                                    <span>{{ section.topItem.count }} {{ t('common.records') }} · {{ section.topItem.percentage }}%</span>
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
                    <div class="section-title">{{ t('pages.complaints.detail') }}</div>
                    <el-tabs v-model="activeDimension" type="border-card">
                        <el-tab-pane
                            v-for="section in dimensionSections"
                            :key="section.key"
                            :name="section.key"
                        >
                            <template #label>
                                <span class="tab-label-with-intro">
                                    {{ section.title }}
                                    <FeatureIntroIcon
                                        page-key="complaints"
                                        :section-key="section.key"
                                        :intros="intros"
                                        :title="section.title"
                                        @saved="setIntro"
                                    />
                                </span>
                            </template>
                            <el-row :gutter="16" class="dimension-metrics">
                                <el-col :xs="24" :sm="8">
                                    <el-statistic :title="t('pages.complaints.groupCount')" :value="section.items.length" />
                                </el-col>
                                <el-col :xs="24" :sm="8">
                                    <el-statistic
                                        v-if="section.topItem"
                                        :title="t('pages.complaints.topItem')"
                                        :value="section.topItem.count"
                                        :suffix="`${t('common.records')} · ${section.topItem.label}`"
                                    />
                                </el-col>
                                <el-col :xs="24" :sm="8">
                                    <el-statistic
                                        v-if="section.topItem"
                                        :title="t('pages.complaints.topRate')"
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
                                        <el-table-column prop="count" :label="t('pages.complaints.colCount')" width="90" align="right" sortable />
                                        <el-table-column :label="t('pages.complaints.colRate')" min-width="160">
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
import { useI18n } from 'vue-i18n';
import LazyApiDebugPanel from '@/components/lazy-api-debug-panel.vue';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import countup from '@/components/countup.vue';
import { useFeatureIntros } from '@/composables/useFeatureIntros';
import { useCachedRef } from '@/composables/useFormCache';
import { getComplaintStats, getComplaintSamples, createComplaint, getComplaintCategories, getComplaintSettings, updateComplaintSettings } from '@/api';
import { ElMessage } from 'element-plus';

const { t, locale } = useI18n();
const { intros, setIntro } = useFeatureIntros('complaints');

void locale;

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
        components.MarkLineComponent,
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
const classifyThreshold = ref(0.65);
const thresholdSaving = ref(false);

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
const sampleQuery = useCachedRef('complaints:sampleQuery', {
    address: '',
    text: '',
    category_name: '',
    dateRange: null as [string, string] | null,
});
const samplePage = ref({ page: 1, page_size: 10 });

interface ComplaintCategoryScore {
    category_id: number;
    category_name: string;
    similarity: number;
}

interface ComplaintCreateResult {
    complaint: ComplaintSample;
    category_created: boolean;
    assigned_category_id: number | null;
    assigned_category_name: string | null;
    similarity: number | null;
    category_scores: ComplaintCategoryScore[];
}

const createVisible = ref(false);
const createLoading = ref(false);
const createResult = ref<ComplaintCreateResult | null>(null);
const createForm = useCachedRef('complaints:createForm', {
    complaint_text: '',
    address: '',
    complaint_time: null as string | null,
});

interface ComplaintCategoryDetail {
    id: number;
    name: string;
    description: string;
    seed_phrases: string[];
    complaint_count: number;
    has_embedding: boolean;
}

const categoriesVisible = ref(false);
const categoriesLoading = ref(false);
const categoryRows = ref<ComplaintCategoryDetail[]>([]);
const categoryQuery = useCachedRef('complaints:categoryQuery', { name: '' });

const classifiedRate = computed(() => {
    if (!stats.value?.total) return 0;
    return Math.round((stats.value.classified / stats.value.total) * 1000) / 10;
});

const summaryCards = computed(() => {
    if (!stats.value) return [];
    return [
        { key: 'total', label: t('pages.complaints.total'), value: stats.value.total, bg: 'bg-total', extra: t('pages.complaints.allRecords') },
        {
            key: 'classified',
            label: t('pages.complaints.classified'),
            value: stats.value.classified,
            bg: 'bg-classified',
            extra: t('pages.complaints.classifyRate', { rate: classifiedRate.value }),
        },
        { key: 'unclassified', label: t('pages.complaints.unclassified'), value: stats.value.unclassified, bg: 'bg-unclassified', extra: t('pages.complaints.pendingClassify') },
        {
            key: 'categories',
            label: t('pages.complaints.typeCount'),
            value: stats.value.by_category.length,
            bg: 'bg-types',
            clickable: true,
            extra: t('pages.complaints.typeCountHint'),
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
            title: t('pages.complaints.dimCategory'),
            columnLabel: t('pages.complaints.colType'),
            items: stats.value.by_category,
            color: DIMENSION_COLORS.category,
            horizontalBar: true,
            useLineSecondary: false,
            miniLimit: 8,
        },
        {
            key: 'address',
            title: t('pages.complaints.dimAddress'),
            columnLabel: t('pages.complaints.colRegion'),
            items: stats.value.by_address,
            color: DIMENSION_COLORS.address,
            horizontalBar: false,
            useLineSecondary: false,
        },
        {
            key: 'time',
            title: t('pages.complaints.dimTime'),
            columnLabel: t('pages.complaints.colDate'),
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
        const [{ data: statsData }, { data: settingsData }] = await Promise.all([
            getComplaintStats(),
            getComplaintSettings(),
        ]);
        await ensureCharts();
        stats.value = statsData as ComplaintStatsReport;
        classifyThreshold.value = (settingsData as { classify_threshold: number }).classify_threshold;
    } finally {
        loading.value = false;
    }
}

async function onThresholdChange(value: number | undefined) {
    if (value == null || thresholdSaving.value) return;
    thresholdSaving.value = true;
    try {
        const { data } = await updateComplaintSettings({ classify_threshold: value });
        classifyThreshold.value = (data as { classify_threshold: number }).classify_threshold;
        ElMessage.success(t('pages.complaints.thresholdSaved'));
    } catch {
        const { data } = await getComplaintSettings();
        classifyThreshold.value = (data as { classify_threshold: number }).classify_threshold;
    } finally {
        thresholdSaving.value = false;
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

const createScoreOption = computed(() => {
    const scores = createResult.value?.category_scores ?? [];
    if (!scores.length || !echartsGraphic) return {};
    const top = scores.slice(0, 10);
    const labels = top.map((item) => item.category_name);
    const values = top.map((item) => item.similarity);
    const threshold = classifyThreshold.value;
    return {
        title: { text: t('pages.complaints.createScoreTitle'), left: 'center', textStyle: { fontSize: 14 } },
        tooltip: { trigger: 'axis', formatter: (params: { name: string; value: number }[]) => {
            const row = params[0];
            return `${row.name}<br/>${row.value.toFixed(4)}`;
        } },
        grid: { left: '3%', right: '8%', bottom: '3%', containLabel: true },
        xAxis: { type: 'value', min: 0, max: 1, axisLabel: { formatter: (v: number) => v.toFixed(2) } },
        yAxis: { type: 'category', data: [...labels].reverse(), inverse: true },
        series: [
            {
                type: 'bar',
                data: [...values].reverse(),
                barMaxWidth: 22,
                itemStyle: {
                    color: (params: { value: number }) => (params.value >= threshold ? DIMENSION_COLORS.category : '#c0c4cc'),
                    borderRadius: [0, 4, 4, 0],
                },
                markLine: {
                    silent: true,
                    symbol: 'none',
                    lineStyle: { type: 'dashed', color: '#f25e43' },
                    data: [{ xAxis: threshold, label: { formatter: threshold.toFixed(2), position: 'end' } }],
                },
            },
        ],
    };
});

function openCreateDialog() {
    createVisible.value = true;
    void ensureCharts();
}

function resetCreateForm() {
    createForm.value = { complaint_text: '', address: '', complaint_time: null };
    createResult.value = null;
}

async function submitComplaint() {
    const text = createForm.value.complaint_text.trim();
    if (text.length < 5) {
        ElMessage.warning(t('pages.complaints.createTextRequired'));
        return;
    }
    createLoading.value = true;
    try {
        const { data } = await createComplaint({
            complaint_text: text,
            address: createForm.value.address.trim() || undefined,
            complaint_time: createForm.value.complaint_time || undefined,
        });
        createResult.value = data as ComplaintCreateResult;
        await ensureCharts();
        await Promise.all([loadSamples(), loadStats()]);
    } finally {
        createLoading.value = false;
    }
}

function onSummaryCardClick(key: string) {
    if (key === 'categories') {
        categoriesVisible.value = true;
    }
}

async function loadCategories() {
    categoriesLoading.value = true;
    try {
        const { data } = await getComplaintCategories({
            name: categoryQuery.value.name.trim() || undefined,
        });
        categoryRows.value = data as ComplaintCategoryDetail[];
    } finally {
        categoriesLoading.value = false;
    }
}

function searchCategories() {
    loadCategories();
}

function viewCategorySamples(categoryName: string) {
    categoriesVisible.value = false;
    sampleQuery.value.category_name = categoryName;
    sampleQuery.value.text = '';
    sampleQuery.value.address = '';
    sampleQuery.value.dateRange = null;
    searchSamples();
    window.scrollTo({ top: 0, behavior: 'smooth' });
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
    margin-bottom: 8px;
}

.samples-toolbar {
    display: flex;
    justify-content: center;
    gap: 12px;
    margin-bottom: 12px;
}

.samples-pagination {
    margin-top: 16px;
    justify-content: flex-end;
}

.create-result {
    margin-top: 8px;
}

.create-alert {
    margin-bottom: 12px;
}

.create-tag {
    margin-left: 8px;
}

.create-chart-wrap {
    margin-top: 4px;
}

.create-score-chart {
    width: 100%;
    height: 280px;
}

.stats-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
}

.stats-header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}

.threshold-setting {
    display: inline-flex;
    align-items: center;
    gap: 8px;
}

.threshold-label {
    font-size: 13px;
    color: #606266;
    white-space: nowrap;
}

.threshold-hint {
    margin-top: 8px;
    font-size: 12px;
    color: #909399;
    line-height: 1.5;
}

.content-title-row {
    display: inline-flex;
    align-items: center;
}

.tab-label-with-intro {
    display: inline-flex;
    align-items: center;
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

.summary-card-clickable {
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.summary-card-clickable:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(156, 39, 176, 0.35);
}

.categories-form {
    margin-bottom: 12px;
}

.category-expand {
    padding: 8px 12px 12px;
}

.category-expand-title {
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 8px;
    color: #606266;
}

.seed-tag {
    margin: 0 8px 8px 0;
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
