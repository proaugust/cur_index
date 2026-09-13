<template>
    <el-card shadow="never" class="data-card">
        <template #header>
            <div class="card-header">
                <span>问卷投诉样本 (insight_complaint_sample)</span>
                <div class="header-actions">
                    <el-button type="primary" @click="search">查询</el-button>
                    <el-button @click="resetQuery">重置</el-button>
                </div>
            </div>
        </template>

        <el-table :data="rows" v-loading="loading" border stripe class="filter-table">
            <el-table-column prop="sample_id" width="100">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.sample_id" size="small" clearable @keyup.enter="search" />
                        <span>样本ID</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="user_id" width="120">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.user_id" size="small" clearable @keyup.enter="search" />
                        <span>用户ID</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="name" width="100" show-overflow-tooltip>
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.name" size="small" clearable @keyup.enter="search" />
                        <span>姓名</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="gender" width="80">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.gender" size="small" clearable @keyup.enter="search" />
                        <span>性别</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="msisdn" width="130" show-overflow-tooltip>
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.msisdn" size="small" clearable @keyup.enter="search" />
                        <span>手机号</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="age" width="80">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.age" size="small" clearable @keyup.enter="search" />
                        <span>年龄</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="region" width="150" show-overflow-tooltip>
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.region" size="small" clearable @keyup.enter="search" />
                        <span>地区</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="plan_id" width="120" show-overflow-tooltip>
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.plan_id" size="small" clearable @keyup.enter="search" />
                        <span>套餐</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="vip_level" width="90">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.vip_level" size="small" clearable @keyup.enter="search" />
                        <span>VIP</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="channel" width="100">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.channel" size="small" clearable @keyup.enter="search" />
                        <span>渠道</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="device_brand" width="130" show-overflow-tooltip>
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.device_brand" size="small" clearable @keyup.enter="search" />
                        <span>终端</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="network_type" width="80">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.network_type" size="small" clearable @keyup.enter="search" />
                        <span>网络</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="monthly_fee" width="90">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.monthly_fee" size="small" clearable @keyup.enter="search" />
                        <span>话费</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="join_date" width="140">
                <template #header>
                    <div class="th-filter">
                        <el-date-picker
                            v-model="query.join_date"
                            type="date"
                            size="small"
                            value-format="YYYY-MM-DD"
                            clearable
                            class="th-date"
                        />
                        <span>入网日</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="contract_end" width="140">
                <template #header>
                    <div class="th-filter">
                        <el-date-picker
                            v-model="query.contract_end"
                            type="date"
                            size="small"
                            value-format="YYYY-MM-DD"
                            clearable
                            class="th-date"
                        />
                        <span>合约到期</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="fee_drift_rate" width="100">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.fee_drift_rate" size="small" clearable @keyup.enter="search" />
                        <span>资费漂移</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="satisfaction_net" width="100">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.satisfaction_net" size="small" clearable @keyup.enter="search" />
                        <span>网络满意</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="satisfaction_srv" width="100">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.satisfaction_srv" size="small" clearable @keyup.enter="search" />
                        <span>服务满意</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="record_date" width="160">
                <template #header>
                    <div class="th-filter th-filter-dates">
                        <el-date-picker
                            v-model="query.date_from"
                            type="date"
                            size="small"
                            value-format="YYYY-MM-DD"
                            placeholder="起"
                            clearable
                            class="th-date"
                        />
                        <el-date-picker
                            v-model="query.date_to"
                            type="date"
                            size="small"
                            value-format="YYYY-MM-DD"
                            placeholder="止"
                            clearable
                            class="th-date"
                        />
                        <span>日期</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column label="问卷题数" width="90">
                <template #default="{ row }">
                    {{ row.survey_answers?.length || 0 }}
                </template>
            </el-table-column>
            <el-table-column prop="satisfaction_score" width="110">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.satisfaction_score" size="small" clearable @keyup.enter="search" />
                        <span>满意度均分</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column label="10类得分" min-width="260">
                <template #default="{ row }">
                    <el-popover
                        v-if="hasScores(row.survey_category_scores)"
                        :visible="isScoreExpanded(row.sample_id)"
                        placement="left"
                        :width="520"
                        trigger="manual"
                    >
                        <template #reference>
                            <div
                                class="score-cell"
                                @click.stop="toggleScoreExpand(row.sample_id)"
                            >
                                <div
                                    v-for="(line, idx) in scorePreviewLines(row.survey_category_scores)"
                                    :key="idx"
                                    class="score-preview-line"
                                >
                                    {{ line }}
                                </div>
                            </div>
                        </template>
                        <div class="score-grid" @click.stop>
                            <span
                                v-for="[key, value] in scoreEntries(row.survey_category_scores)"
                                :key="key"
                                class="score-item"
                            >
                                {{ scoreLabel(key) }}：{{ Number(value).toFixed(2) }}
                            </span>
                        </div>
                    </el-popover>
                    <span v-else>-</span>
                </template>
            </el-table-column>
            <el-table-column prop="complaint_id" label="投诉流水" width="150" show-overflow-tooltip />
            <el-table-column label="投诉分类" width="160" show-overflow-tooltip>
                <template #default="{ row }">
                    <span>{{ formatCategory(row) }}</span>
                </template>
            </el-table-column>
            <el-table-column prop="raw_text" label="投诉正文" min-width="200" show-overflow-tooltip />
        </el-table>

        <el-pagination class="pager" background layout="total, prev, pager, next" :total="page.total" :page-size="page.size" :current-page="page.index" @current-change="changePage" />
    </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { getInsightSamples } from '@/api';

interface SampleRow {
    sample_id: number;
    user_id: string;
    name?: string | null;
    gender?: string | null;
    msisdn?: string | null;
    age?: number | null;
    region?: string | null;
    plan_id?: string | null;
    vip_level?: string | null;
    channel?: string | null;
    device_brand?: string | null;
    network_type?: string | null;
    monthly_fee?: number | null;
    join_date?: string | null;
    contract_end?: string | null;
    fee_drift_rate?: number | null;
    satisfaction_net?: number | null;
    satisfaction_srv?: number | null;
    record_date: string;
    survey_answers: Array<Record<string, unknown>>;
    survey_category_scores: Record<string, number>;
    satisfaction_score: number;
    complaint_id?: string | null;
    sample_time?: string | null;
    complaint_type?: string | null;
    sub_category?: string | null;
    raw_text?: string | null;
    complaint_vector?: number[] | null;
}

const emptyQuery = () => ({
    sample_id: '',
    user_id: '',
    name: '',
    gender: '',
    msisdn: '',
    age: '',
    region: '',
    plan_id: '',
    vip_level: '',
    channel: '',
    device_brand: '',
    network_type: '',
    monthly_fee: '',
    join_date: '',
    contract_end: '',
    fee_drift_rate: '',
    satisfaction_net: '',
    satisfaction_srv: '',
    date_from: '',
    date_to: '',
    satisfaction_score: '',
});

const SCORE_LABELS: Record<string, string> = {
    network_quality: '网络质量',
    billing_fee: '资费账单',
    customer_service: '客服服务',
    package_value: '套餐价值',
    app_experience: 'App体验',
    shop_experience: '门店体验',
    device_service: '终端服务',
    roaming_service: '漫游服务',
    privacy_security: '隐私安全',
    loyalty_retention: '忠诚留存',
};

const rows = ref<SampleRow[]>([]);
const loading = ref(false);
const page = reactive({ index: 1, size: 10, total: 0 });
const query = reactive(emptyQuery());
const expandedScoreIds = ref<Set<number>>(new Set());

function toNumber(value: string) {
    const trimmed = value.trim();
    if (!trimmed) return undefined;
    const n = Number(trimmed);
    return Number.isFinite(n) ? n : undefined;
}

function params() {
    return {
        sample_id: toNumber(query.sample_id),
        user_id: query.user_id || undefined,
        name: query.name || undefined,
        gender: query.gender || undefined,
        msisdn: query.msisdn || undefined,
        age: toNumber(query.age),
        region: query.region || undefined,
        plan_id: query.plan_id || undefined,
        vip_level: query.vip_level || undefined,
        channel: query.channel || undefined,
        device_brand: query.device_brand || undefined,
        network_type: query.network_type || undefined,
        monthly_fee: toNumber(query.monthly_fee),
        join_date: query.join_date || undefined,
        contract_end: query.contract_end || undefined,
        fee_drift_rate: toNumber(query.fee_drift_rate),
        satisfaction_net: toNumber(query.satisfaction_net),
        satisfaction_srv: toNumber(query.satisfaction_srv),
        date_from: query.date_from || undefined,
        date_to: query.date_to || undefined,
        satisfaction_score: toNumber(query.satisfaction_score),
        page: page.index,
        page_size: page.size,
    };
}

function formatCategory(row: SampleRow) {
    if (!row.complaint_type && !row.sub_category) return '-';
    return [row.complaint_type, row.sub_category].filter(Boolean).join(' / ');
}

function hasScores(scores?: Record<string, number>) {
    return !!scores && Object.keys(scores).length > 0;
}

function scoreEntries(scores: Record<string, number>) {
    return Object.entries(scores);
}

function scoreLabel(key: string) {
    return SCORE_LABELS[key] || key;
}

function isScoreExpanded(sampleId: number) {
    return expandedScoreIds.value.has(sampleId);
}

function setScoreExpand(sampleId: number, visible: boolean) {
    const next = new Set(expandedScoreIds.value);
    if (visible) next.add(sampleId);
    else next.delete(sampleId);
    expandedScoreIds.value = next;
}

function toggleScoreExpand(sampleId: number) {
    setScoreExpand(sampleId, !isScoreExpanded(sampleId));
}

function scorePreviewLines(scores: Record<string, number>) {
    const entries = Object.entries(scores);
    const mid = Math.ceil(entries.length / 2);
    const fmt = (list: [string, number][]) =>
        list.map(([key, value]) => `${scoreLabel(key)}:${Number(value).toFixed(1)}`).join(' / ');
    return [fmt(entries.slice(0, mid)), fmt(entries.slice(mid))].filter(Boolean);
}

async function loadData() {
    loading.value = true;
    try {
        const { data } = await getInsightSamples(params());
        rows.value = data.list;
        page.total = data.pageTotal;
    } finally {
        loading.value = false;
    }
}

function search() {
    page.index = 1;
    loadData();
}

function resetQuery() {
    Object.assign(query, emptyQuery());
    search();
}

function changePage(val: number) {
    page.index = val;
    loadData();
}

onMounted(loadData);
</script>

<style scoped>
.data-card {
    margin-top: 16px;
}
.card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.header-actions {
    display: flex;
    gap: 8px;
}
.th-filter {
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    gap: 6px;
    line-height: 1.2;
    min-height: 52px;
}
.th-filter-dates {
    min-height: 84px;
}
.th-filter span {
    font-size: 12px;
    color: var(--el-text-color-regular);
    white-space: nowrap;
}
.th-filter :deep(.el-input),
.th-date {
    width: 100%;
}
.filter-table :deep(.el-table__header th) {
    vertical-align: bottom;
}
.filter-table :deep(.el-table__header .cell) {
    padding: 6px 4px;
}
.pager {
    justify-content: flex-end;
    margin-top: 16px;
}
.score-cell {
    cursor: pointer;
    color: var(--el-color-primary);
    line-height: 1.35;
    user-select: none;
}
.score-preview-line {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.score-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    grid-template-rows: auto auto;
    gap: 6px 10px;
}
.score-item {
    white-space: nowrap;
    font-size: 13px;
}
</style>
