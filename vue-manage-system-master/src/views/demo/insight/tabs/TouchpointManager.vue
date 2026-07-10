<template>
    <el-card shadow="never" class="data-card">
        <template #header>
            <div class="card-header">
                <span>问卷投诉样本 (insight_complaint_sample)</span>
            </div>
        </template>

        <el-form :model="query" inline class="query-form">
            <el-form-item label="用户ID"><el-input v-model="query.user_id" clearable /></el-form-item>
            <el-form-item>
                <el-button type="primary" @click="search">查询</el-button>
                <el-button @click="resetQuery">重置</el-button>
            </el-form-item>
        </el-form>

        <el-table :data="rows" v-loading="loading" border stripe>
            <el-table-column prop="sample_id" label="样本ID" width="90" />
            <el-table-column prop="user_id" label="用户ID" width="110" />
            <el-table-column prop="record_date" label="日期" width="120" />
            <el-table-column label="问卷题数" width="90">
                <template #default="{ row }">
                    {{ row.survey_answers?.length || 0 }}
                </template>
            </el-table-column>
            <el-table-column prop="satisfaction_score" label="满意度均分" width="100" />
            <el-table-column label="10类得分" min-width="260" show-overflow-tooltip>
                <template #default="{ row }">
                    <span>{{ formatScores(row.survey_category_scores) }}</span>
                </template>
            </el-table-column>
            <el-table-column prop="complaint_id" label="投诉流水" width="150" show-overflow-tooltip />
            <el-table-column label="投诉分类" width="180" show-overflow-tooltip>
                <template #default="{ row }">
                    <span>{{ formatCategory(row) }}</span>
                </template>
            </el-table-column>
            <el-table-column prop="raw_text" label="投诉正文" min-width="260" show-overflow-tooltip />
            <el-table-column label="投诉向量" min-width="220" show-overflow-tooltip>
                <template #default="{ row }">
                    <span>{{ formatVector(row.complaint_vector) }}</span>
                </template>
            </el-table-column>
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

const rows = ref<SampleRow[]>([]);
const loading = ref(false);
const page = reactive({ index: 1, size: 10, total: 0 });
const query = reactive({ user_id: '' });

function params() {
    return { ...query, page: page.index, page_size: page.size };
}

function formatCategory(row: SampleRow) {
    if (!row.complaint_type && !row.sub_category) return '-';
    return [row.complaint_type, row.sub_category].filter(Boolean).join(' / ');
}

function formatVector(vector?: number[] | null) {
    if (!vector?.length) return '-';
    const preview = vector.slice(0, 3).map((item) => Number(item).toFixed(4));
    return `[${preview.join(', ')}, ...] ${vector.length}维`;
}

function formatScores(scores?: Record<string, number>) {
    if (!scores || !Object.keys(scores).length) return '-';
    return Object.entries(scores)
        .slice(0, 4)
        .map(([key, value]) => `${key}:${Number(value).toFixed(2)}`)
        .join(' / ');
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
    query.user_id = '';
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
.query-form {
    margin-bottom: 8px;
}
.pager {
    justify-content: flex-end;
    margin-top: 16px;
}
</style>
