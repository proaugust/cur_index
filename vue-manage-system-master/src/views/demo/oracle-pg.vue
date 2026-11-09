<template>
    <div class="container oracle-pg-page">
        <el-card shadow="hover">
            <template #header>
                <div class="page-header">
                    <span class="page-title">{{ t('pages.oraclePg.title') }}</span>
                    <FeatureIntroIcon
                        page-key="oracle-pg"
                        section-key="page"
                        :intros="intros"
                        :title="t('pages.oraclePg.title')"
                        @saved="setIntro"
                    />
                </div>
                <p class="page-subtitle">{{ t('pages.oraclePg.subtitle') }}</p>
            </template>

            <el-alert
                v-if="status && !status.installed"
                :title="t('pages.oraclePg.missing')"
                type="warning"
                show-icon
                :closable="false"
                class="block"
            />
            <el-alert
                v-else-if="status?.installed"
                :title="t('pages.oraclePg.installed', { version: status.version, bench: status.bench_rows, emp: status.emp_rows })"
                type="success"
                show-icon
                :closable="false"
                class="block"
            />

            <div class="action-bar">
                <span class="field-label">{{ t('pages.oraclePg.rows') }}</span>
                <el-input
                    v-model="rowsText"
                    class="rows-input"
                    clearable
                    :disabled="!!loading"
                    :placeholder="t('pages.oraclePg.rowsHint')"
                    @keyup.enter="seed(true)"
                />
                <el-button type="primary" :loading="loading === 'seed'" :disabled="!!loading" @click="seed(true)">
                    {{ t('pages.oraclePg.seed') }}
                </el-button>
                <el-button type="success" :loading="loading === 'run'" :disabled="!!loading" @click="run">
                    {{ t('pages.oraclePg.run') }}
                </el-button>
                <el-button :loading="loading === 'both'" :disabled="!!loading" @click="seedAndRun">
                    {{ t('pages.oraclePg.seedAndRun') }}
                </el-button>
                <el-button
                    type="danger"
                    plain
                    :loading="loading === 'clear'"
                    :disabled="!!loading"
                    @click="clearAll"
                >
                    {{ t('pages.oraclePg.clear') }}
                </el-button>
                <el-button :loading="dataLoading" :disabled="!!loading" @click="loadDataRows">
                    {{ t('common.refresh') }}
                </el-button>
            </div>

            <div v-if="fieldTags.length" class="field-line">
                <span class="field-label">{{ t('pages.oraclePg.fields') }}</span>
                <el-tag v-for="name in fieldTags" :key="name" size="small" effect="plain">{{ name }}</el-tag>
            </div>

            <div
                v-if="(status?.bench_rows || 0) > 0 || (status?.emp_rows || 0) > 0"
                class="data-section"
                v-memo="[dataRows, dataFields, dataTable, dataPage, dataPageSize, dataTotal, dataLoading]"
            >
                <div class="data-toolbar">
                    <span class="section-label">{{ t('pages.oraclePg.dataTitle') }}</span>
                    <el-radio-group v-model="dataTable" size="small" :disabled="dataLoading" @change="onDataTableChange">
                        <el-radio-button value="emp_bench">{{ t('pages.oraclePg.tableBench') }}</el-radio-button>
                        <el-radio-button value="emp">{{ t('pages.oraclePg.tableEmp') }}</el-radio-button>
                        <el-radio-button value="dept">{{ t('pages.oraclePg.tableDept') }}</el-radio-button>
                    </el-radio-group>
                </div>
                <el-table v-loading="dataLoading" :data="dataRows" stripe size="small" class="block" max-height="420">
                    <el-table-column
                        v-for="col in dataFields"
                        :key="col"
                        :prop="col"
                        :label="col"
                        min-width="110"
                        show-overflow-tooltip
                    />
                </el-table>
                <div class="pager">
                    <el-pagination
                        v-model:current-page="dataPage"
                        v-model:page-size="dataPageSize"
                        background
                        layout="total, sizes, prev, pager, next"
                        :total="dataTotal"
                        :page-sizes="[10, 20, 50, 100]"
                        @current-change="loadDataRows"
                        @size-change="onDataPageSizeChange"
                    />
                </div>
            </div>

            <div v-if="report" class="chart-wrap" v-memo="[chartOption]">
                <div class="section-label">
                    {{ t('pages.oraclePg.chartTitle') }} (ms) —
                    {{ t('pages.oraclePg.seriesPlugin') }} / {{ t('pages.oraclePg.seriesNative') }}
                </div>
                <p class="filter-hint">{{ t('pages.oraclePg.chartHint') }}</p>
                <VChart v-if="VChart" class="chart" :option="chartOption" autoresize />
            </div>

            <div v-if="report" class="result-filters" v-memo="[report.summary, report.categories, verdictFilter, category]">
                <el-row :gutter="12" class="stat-row">
                    <el-col :span="4">
                        <div
                            class="stat clickable"
                            :class="{ active: verdictFilter === 'usable' }"
                            @click="toggleVerdict('usable')"
                        >
                            <div class="stat-num">{{ report.summary.usable }}/{{ report.summary.total }}</div>
                            <div class="stat-label">{{ t('pages.oraclePg.statUsable') }}</div>
                        </div>
                    </el-col>
                    <el-col :span="4">
                        <div
                            class="stat clickable"
                            :class="{ active: verdictFilter === 'acceptable' }"
                            @click="toggleVerdict('acceptable')"
                        >
                            <div class="stat-num">{{ report.summary.acceptable }}</div>
                            <div class="stat-label">{{ t('pages.oraclePg.statOk') }}</div>
                        </div>
                    </el-col>
                    <el-col :span="4">
                        <div
                            class="stat clickable"
                            :class="{ active: verdictFilter === 'slow' }"
                            @click="toggleVerdict('slow')"
                        >
                            <div class="stat-num">{{ report.summary.slowish + report.summary.slow }}</div>
                            <div class="stat-label">{{ t('pages.oraclePg.statSlow') }}</div>
                        </div>
                    </el-col>
                    <el-col :span="4">
                        <div
                            class="stat clickable"
                            :class="{ active: verdictFilter === 'failed' }"
                            @click="toggleVerdict('failed')"
                        >
                            <div class="stat-num">{{ report.summary.failed }}</div>
                            <div class="stat-label">{{ t('pages.oraclePg.statFail') }}</div>
                        </div>
                    </el-col>
                    <el-col :span="8">
                        <div class="stat">
                            <div class="stat-num">{{ report.summary.plugin_ms }} / {{ report.summary.native_ms }}</div>
                            <div class="stat-label">{{ t('pages.oraclePg.statMs') }}</div>
                        </div>
                    </el-col>
                </el-row>
                <div class="filter-line">
                    <el-radio-group v-model="category" size="small">
                        <el-radio-button value="">{{ t('pages.oraclePg.all') }}</el-radio-button>
                        <el-radio-button v-for="item in report.categories" :key="item.name" :value="item.name">
                            {{ item.name }} {{ item.usable }}/{{ item.total }}
                        </el-radio-button>
                    </el-radio-group>
                </div>
                <p class="filter-hint">{{ t('pages.oraclePg.filterHint') }}</p>
            </div>

            <el-table
                v-if="report"
                v-memo="[visibleCases]"
                :data="visibleCases"
                stripe
                size="small"
                class="block"
                highlight-current-row
                @row-click="onCaseRowClick"
            >
                <el-table-column type="expand">
                    <template #default="{ row }">
                        <div class="sample-wrap">
                            <p v-if="row.error" class="err">{{ row.error }}</p>
                            <p class="note">{{ row.note }}</p>
                            <el-table v-if="row.sample.length" :data="row.sample" size="small" border>
                                <el-table-column
                                    v-for="col in columnsOf(row)"
                                    :key="col"
                                    :prop="col"
                                    :label="col"
                                    min-width="108"
                                    show-overflow-tooltip
                                />
                            </el-table>
                        </div>
                    </template>
                </el-table-column>
                <el-table-column prop="category" :label="t('pages.oraclePg.colCategory')" width="88" />
                <el-table-column prop="fn" :label="t('pages.oraclePg.colFn')" min-width="170" />
                <el-table-column prop="what" :label="t('pages.oraclePg.colWhat')" min-width="240" show-overflow-tooltip />
                <el-table-column prop="plugin_ms" :label="t('pages.oraclePg.colPluginMs')" width="110" align="right" />
                <el-table-column prop="native_ms" :label="t('pages.oraclePg.colNativeMs')" width="110" align="right" />
                <el-table-column :label="t('pages.oraclePg.colRatio')" width="80" align="right">
                    <template #default="{ row }">{{ row.ratio ?? '—' }}</template>
                </el-table-column>
                <el-table-column :label="t('pages.oraclePg.colVerdict')" width="96">
                    <template #default="{ row }">
                        <el-tag :type="tagType(row.verdict)" size="small">{{ row.verdict }}</el-tag>
                    </template>
                </el-table-column>
            </el-table>

            <div v-if="report" class="analysis" v-memo="[report.analysis]">
                <div class="section-label">{{ t('pages.oraclePg.analysis') }}</div>
                <ul>
                    <li v-for="(line, index) in report.analysis" :key="index">{{ line }}</li>
                </ul>
            </div>

            <div v-if="report" class="sql-section">
                <div class="data-toolbar">
                    <span class="section-label">{{ t('pages.oraclePg.sqlTitle') }}</span>
                    <el-select
                        :model-value="selectedCaseId"
                        class="case-select"
                        filterable
                        @update:model-value="(id) => selectCase(String(id ?? ''))"
                    >
                        <el-option
                            v-for="item in report.cases"
                            :key="item.id"
                            :label="`${item.fn} · ${item.what}`"
                            :value="item.id"
                        />
                    </el-select>
                    <el-button :disabled="!selectedCaseId || caseLoading" @click="resetSql">
                        {{ t('pages.oraclePg.sqlReset') }}
                    </el-button>
                    <el-button type="primary" :loading="caseLoading" :disabled="!selectedCaseId" @click="rerunCase">
                        {{ t('pages.oraclePg.sqlRerun') }}
                    </el-button>
                </div>
                <p class="filter-hint">{{ t('pages.oraclePg.sqlHint') }}</p>
                <div class="sql-grid">
                    <div v-for="kind in sqlKinds" :key="kind" class="sql-block">
                        <div class="sql-block-head">
                            <el-button
                                size="small"
                                type="primary"
                                plain
                                :loading="sqlRunLoading === kind"
                                :disabled="!selectedCaseId || !!sqlRunLoading || caseLoading"
                                @click="runSingleSql(kind)"
                            >
                                {{ t('pages.oraclePg.sqlRunOne') }}
                            </el-button>
                            <div class="sql-label">{{ kind }}</div>
                        </div>
                        <el-input
                            :model-value="sqlText(kind)"
                            type="textarea"
                            :rows="14"
                            class="sql-input"
                            @update:model-value="(value) => setSqlText(kind, String(value ?? ''))"
                            @blur="flushPersist"
                        />
                        <div class="sql-result" :class="{ pending: !sqlResults[kind] }">
                            <template v-if="sqlResults[kind]">
                                <div class="sql-result-meta">
                                    <span>{{ t('pages.oraclePg.sqlElapsed', { ms: sqlResults[kind]?.ms ?? '—' }) }}</span>
                                    <el-tag
                                        v-if="kind === 'check_sql' && sqlResults[kind]?.passed != null"
                                        :type="sqlResults[kind]?.passed ? 'success' : 'danger'"
                                        size="small"
                                    >
                                        {{
                                            sqlResults[kind]?.passed
                                                ? t('pages.oraclePg.sqlPassed')
                                                : t('pages.oraclePg.sqlFailedCheck')
                                        }}
                                    </el-tag>
                                </div>
                                <p v-if="sqlResults[kind]?.error" class="err">{{ sqlResults[kind]?.error }}</p>
                                <p v-else-if="kind === 'check_sql'" class="note">
                                    {{ t('pages.oraclePg.sqlScalar') }}:
                                    {{ formatSqlCell(sqlResults[kind]?.scalar) }}
                                </p>
                                <el-table
                                    v-if="(sqlResults[kind]?.rows?.length || 0) > 0"
                                    :data="sqlResults[kind]?.rows || []"
                                    stripe
                                    size="small"
                                    max-height="220"
                                    class="sql-result-table"
                                >
                                    <el-table-column
                                        v-for="col in sqlResultColumns(sqlResults[kind]?.rows || [])"
                                        :key="col"
                                        :prop="col"
                                        :label="col"
                                        min-width="100"
                                        show-overflow-tooltip
                                    />
                                </el-table>
                                <div v-if="(sqlResults[kind]?.analysis?.length || 0) > 0" class="sql-analysis">
                                    <div class="section-label">{{ t('pages.oraclePg.sqlAnalysis') }}</div>
                                    <ul>
                                        <li v-for="(line, index) in sqlResults[kind]?.analysis || []" :key="index">
                                            {{ line }}
                                        </li>
                                    </ul>
                                </div>
                                <el-collapse v-if="sqlResults[kind]?.explain" class="sql-explain">
                                    <el-collapse-item :title="t('pages.oraclePg.sqlExplain')" name="explain">
                                        <pre class="explain-pre">{{ sqlResults[kind]?.explain }}</pre>
                                    </el-collapse-item>
                                </el-collapse>
                            </template>
                            <p v-else class="note">{{ t('pages.oraclePg.sqlRunOne') }} → {{ t('pages.oraclePg.sqlAnalysis') }}</p>
                        </div>
                    </div>
                </div>
                <div v-if="sqlTimingCount > 0" class="chart-wrap sql-timing-wrap">
                    <div class="section-label">{{ t('pages.oraclePg.sqlTimingChart') }} (ms)</div>
                    <VChart v-if="VChart" class="chart sql-timing-chart" :option="sqlTimingChartOption" autoresize />
                </div>
            </div>

            <el-empty v-if="!report && !loading" :description="t('pages.oraclePg.empty')" :image-size="80" />
        </el-card>
    </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, type Component } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox } from 'element-plus';
import FeatureIntroIcon from '@/components/feature-intro-icon.vue';
import { useFeatureIntros } from '@/composables/useFeatureIntros';
import {
    clearOracleCompat,
    getOracleCompatStatus,
    listOracleCompatRows,
    runOracleCompat,
    runOracleCompatCase,
    runOracleCompatSql,
    seedOracleCompat,
} from '@/api';

interface SampleRow {
    [key: string]: string | number | boolean | null;
}

type SqlKind = 'sample_sql' | 'check_sql' | 'plugin_bench' | 'native_bench';

interface CaseSql {
    sample_sql: string;
    check_sql: string;
    plugin_bench: string;
    native_bench: string;
}

interface SqlRunResult {
    kind: SqlKind;
    ms: number | null;
    rows: SampleRow[] | null;
    scalar: string | number | boolean | null;
    passed: boolean | null;
    explain: string | null;
    analysis: string[];
    error: string | null;
}

interface CaseRow extends CaseSql {
    id: string;
    category: string;
    fn: string;
    what: string;
    note: string;
    usable: boolean;
    error: string | null;
    sample: SampleRow[];
    plugin_ms: number | null;
    native_ms: number | null;
    ratio: number | null;
    verdict: string;
}

interface Report {
    version: string;
    emp_rows: number;
    bench_rows: number;
    emp_fields: string[];
    dept_fields: string[];
    summary: {
        total: number;
        usable: number;
        failed: number;
        acceptable: number;
        slowish: number;
        slow: number;
        plugin_ms: number;
        native_ms: number;
        wall_ms: number;
    };
    categories: { name: string; total: number; usable: number; plugin_ms: number; native_ms: number }[];
    cases: CaseRow[];
    analysis: string[];
}

interface Status {
    installed: boolean;
    version: string | null;
    emp_rows: number;
    bench_rows: number;
    emp_fields: string[];
    dept_fields: string[];
}

type DataTable = 'emp' | 'emp_bench' | 'dept';
type VerdictFilter = '' | 'usable' | 'acceptable' | 'slow' | 'failed';

interface CaseSqlCache {
    texts: CaseSql;
    results: Partial<Record<SqlKind, SqlRunResult>>;
}

interface PersistedState {
    report: Report;
    selectedCaseId: string;
    rowsText: string;
    sqlByCase: Record<string, CaseSqlCache>;
}

const ROWS_MIN = 1000;
const ROWS_MAX = 100000;
const STORAGE_KEY = 'oracle-pg:last-run';

const { t } = useI18n();
const { intros, setIntro } = useFeatureIntros('oracle-pg');
const VChart = shallowRef<Component | null>(null);
const status = ref<Status | null>(null);
const report = ref<Report | null>(null);
const rowsText = ref('20000');
const loading = ref<'' | 'seed' | 'run' | 'both' | 'clear'>('');
const category = ref('');
const verdictFilter = ref<VerdictFilter>('');

const dataTable = ref<DataTable>('emp_bench');
const dataRows = ref<SampleRow[]>([]);
const dataFields = ref<string[]>([]);
const dataTotal = ref(0);
const dataPage = ref(1);
const dataPageSize = ref(20);
const dataLoading = ref(false);

const selectedCaseId = ref('');
const editSampleSql = ref('');
const editCheckSql = ref('');
const editPluginBench = ref('');
const editNativeBench = ref('');
const caseLoading = ref(false);
const sqlDefaults = ref<Record<string, CaseSql>>({});
const sqlRunLoading = ref<SqlKind | ''>('');
const sqlResults = ref<Partial<Record<SqlKind, SqlRunResult>>>({});
const sqlByCase = ref<Record<string, CaseSqlCache>>({});
const sqlKinds: SqlKind[] = ['sample_sql', 'check_sql', 'plugin_bench', 'native_bench'];

function sqlText(kind: SqlKind): string {
    if (kind === 'sample_sql') return editSampleSql.value;
    if (kind === 'check_sql') return editCheckSql.value;
    if (kind === 'plugin_bench') return editPluginBench.value;
    return editNativeBench.value;
}

function currentSqlTexts(): CaseSql {
    return {
        sample_sql: editSampleSql.value,
        check_sql: editCheckSql.value,
        plugin_bench: editPluginBench.value,
        native_bench: editNativeBench.value,
    };
}

function applySqlTexts(texts: CaseSql) {
    editSampleSql.value = texts.sample_sql;
    editCheckSql.value = texts.check_sql;
    editPluginBench.value = texts.plugin_bench;
    editNativeBench.value = texts.native_bench;
}

function setSqlText(kind: SqlKind, value: string) {
    if (kind === 'sample_sql') editSampleSql.value = value;
    else if (kind === 'check_sql') editCheckSql.value = value;
    else if (kind === 'plugin_bench') editPluginBench.value = value;
    else editNativeBench.value = value;
    schedulePersist();
}

let persistTimer: ReturnType<typeof setTimeout> | null = null;

function schedulePersist() {
    if (persistTimer) clearTimeout(persistTimer);
    persistTimer = setTimeout(() => {
        persistTimer = null;
        persistState();
    }, 400);
}

function flushPersist() {
    if (persistTimer) {
        clearTimeout(persistTimer);
        persistTimer = null;
    }
    persistState();
}

function sqlResultColumns(rows: SampleRow[]): string[] {
    if (!rows.length) return [];
    return Object.keys(rows[0]);
}

function formatSqlCell(value: string | number | boolean | null | undefined) {
    if (value === null || value === undefined) return 'null';
    return String(value);
}

function clearSqlResults() {
    sqlResults.value = {};
}

function snapshotCurrentCase() {
    if (!selectedCaseId.value) return;
    sqlByCase.value = {
        ...sqlByCase.value,
        [selectedCaseId.value]: {
            texts: currentSqlTexts(),
            results: { ...sqlResults.value },
        },
    };
}

function persistState() {
    if (!report.value) return;
    snapshotCurrentCase();
    const payload: PersistedState = {
        report: report.value,
        selectedCaseId: selectedCaseId.value,
        rowsText: rowsText.value,
        sqlByCase: sqlByCase.value,
    };
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    } catch {
        /* ignore quota / private mode */
    }
}

function clearPersistedState() {
    try {
        localStorage.removeItem(STORAGE_KEY);
    } catch {
        /* ignore */
    }
}

function applyCaseEditor(caseId: string) {
    const item = report.value?.cases.find((row) => row.id === caseId);
    const cached = sqlByCase.value[caseId];
    if (cached) {
        applySqlTexts(cached.texts);
        sqlResults.value = { ...cached.results };
        return;
    }
    if (item) {
        applySqlTexts({
            sample_sql: item.sample_sql,
            check_sql: item.check_sql,
            plugin_bench: item.plugin_bench,
            native_bench: item.native_bench,
        });
        clearSqlResults();
        return;
    }
    applySqlTexts({ sample_sql: '', check_sql: '', plugin_bench: '', native_bench: '' });
    clearSqlResults();
}

async function restorePersistedState() {
    let raw: string | null = null;
    try {
        raw = localStorage.getItem(STORAGE_KEY);
    } catch {
        return;
    }
    if (!raw) return;
    try {
        const data = JSON.parse(raw) as PersistedState;
        if (!data?.report?.cases?.length) return;
        await ensureChart();
        report.value = data.report;
        if (typeof data.rowsText === 'string' && data.rowsText) {
            rowsText.value = data.rowsText;
        }
        sqlByCase.value = data.sqlByCase || {};
        captureSqlDefaults(data.report.cases);
        const caseId =
            data.selectedCaseId && data.report.cases.some((row) => row.id === data.selectedCaseId)
                ? data.selectedCaseId
                : data.report.cases[0].id;
        selectedCaseId.value = caseId;
        applyCaseEditor(caseId);
    } catch {
        clearPersistedState();
    }
}

const fieldTags = computed(() => {
    const source = report.value ?? status.value;
    if (!source) return [];
    return [...source.dept_fields, ...source.emp_fields];
});

const visibleCases = computed(() => {
    let cases = report.value?.cases ?? [];
    if (category.value) {
        cases = cases.filter((item) => item.category === category.value);
    }
    if (verdictFilter.value === 'usable') {
        cases = cases.filter((item) => item.usable);
    } else if (verdictFilter.value === 'acceptable') {
        cases = cases.filter((item) => item.verdict === '可接受');
    } else if (verdictFilter.value === 'slow') {
        cases = cases.filter((item) => item.verdict === '略慢' || item.verdict === '偏慢');
    } else if (verdictFilter.value === 'failed') {
        cases = cases.filter((item) => !item.usable || item.verdict === '不可用');
    }
    return cases;
});

const sqlTimingCount = computed(() => sqlKinds.filter((kind) => sqlResults.value[kind]?.ms != null).length);

const sqlTimingChartOption = computed(() => {
    const labels = sqlKinds.filter((kind) => sqlResults.value[kind]?.ms != null);
    return {
        tooltip: {
            trigger: 'axis',
            valueFormatter: (value: number | string) => `${value} ms`,
        },
        grid: { left: 120, right: 40, top: 16, bottom: 24 },
        xAxis: { type: 'value', name: 'ms', nameGap: 8 },
        yAxis: {
            type: 'category',
            inverse: true,
            data: labels,
        },
        series: [
            {
                type: 'bar',
                data: labels.map((kind) => sqlResults.value[kind]?.ms ?? 0),
            },
        ],
    };
});

const chartOption = computed(() => {
    const cases = report.value?.cases ?? [];
    return {
        tooltip: {
            trigger: 'axis',
            valueFormatter: (value: number | string) => `${value} ms`,
        },
        legend: { data: [t('pages.oraclePg.seriesPlugin'), t('pages.oraclePg.seriesNative')] },
        grid: { left: 150, right: 40, top: 36, bottom: 24 },
        xAxis: { type: 'value', name: 'ms', nameGap: 8 },

        yAxis: {
            type: 'category',
            inverse: true,
            data: cases.map((item) => item.fn.replace('oracle.', '')),
        },
        series: [
            {
                name: t('pages.oraclePg.seriesPlugin'),
                type: 'bar',
                data: cases.map((item) => item.plugin_ms ?? 0),
            },
            {
                name: t('pages.oraclePg.seriesNative'),
                type: 'bar',
                data: cases.map((item) => item.native_ms ?? 0),
            },
        ],
    };
});

function tagType(verdict: string) {
    if (verdict === '可接受' || verdict === '可用') return 'success';
    if (verdict === '略慢') return 'warning';
    return 'danger';
}

function columnsOf(row: CaseRow) {
    return Object.keys(row.sample[0] || {});
}

function toggleVerdict(key: Exclude<VerdictFilter, ''>) {
    verdictFilter.value = verdictFilter.value === key ? '' : key;
}

function captureSqlDefaults(cases: CaseRow[]) {
    const next: Record<string, CaseSql> = {};
    for (const item of cases) {
        next[item.id] = {
            sample_sql: item.sample_sql,
            check_sql: item.check_sql,
            plugin_bench: item.plugin_bench,
            native_bench: item.native_bench,
        };
    }
    sqlDefaults.value = next;
}

function selectCase(caseId: string) {
    if (caseId === selectedCaseId.value) {
        applyCaseEditor(caseId);
        return;
    }
    snapshotCurrentCase();
    selectedCaseId.value = caseId;
    applyCaseEditor(caseId);
    persistState();
}

function onCaseRowClick(row: CaseRow) {
    selectCase(row.id);
}

function resetSql() {
    const defaults = sqlDefaults.value[selectedCaseId.value];
    if (!defaults) return;
    applySqlTexts(defaults);
    clearSqlResults();
    snapshotCurrentCase();
    persistState();
}

async function runSingleSql(kind: SqlKind) {
    if (!selectedCaseId.value) return;
    const sql = sqlText(kind).trim();
    if (!sql) {
        ElMessage.warning(t('pages.oraclePg.sqlEmpty'));
        return;
    }
    sqlRunLoading.value = kind;
    try {
        await ensureChart();
        const res = await runOracleCompatSql({
            case_id: selectedCaseId.value,
            kind,
            sql,
        });
        const data = res.data as SqlRunResult & { error?: string | null };
        sqlResults.value = {
            ...sqlResults.value,
            [kind]: {
                kind,
                ms: data.ms ?? null,
                rows: data.rows ?? null,
                scalar: data.scalar ?? null,
                passed: data.passed ?? null,
                explain: data.explain ?? null,
                analysis: data.analysis ?? [],
                error: data.error ?? null,
            },
        };
        snapshotCurrentCase();
        persistState();
        if (data.error) {
            ElMessage.error(data.error);
        } else {
            ElMessage.success(t('pages.oraclePg.sqlRunOneOk', { kind }));
        }
    } catch (err) {
        ElMessage.error(errorText(err));
    } finally {
        sqlRunLoading.value = '';
    }
}

function rebuildSummary(cases: CaseRow[], wallMs: number) {
    if (!report.value) return;
    const usable = cases.filter((item) => item.usable).length;
    report.value.summary = {
        total: cases.length,
        usable,
        failed: cases.length - usable,
        acceptable: cases.filter((item) => item.verdict === '可接受').length,
        slowish: cases.filter((item) => item.verdict === '略慢').length,
        slow: cases.filter((item) => item.verdict === '偏慢').length,
        plugin_ms: Math.round(cases.reduce((sum, item) => sum + (item.plugin_ms || 0), 0) * 100) / 100,
        native_ms: Math.round(cases.reduce((sum, item) => sum + (item.native_ms || 0), 0) * 100) / 100,
        wall_ms: wallMs,
    };
    report.value.categories = [...new Set(cases.map((item) => item.category))].map((name) => {
        const group = cases.filter((item) => item.category === name);
        return {
            name,
            total: group.length,
            usable: group.filter((item) => item.usable).length,
            plugin_ms: Math.round(group.reduce((sum, item) => sum + (item.plugin_ms || 0), 0) * 100) / 100,
            native_ms: Math.round(group.reduce((sum, item) => sum + (item.native_ms || 0), 0) * 100) / 100,
        };
    });
}

async function rerunCase() {
    if (!selectedCaseId.value || !report.value) return;
    caseLoading.value = true;
    try {
        const res = await runOracleCompatCase({
            case_id: selectedCaseId.value,
            sample_sql: editSampleSql.value,
            check_sql: editCheckSql.value,
            plugin_bench: editPluginBench.value,
            native_bench: editNativeBench.value,
        });
        const updated = res.data.case as CaseRow;
        const cases = report.value.cases.map((item) => (item.id === updated.id ? updated : item));
        report.value.cases = cases;
        rebuildSummary(cases, Number(res.data.wall_ms) || report.value.summary.wall_ms);
        applySqlTexts({
            sample_sql: updated.sample_sql,
            check_sql: updated.check_sql,
            plugin_bench: updated.plugin_bench,
            native_bench: updated.native_bench,
        });
        clearSqlResults();
        snapshotCurrentCase();
        persistState();
        ElMessage.success(t('pages.oraclePg.sqlRerunOk', { fn: updated.fn }));
    } catch (err) {
        ElMessage.error(errorText(err));
    } finally {
        caseLoading.value = false;
    }
}

function parseRows(): number | null {
    const raw = rowsText.value.trim();
    if (!/^\d+$/.test(raw)) return null;
    const value = Number(raw);
    if (value < ROWS_MIN || value > ROWS_MAX) return null;
    return value;
}

function errorText(err: unknown) {
    const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length) {
        const first = detail[0] as { msg?: string };
        return first.msg || t('pages.oraclePg.failed');
    }
    return t('pages.oraclePg.failed');
}

async function ensureChart() {
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
        components.GridComponent,
        components.TooltipComponent,
        components.LegendComponent,
    ]);
    VChart.value = vueEcharts.default;
}

async function loadDataRows() {
    if ((status.value?.bench_rows || 0) <= 0 && (status.value?.emp_rows || 0) <= 0) {
        dataRows.value = [];
        dataFields.value = [];
        dataTotal.value = 0;
        return;
    }
    dataLoading.value = true;
    try {
        const res = await listOracleCompatRows({
            table: dataTable.value,
            page: dataPage.value,
            page_size: dataPageSize.value,
        });
        dataRows.value = res.data.items as SampleRow[];
        dataFields.value = res.data.fields as string[];
        dataTotal.value = res.data.total as number;
        dataPage.value = res.data.page as number;
        dataPageSize.value = res.data.page_size as number;
    } catch (err) {
        ElMessage.error(errorText(err));
    } finally {
        dataLoading.value = false;
    }
}

function onDataTableChange() {
    dataPage.value = 1;
    loadDataRows();
}

function onDataPageSizeChange() {
    dataPage.value = 1;
    loadDataRows();
}

async function loadStatus() {
    const res = await getOracleCompatStatus();
    status.value = res.data as Status;
    if ((status.value.bench_rows || 0) > 0 || (status.value.emp_rows || 0) > 0) {
        await loadDataRows();
    }
}

async function seed(showMessage: boolean) {
    const rows = parseRows();
    if (rows == null) {
        ElMessage.warning(t('pages.oraclePg.rowsInvalid', { min: ROWS_MIN, max: ROWS_MAX }));
        return;
    }
    loading.value = loading.value === 'both' ? 'both' : 'seed';
    try {
        const res = await seedOracleCompat(rows);
        status.value = {
            installed: true,
            version: res.data.version,
            emp_rows: res.data.emp_rows,
            bench_rows: res.data.bench_rows,
            emp_fields: res.data.emp_fields,
            dept_fields: res.data.dept_fields,
        };
        dataTable.value = 'emp_bench';
        dataPage.value = 1;
        await loadDataRows();
        if (showMessage) {
            ElMessage.success(
                t('pages.oraclePg.seeded', {
                    added: res.data.added_rows ?? rows,
                    bench: res.data.bench_rows,
                })
            );
        }
    } catch (err) {
        ElMessage.error(errorText(err));
        throw err;
    } finally {
        if (loading.value === 'seed') loading.value = '';
    }
}

async function run() {
    const keep = loading.value;
    loading.value = keep === 'both' ? 'both' : 'run';
    try {
        await ensureChart();
        const res = await runOracleCompat();
        report.value = res.data as Report;
        category.value = '';
        verdictFilter.value = '';
        sqlByCase.value = {};
        clearSqlResults();
        captureSqlDefaults(report.value.cases);
        selectedCaseId.value = report.value.cases[0]?.id || '';
        applyCaseEditor(selectedCaseId.value);
        persistState();
        status.value = {
            installed: true,
            version: report.value.version,
            emp_rows: report.value.emp_rows,
            bench_rows: report.value.bench_rows,
            emp_fields: report.value.emp_fields,
            dept_fields: report.value.dept_fields,
        };
    } catch (err) {
        ElMessage.error(errorText(err));
        throw err;
    } finally {
        if (loading.value === 'run' || loading.value === 'both') loading.value = '';
    }
}

async function seedAndRun() {
    const rows = parseRows();
    if (rows == null) {
        ElMessage.warning(t('pages.oraclePg.rowsInvalid', { min: ROWS_MIN, max: ROWS_MAX }));
        return;
    }
    loading.value = 'both';
    try {
        await seed(false);
        await run();
    } catch {
        loading.value = '';
    }
}

async function clearAll() {
    try {
        await ElMessageBox.confirm(t('pages.oraclePg.clearConfirm'), t('pages.oraclePg.clear'), {
            type: 'warning',
        });
    } catch {
        return;
    }
    loading.value = 'clear';
    try {
        const res = await clearOracleCompat();
        status.value = res.data as Status;
        report.value = null;
        dataRows.value = [];
        dataTotal.value = 0;
        selectedCaseId.value = '';
        sqlByCase.value = {};
        sqlDefaults.value = {};
        applySqlTexts({ sample_sql: '', check_sql: '', plugin_bench: '', native_bench: '' });
        clearSqlResults();
        clearPersistedState();
        ElMessage.success(t('pages.oraclePg.cleared'));
    } catch (err) {
        ElMessage.error(errorText(err));
    } finally {
        loading.value = '';
    }
}

onMounted(() => {
    loadStatus()
        .then(() => restorePersistedState())
        .catch((err) => ElMessage.error(errorText(err)));
});

onBeforeUnmount(() => {
    flushPersist();
});
</script>

<style scoped>
.page-header {
    display: flex;
    align-items: center;
    gap: 8px;
}
.page-title {
    font-size: 16px;
    font-weight: 600;
}
.page-subtitle {
    margin: 8px 0 0;
    color: var(--el-text-color-secondary);
    font-size: 13px;
}
.block {
    margin-top: 12px;
}
.action-bar,
.field-line,
.filter-line,
.data-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
}
.rows-input {
    width: 160px;
}
.field-label,
.section-label {
    color: var(--el-text-color-regular);
    font-size: 13px;
}
.data-section {
    margin-top: 8px;
}
.pager {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
}
.result-filters {
    margin-top: 16px;
}
.stat-row {
    margin-top: 0;
}
.result-filters .filter-line {
    margin-top: 10px;
}
.stat {
    background: var(--el-fill-color-light);
    border-radius: 6px;
    padding: 12px;
    border: 1px solid transparent;
}
.stat.clickable {
    cursor: pointer;
    user-select: none;
}
.stat.clickable:hover {
    border-color: var(--el-color-primary-light-5);
}
.stat.active {
    border-color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
}
.stat-num {
    font-size: 20px;
    font-weight: 600;
}
.stat-label {
    margin-top: 4px;
    color: var(--el-text-color-secondary);
    font-size: 12px;
}
.filter-hint {
    margin: 8px 0 0;
    color: var(--el-text-color-secondary);
    font-size: 12px;
}
.chart-wrap {
    margin-top: 16px;
}
.chart {
    height: 560px;
}
.sample-wrap {
    padding: 8px 12px 12px 48px;
}
.note {
    margin: 0 0 8px;
    color: var(--el-text-color-secondary);
}
.err {
    margin: 0 0 8px;
    color: var(--el-color-danger);
}
.analysis ul {
    margin: 8px 0 0;
    padding-left: 18px;
}
.analysis li + li {
    margin-top: 6px;
}
.sql-section {
    margin-top: 16px;
}
.case-select {
    min-width: 320px;
}
.sql-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
    margin-top: 8px;
}
.sql-block {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px;
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 8px;
    background: var(--el-fill-color-blank);
}
.sql-block-head {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 8px;
}
.sql-label {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12px;
    color: var(--el-text-color-secondary);
}
.sql-input :deep(textarea) {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12px;
    line-height: 1.5;
    min-height: 280px;
}
.sql-result {
    margin-top: 4px;
    padding: 8px;
    border: 1px dashed var(--el-border-color);
    border-radius: 6px;
    background: var(--el-fill-color-light);
}
.sql-result:not(.pending) {
    border-style: solid;
    border-color: var(--el-color-primary-light-5);
    background: var(--el-fill-color-blank);
}
.sql-timing-wrap {
    margin-top: 12px;
}
.sql-timing-chart {
    height: 220px;
}
.sql-result-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
}
.sql-result-table {
    margin-top: 4px;
}
.sql-analysis {
    margin-top: 8px;
}
.sql-analysis ul {
    margin: 6px 0 0;
    padding-left: 18px;
}
.sql-analysis li + li {
    margin-top: 4px;
}
.sql-explain {
    margin-top: 8px;
}
.explain-pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12px;
    line-height: 1.45;
}
</style>
