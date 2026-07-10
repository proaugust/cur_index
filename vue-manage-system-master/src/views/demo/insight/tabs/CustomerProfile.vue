<template>
    <div class="profile-tab">
        <el-alert :title="t('pages.insight.profile.hint')" type="info" show-icon :closable="false" class="mgb16" />

        <el-row :gutter="16">
            <el-col :xs="24" :lg="10">
                <el-card shadow="never" class="list-card">
                    <template #header>{{ t('pages.insight.profile.listTitle') }}</template>
                    <el-form :model="query" inline class="query-form" @submit.prevent="searchUsers">
                        <el-form-item :label="t('pages.insight.profile.userId')">
                            <el-input v-model="query.user_id" clearable style="width: 110px" />
                        </el-form-item>
                        <el-form-item :label="t('pages.insight.profile.region')">
                            <el-input v-model="query.region" clearable style="width: 110px" />
                        </el-form-item>
                        <el-form-item :label="t('pages.insight.profile.hasSample')">
                            <el-select v-model="query.has_sample" style="width: 110px">
                                <el-option :label="t('pages.insight.profile.hasSampleYes')" :value="true" />
                                <el-option :label="t('pages.insight.profile.hasSampleAll')" value="" />
                                <el-option :label="t('pages.insight.profile.hasSampleNo')" :value="false" />
                            </el-select>
                        </el-form-item>
                        <el-form-item>
                            <el-button type="primary" @click="searchUsers">{{ t('common.search') }}</el-button>
                            <el-button @click="resetQuery">{{ t('common.reset') }}</el-button>
                        </el-form-item>
                    </el-form>

                    <el-table
                        :data="rows"
                        v-loading="listLoading"
                        border
                        stripe
                        highlight-current-row
                        :row-class-name="rowClassName"
                        @row-click="selectUser"
                    >
                        <el-table-column prop="user_id" :label="t('pages.insight.profile.userId')" width="100" />
                        <el-table-column prop="name" :label="t('pages.insight.profile.name')" width="80" />
                        <el-table-column prop="region" :label="t('pages.insight.profile.region')" min-width="110" show-overflow-tooltip />
                        <el-table-column :label="t('pages.insight.profile.sampleCount')" width="72" align="right">
                            <template #default="{ row }">{{ row.sample_count ?? 0 }}</template>
                        </el-table-column>
                        <el-table-column :label="t('pages.insight.profile.riskScore')" width="100">
                            <template #default="{ row }">{{ formatRisk(row.risk_score, row.risk_level) }}</template>
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
                </el-card>
            </el-col>

            <el-col :xs="24" :lg="14">
                <el-empty v-if="!selectedUserId" :description="t('pages.insight.profile.selectHint')" :image-size="72" />
                <template v-else>
                    <div class="cache-bar mgb12" v-if="profile">
                        <el-tag :type="profile.cache.hit ? 'success' : 'info'" size="small">
                            {{ profile.cache.hit ? t('pages.insight.profile.cacheHit') : t('pages.insight.profile.cacheMiss') }}
                        </el-tag>
                        <el-tag type="warning" size="small" v-if="profile.cache.hot">{{ t('pages.insight.profile.hot') }}</el-tag>
                        <span class="cache-source">{{ t('pages.insight.profile.source') }}: {{ profile.cache.source }}</span>
                    </div>

                    <div v-loading="detailLoading">
                        <template v-if="profile">
                            <el-row :gutter="12" class="mgb12">
                                <el-col :span="12">
                                    <el-card shadow="hover">
                                        <template #header>{{ t('pages.insight.profile.basic') }}</template>
                                        <el-descriptions :column="1" border size="small">
                                            <el-descriptions-item label="ID">{{ profile.profile.user_id }}</el-descriptions-item>
                                            <el-descriptions-item :label="t('pages.insight.profile.name')">{{ profile.profile.name }}</el-descriptions-item>
                                            <el-descriptions-item :label="t('pages.insight.profile.age')">
                                                {{ profile.profile.age }} ({{ profile.profile.age_group }})
                                            </el-descriptions-item>
                                            <el-descriptions-item :label="t('pages.insight.profile.region')">{{ profile.profile.region }}</el-descriptions-item>
                                            <el-descriptions-item :label="t('pages.insight.profile.package')">{{ profile.profile.plan_id }}</el-descriptions-item>
                                            <el-descriptions-item :label="t('pages.insight.profile.vip')">{{ profile.profile.vip_level }}</el-descriptions-item>
                                            <el-descriptions-item :label="t('pages.insight.profile.tags')">
                                                <el-tag v-for="tag in profile.profile.tags || []" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
                                                <span v-if="!profile.profile.tags?.length">-</span>
                                            </el-descriptions-item>
                                        </el-descriptions>
                                    </el-card>
                                </el-col>
                                <el-col :span="12">
                                    <el-card shadow="hover" class="mgb12">
                                        <template #header>{{ t('pages.insight.profile.stats') }}</template>
                                        <el-row :gutter="8">
                                            <el-col :span="12">
                                                <el-statistic :title="t('pages.insight.status.complaints')" :value="profile.stats.complaint_total" />
                                            </el-col>
                                            <el-col :span="12">
                                                <el-statistic :title="t('pages.insight.status.samples')" :value="profile.stats.sample_total" />
                                            </el-col>
                                        </el-row>
                                    </el-card>
                                    <el-card shadow="hover">
                                        <template #header>{{ t('pages.insight.profile.risk') }}</template>
                                        <el-alert
                                            v-if="!profile.snapshot"
                                            :title="t('pages.insight.profile.noRisk')"
                                            type="warning"
                                            show-icon
                                            :closable="false"
                                            class="mgb12"
                                        />
                                        <el-descriptions :column="1" border size="small">
                                            <el-descriptions-item :label="t('pages.insight.profile.riskScore')">
                                                {{ formatRisk(profile.profile.risk_score, profile.profile.risk_level) }}
                                            </el-descriptions-item>
                                            <el-descriptions-item :label="t('pages.insight.risk.activityTrend')">
                                                {{ profile.snapshot?.activity_trend || '-' }}
                                            </el-descriptions-item>
                                            <el-descriptions-item :label="t('pages.insight.profile.shap')">
                                                <div v-if="shapItems.length" class="shap-list">
                                                    <div v-for="item in shapItems" :key="item.name" class="shap-row">
                                                        <span class="shap-name">{{ item.name }}</span>
                                                        <el-progress
                                                            :percentage="item.pct"
                                                            :color="item.value >= 0 ? '#f56c6c' : '#67c23a'"
                                                            :stroke-width="10"
                                                            :show-text="false"
                                                        />
                                                        <span class="shap-val" :class="item.value >= 0 ? 'up' : 'down'">
                                                            {{ item.value >= 0 ? '+' : '' }}{{ item.value.toFixed(4) }}
                                                        </span>
                                                    </div>
                                                    <div v-if="isInferredShap" class="shap-note">{{ t('pages.insight.profile.shapInferred') }}</div>
                                                </div>
                                                <span v-else>-</span>
                                            </el-descriptions-item>
                                        </el-descriptions>
                                    </el-card>
                                </el-col>
                            </el-row>

                            <el-card shadow="hover">
                                <template #header>{{ t('pages.insight.profile.flowTitle') }}</template>
                                <el-table :data="flowRows" stripe size="small" :empty-text="t('pages.insight.profile.flowEmpty')">
                                    <el-table-column prop="time" :label="t('pages.complaints.colTime')" width="160" />
                                    <el-table-column prop="kind" :label="t('pages.insight.profile.flowKind')" width="80" />
                                    <el-table-column prop="category" :label="t('pages.complaints.colCategory')" width="140" show-overflow-tooltip />
                                    <el-table-column prop="score" :label="t('pages.insight.profile.avgScore')" width="90" />
                                    <el-table-column prop="content" :label="t('pages.complaints.colContent')" min-width="180" show-overflow-tooltip />
                                </el-table>
                            </el-card>
                        </template>
                    </div>
                </template>
            </el-col>
        </el-row>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { getInsightUserProfile, getInsightUsers } from '@/api';

const props = defineProps<{ initialUserId?: string }>();
const { t } = useI18n();

const rows = ref<Record<string, any>[]>([]);
const listLoading = ref(false);
const detailLoading = ref(false);
const selectedUserId = ref('');
const profile = ref<Record<string, any> | null>(null);
const page = reactive({ index: 1, size: 10, total: 0 });
const query = reactive<{ user_id: string; region: string; has_sample: boolean | '' }>({
    user_id: '',
    region: '',
    has_sample: true,
});

const shapItems = computed(() => {
    const raw = profile.value?.profile?.shap_values || {};
    const entries = Object.entries(raw).map(([name, value]) => ({ name, value: Number(value) }));
    if (!entries.length) return [];
    const maxAbs = Math.max(...entries.map((item) => Math.abs(item.value)), 0.001);
    return entries
        .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
        .slice(0, 8)
        .map((item) => ({ ...item, pct: Math.round((Math.abs(item.value) / maxAbs) * 100) }));
});
const isInferredShap = computed(() =>
    (profile.value?.profile?.tags || []).some((tag: string) => tag.startsWith('沉默客户')),
);
const flowRows = computed(() => {
    const samples = profile.value?.recent_samples || profile.value?.recent_touchpoints || [];
    return samples.map((row: Record<string, any>) => ({
        time: row.sample_time || row.record_date || '-',
        kind: row.complaint_id ? t('pages.insight.profile.flowComplaint') : t('pages.insight.profile.flowSurvey'),
        category: [row.complaint_type, row.sub_category].filter(Boolean).join(' / ') || '-',
        score: row.satisfaction_score ?? '-',
        content: row.raw_text || '-',
    }));
});

function formatRisk(score: unknown, level: unknown) {
    if (score === null || score === undefined || score === '') return '-';
    return `${Number(score).toFixed(4)}${level ? ` (${level})` : ''}`;
}

function rowClassName({ row }: { row: Record<string, any> }) {
    return row.user_id === selectedUserId.value ? 'is-selected' : '';
}

async function loadUsers() {
    listLoading.value = true;
    try {
        const params: Record<string, unknown> = { page: page.index, page_size: page.size };
        if (query.user_id) params.user_id = query.user_id;
        if (query.region) params.region = query.region;
        if (query.has_sample !== '') params.has_sample = query.has_sample;
        const { data } = await getInsightUsers(params);
        rows.value = data.list;
        page.total = data.pageTotal;
        if (!selectedUserId.value && rows.value.length) {
            await loadProfile(rows.value[0].user_id);
        }
    } finally {
        listLoading.value = false;
    }
}

async function loadProfile(userId: string) {
    selectedUserId.value = userId;
    detailLoading.value = true;
    try {
        const { data } = await getInsightUserProfile(userId);
        profile.value = data;
    } catch (e: any) {
        profile.value = null;
        ElMessage.error(e?.response?.data?.detail || t('pages.insight.profile.loadFailed'));
    } finally {
        detailLoading.value = false;
    }
}

function selectUser(row: Record<string, any>) {
    if (!row?.user_id) return;
    loadProfile(row.user_id);
}

function searchUsers() {
    page.index = 1;
    loadUsers();
}

function resetQuery() {
    query.user_id = '';
    query.region = '';
    query.has_sample = true;
    searchUsers();
}

function changePage(val: number) {
    page.index = val;
    loadUsers();
}

watch(
    () => props.initialUserId,
    (val) => {
        if (val?.trim()) loadProfile(val.trim());
    },
);

onMounted(async () => {
    await loadUsers();
    if (props.initialUserId?.trim()) {
        await loadProfile(props.initialUserId.trim());
    }
});
</script>

<style scoped>
.mgb16 { margin-bottom: 16px; }
.mgb12 { margin-bottom: 12px; }
.query-form { margin-bottom: 8px; }
.pager { justify-content: flex-end; margin-top: 12px; }
.cache-bar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cache-source { color: var(--el-text-color-secondary); font-size: 12px; }
.tag-item { margin-right: 4px; }
.shap-list { width: 100%; }
.shap-row {
    display: grid;
    grid-template-columns: 72px 1fr 64px;
    gap: 6px;
    align-items: center;
    margin-bottom: 6px;
}
.shap-name { font-size: 12px; color: var(--el-text-color-secondary); }
.shap-val { font-size: 12px; text-align: right; }
.shap-val.up { color: var(--el-color-danger); }
.shap-val.down { color: var(--el-color-success); }
.shap-note { margin-top: 6px; font-size: 12px; color: var(--el-text-color-secondary); }
:deep(.is-selected) { --el-table-tr-bg-color: var(--el-color-primary-light-9); }
</style>
