<template>
    <el-card shadow="never" class="data-card">
        <template #header>
            <div class="card-header">
                <span>用户画像管理 (insight_user_profile)</span>
                <div class="header-actions">
                    <el-button type="primary" @click="search">查询</el-button>
                    <el-button @click="resetQuery">重置</el-button>
                    <el-button type="primary" @click="openCreate">新增用户</el-button>
                </div>
            </div>
        </template>

        <el-table :data="rows" v-loading="loading" border stripe class="filter-table">
            <el-table-column prop="user_id" width="120" fixed>
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.user_id" size="small" clearable @keyup.enter="search" />
                        <span>用户ID</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="name" width="100">
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
            <el-table-column prop="age" width="70">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.age" size="small" clearable @keyup.enter="search" />
                        <span>年龄</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="age_group" width="100">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.age_group" size="small" clearable @keyup.enter="search" />
                        <span>年龄段</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="region_l1" width="100" show-overflow-tooltip>
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.region_l1" size="small" clearable @keyup.enter="search" />
                        <span>省/都道府</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="region_l2" width="100" show-overflow-tooltip>
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.region_l2" size="small" clearable @keyup.enter="search" />
                        <span>市/区</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="region" min-width="150" show-overflow-tooltip>
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.region" size="small" clearable @keyup.enter="search" />
                        <span>区域</span>
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
            <el-table-column prop="channel" width="110">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.channel" size="small" clearable @keyup.enter="search" />
                        <span>入网渠道</span>
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
            <el-table-column prop="join_date" width="130">
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
            <el-table-column prop="contract_end" width="130">
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
            <el-table-column prop="monthly_fee" width="90">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.monthly_fee" size="small" clearable @keyup.enter="search" />
                        <span>月消费</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="fee_drift_rate" width="90">
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
                <template #default="{ row }">{{ row.satisfaction_net ?? '-' }}</template>
            </el-table-column>
            <el-table-column prop="satisfaction_srv" width="100">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.satisfaction_srv" size="small" clearable @keyup.enter="search" />
                        <span>服务满意</span>
                    </div>
                </template>
                <template #default="{ row }">{{ row.satisfaction_srv ?? '-' }}</template>
            </el-table-column>
            <el-table-column prop="sample_satisfaction" width="110">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.sample_satisfaction" size="small" clearable @keyup.enter="search" />
                        <span>样本满意度</span>
                    </div>
                </template>
                <template #default="{ row }">{{ row.sample_satisfaction ?? '-' }}</template>
            </el-table-column>
            <el-table-column prop="pred_satisfaction" width="110">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.pred_satisfaction" size="small" clearable @keyup.enter="search" />
                        <span>预测满意度</span>
                    </div>
                </template>
                <template #default="{ row }">{{ row.pred_satisfaction ?? '-' }}</template>
            </el-table-column>
            <el-table-column width="100">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.sample_id" size="small" clearable @keyup.enter="search" />
                        <span>样本ID</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="sample_count" label="样本数" width="80" align="right">
                <template #default="{ row }">{{ row.sample_count ?? 0 }}</template>
            </el-table-column>
            <el-table-column prop="complaint_count" label="投诉数" width="80" align="right">
                <template #default="{ row }">{{ row.complaint_count ?? 0 }}</template>
            </el-table-column>
            <el-table-column prop="risk_score" label="风险分" width="90">
                <template #default="{ row }">{{ row.risk_score ?? '-' }}</template>
            </el-table-column>
            <el-table-column prop="risk_level" width="100">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.risk_level" size="small" clearable @keyup.enter="search" />
                        <span>风险等级</span>
                    </div>
                </template>
                <template #default="{ row }">{{ row.risk_level || '-' }}</template>
            </el-table-column>
            <el-table-column prop="tags" label="标签" min-width="160">
                <template #default="{ row }">
                    <el-tag v-for="tag in row.tags || []" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
                    <span v-if="!row.tags?.length">-</span>
                </template>
            </el-table-column>
            <el-table-column label="SHAP" min-width="160" show-overflow-tooltip>
                <template #default="{ row }">{{ formatShap(row.shap_values) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
                <template #default="{ row }">
                    <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
                    <el-button link type="danger" @click="remove(row)">删除</el-button>
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

        <el-dialog v-model="visible" :title="editingId ? '编辑用户' : '新增用户'" width="760px" destroy-on-close>
            <el-form :model="form" label-width="110px">
                <el-row :gutter="12">
                    <el-col :span="12" v-if="!editingId"><el-form-item label="用户ID"><el-input v-model="form.user_id" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="性别"><el-input v-model="form.gender" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="手机号"><el-input v-model="form.msisdn" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="年龄"><el-input-number v-model="form.age" :min="0" :max="120" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="年龄段"><el-input v-model="form.age_group" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="省/都道府"><el-input v-model="form.region_l1" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="市/区"><el-input v-model="form.region_l2" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="区域"><el-input v-model="form.region" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="套餐"><el-input v-model="form.plan_id" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="VIP"><el-input v-model="form.vip_level" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="入网渠道"><el-input v-model="form.channel" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="终端"><el-input v-model="form.device_brand" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="网络"><el-input v-model="form.network_type" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="入网日期"><el-date-picker v-model="form.join_date" value-format="YYYY-MM-DD" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="合约到期"><el-date-picker v-model="form.contract_end" value-format="YYYY-MM-DD" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="月消费"><el-input-number v-model="form.monthly_fee" :min="0" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="资费漂移"><el-input-number v-model="form.fee_drift_rate" :step="0.01" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="网络满意度"><el-input-number v-model="form.satisfaction_net" :min="1" :max="5" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="客服满意度"><el-input-number v-model="form.satisfaction_srv" :min="1" :max="5" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="样本满意度"><el-input-number v-model="form.sample_satisfaction" :min="0" :max="5" :step="0.1" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="预测满意度"><el-input-number v-model="form.pred_satisfaction" :min="0" :max="5" :step="0.1" /></el-form-item></el-col>
                </el-row>
            </el-form>
            <template #footer>
                <el-button @click="visible = false">取消</el-button>
                <el-button type="primary" :loading="saving" @click="save">保存</el-button>
            </template>
        </el-dialog>
    </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { createInsightUser, deleteInsightUser, getInsightUsers, updateInsightUser } from '@/api';

interface UserRow {
    user_id: string;
    name: string;
    gender?: string | null;
    msisdn?: string | null;
    age: number;
    age_group: string;
    region_l1?: string;
    region_l2?: string;
    region: string;
    plan_id: string;
    channel?: string | null;
    device_brand?: string | null;
    network_type?: string | null;
    monthly_fee: number | string;
    fee_drift_rate?: number | string | null;
    vip_level: string;
    join_date: string;
    contract_end?: string | null;
    satisfaction_net?: number | null;
    satisfaction_srv?: number | null;
    sample_satisfaction?: number | string | null;
    pred_satisfaction?: number | string | null;
    sample_count?: number;
    complaint_count?: number;
    risk_score?: number | string;
    risk_level?: string;
    tags?: string[];
    shap_values?: Record<string, unknown> | null;
}

const emit = defineEmits<{ refresh: [] }>();
const rows = ref<UserRow[]>([]);
const loading = ref(false);
const saving = ref(false);
const visible = ref(false);
const editingId = ref<string | null>(null);
const page = reactive({ index: 1, size: 10, total: 0 });
const emptyQuery = () => ({
    user_id: '',
    name: '',
    gender: '',
    msisdn: '',
    age: '',
    region: '',
    region_l1: '',
    region_l2: '',
    age_group: '',
    plan_id: '',
    vip_level: '',
    channel: '',
    device_brand: '',
    network_type: '',
    join_date: '',
    contract_end: '',
    monthly_fee: '',
    fee_drift_rate: '',
    sample_id: '',
    satisfaction_net: '',
    satisfaction_srv: '',
    sample_satisfaction: '',
    pred_satisfaction: '',
    risk_level: '',
});
const query = reactive(emptyQuery());
const emptyForm = (): UserRow => ({
    user_id: '',
    name: '',
    gender: '男',
    msisdn: '',
    age: 30,
    age_group: '26-35',
    region_l1: '',
    region_l2: '',
    region: '',
    plan_id: '199元套餐',
    channel: '线上APP',
    device_brand: '',
    network_type: '5G',
    monthly_fee: 199,
    fee_drift_rate: 0,
    vip_level: '普通',
    join_date: '',
    contract_end: '',
    satisfaction_net: 3,
    satisfaction_srv: 3,
    sample_satisfaction: null,
    pred_satisfaction: null,
});
const form = reactive(emptyForm());

function formatShap(values?: Record<string, unknown> | null) {
    if (!values || !Object.keys(values).length) return '-';
    return Object.entries(values)
        .map(([k, v]) => `${k}:${v}`)
        .join(', ');
}

function toNumber(value: string) {
    const trimmed = value.trim();
    if (!trimmed) return undefined;
    const n = Number(trimmed);
    return Number.isFinite(n) ? n : undefined;
}

function params() {
    return {
        user_id: query.user_id || undefined,
        name: query.name || undefined,
        gender: query.gender || undefined,
        msisdn: query.msisdn || undefined,
        age: toNumber(query.age),
        region: query.region || undefined,
        region_l1: query.region_l1 || undefined,
        region_l2: query.region_l2 || undefined,
        age_group: query.age_group || undefined,
        plan_id: query.plan_id || undefined,
        vip_level: query.vip_level || undefined,
        channel: query.channel || undefined,
        device_brand: query.device_brand || undefined,
        network_type: query.network_type || undefined,
        join_date: query.join_date || undefined,
        contract_end: query.contract_end || undefined,
        monthly_fee: toNumber(query.monthly_fee),
        fee_drift_rate: toNumber(query.fee_drift_rate),
        sample_id: toNumber(query.sample_id),
        satisfaction_net: toNumber(query.satisfaction_net),
        satisfaction_srv: toNumber(query.satisfaction_srv),
        sample_satisfaction: toNumber(query.sample_satisfaction),
        pred_satisfaction: toNumber(query.pred_satisfaction),
        risk_level: query.risk_level || undefined,
        page: page.index,
        page_size: page.size,
    };
}

async function loadData() {
    loading.value = true;
    try {
        const { data } = await getInsightUsers(params());
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

function openCreate() {
    editingId.value = null;
    Object.assign(form, emptyForm());
    visible.value = true;
}

function openEdit(row: UserRow) {
    editingId.value = row.user_id;
    Object.assign(form, row, {
        monthly_fee: Number(row.monthly_fee),
        fee_drift_rate: row.fee_drift_rate == null ? 0 : Number(row.fee_drift_rate),
        sample_satisfaction: row.sample_satisfaction == null ? null : Number(row.sample_satisfaction),
        pred_satisfaction: row.pred_satisfaction == null ? null : Number(row.pred_satisfaction),
    });
    visible.value = true;
}

async function save() {
    saving.value = true;
    try {
        if (editingId.value) await updateInsightUser(editingId.value, form);
        else await createInsightUser(form);
        ElMessage.success('保存成功');
        visible.value = false;
        emit('refresh');
        loadData();
    } finally {
        saving.value = false;
    }
}

async function remove(row: UserRow) {
    await ElMessageBox.confirm(`确认删除用户 ${row.user_id}？关联投诉与触点也会删除。`, '删除确认', { type: 'warning' });
    await deleteInsightUser(row.user_id);
    ElMessage.success('删除成功');
    emit('refresh');
    loadData();
}

onMounted(loadData);
</script>

<style scoped>
.data-card {
    margin-top: 20px;
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
.th-filter span {
    font-size: 12px;
    color: var(--el-text-color-regular);
    white-space: nowrap;
}
.th-filter :deep(.el-input) {
    width: 100%;
}
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
.tag-item {
    margin-right: 4px;
}
</style>
