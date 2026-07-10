<template>
    <div class="risk-tab">
        <el-alert
            :title="t('pages.insight.risk.hint')"
            type="info"
            show-icon
            :closable="false"
            class="mgb20"
        />

        <el-form :model="query" inline class="query-form">
            <el-form-item :label="t('pages.insight.bi.snapshotDate')">
                <el-date-picker
                    v-model="query.snapshot_date"
                    type="date"
                    value-format="YYYY-MM-DD"
                    clearable
                    style="width: 150px"
                />
            </el-form-item>
            <el-form-item :label="t('pages.insight.profile.userId')">
                <el-input v-model="query.user_id" clearable style="width: 130px" />
            </el-form-item>
            <el-form-item :label="t('pages.insight.bi.regionL1')">
                <el-input v-model="query.region_l1" clearable style="width: 120px" />
            </el-form-item>
            <el-form-item :label="t('pages.insight.bi.regionL2')">
                <el-input v-model="query.region_l2" clearable style="width: 120px" />
            </el-form-item>
            <el-form-item :label="t('pages.insight.risk.riskLevel')">
                <el-select v-model="query.churn_risk_level" clearable style="width: 110px">
                    <el-option label="high" value="high" />
                    <el-option label="medium" value="medium" />
                    <el-option label="low" value="low" />
                </el-select>
            </el-form-item>
            <el-form-item>
                <el-button type="primary" @click="search">{{ t('common.search') }}</el-button>
                <el-button @click="resetQuery">重置</el-button>
            </el-form-item>
        </el-form>

        <el-table :data="rows" v-loading="loading" border stripe>
            <el-table-column prop="snapshot_date" :label="t('pages.insight.bi.snapshotDate')" width="120" />
            <el-table-column prop="user_id" :label="t('pages.insight.profile.userId')" width="110" />
            <el-table-column prop="region_l1" :label="t('pages.insight.bi.regionL1')" width="110" />
            <el-table-column prop="region_l2" :label="t('pages.insight.bi.regionL2')" width="120" />
            <el-table-column prop="vip_level" :label="t('pages.insight.profile.vip')" width="90" />
            <el-table-column :label="t('pages.insight.profile.riskScore')" width="150">
                <template #default="{ row }">
                    <span :class="riskClass(row.churn_risk_level)">
                        {{ Number(row.risk_score).toFixed(4) }} ({{ row.churn_risk_level }})
                    </span>
                </template>
            </el-table-column>
            <el-table-column prop="activity_trend" :label="t('pages.insight.risk.activityTrend')" width="110" />
            <el-table-column :label="t('pages.insight.profile.tags')" min-width="180">
                <template #default="{ row }">
                    <el-tag v-for="tag in row.tags || []" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
                    <span v-if="!row.tags?.length">-</span>
                </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
                <template #default="{ row }">
                    <el-button link type="primary" @click="emit('openProfile', row.user_id)">
                        {{ t('pages.insight.risk.viewProfile') }}
                    </el-button>
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
import { onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { getInsightSnapshots } from '@/api';

const emit = defineEmits<{ openProfile: [userId: string] }>();
const { t } = useI18n();

const query = reactive({
    snapshot_date: '',
    user_id: '',
    region_l1: '',
    region_l2: '',
    churn_risk_level: 'high',
});

const rows = ref<Record<string, unknown>[]>([]);
const loading = ref(false);
const page = reactive({ index: 1, size: 20, total: 0 });

function riskClass(level: string) {
    if (level === 'high') return 'risk-high';
    if (level === 'medium') return 'risk-medium';
    return '';
}

function buildParams() {
    const params: Record<string, unknown> = { page: page.index, page_size: page.size };
    for (const [key, value] of Object.entries(query)) {
        if (value) params[key] = value;
    }
    return params;
}

async function loadRows() {
    loading.value = true;
    try {
        const { data } = await getInsightSnapshots(buildParams());
        rows.value = data.list;
        page.total = data.pageTotal;
    } finally {
        loading.value = false;
    }
}

function search() {
    page.index = 1;
    loadRows();
}

function resetQuery() {
    query.snapshot_date = '';
    query.user_id = '';
    query.region_l1 = '';
    query.region_l2 = '';
    query.churn_risk_level = 'high';
    search();
}

function changePage(val: number) {
    page.index = val;
    loadRows();
}

onMounted(loadRows);
</script>

<style scoped>
.pager {
    justify-content: flex-end;
    margin-top: 16px;
}
.mgb20 {
    margin-bottom: 20px;
}
.tag-item {
    margin-right: 4px;
}
.risk-high {
    color: var(--el-color-danger);
    font-weight: 600;
}
.risk-medium {
    color: var(--el-color-warning);
}
</style>
