<template>
    <el-card shadow="never" class="data-card">
        <template #header>
            <div class="card-header">
                <span>投诉样本管理 (insight_complaint_sample)</span>
                <div class="header-actions">
                    <el-button type="primary" @click="search">查询</el-button>
                    <el-button @click="resetQuery">重置</el-button>
                    <el-button type="primary" @click="openCreate">新增投诉</el-button>
                </div>
            </div>
        </template>

        <el-table :data="rows" v-loading="loading" border stripe class="filter-table">
            <el-table-column prop="complaint_id" label="流水号" width="150" />
            <el-table-column prop="user_id" width="120">
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.user_id" size="small" clearable @keyup.enter="search" />
                        <span>用户ID</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="name" label="姓名" width="90" show-overflow-tooltip />
            <el-table-column prop="gender" label="性别" width="70" />
            <el-table-column prop="msisdn" label="手机号" width="120" show-overflow-tooltip />
            <el-table-column prop="age" label="年龄" width="70" />
            <el-table-column prop="region" width="150" show-overflow-tooltip>
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.region" size="small" clearable @keyup.enter="search" />
                        <span>区域</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="plan_id" label="套餐" width="110" show-overflow-tooltip />
            <el-table-column prop="vip_level" label="VIP" width="80" />
            <el-table-column prop="channel" label="渠道" width="90" />
            <el-table-column prop="device_brand" label="终端" width="120" show-overflow-tooltip />
            <el-table-column prop="network_type" label="网络" width="70" />
            <el-table-column prop="monthly_fee" label="话费" width="80" />
            <el-table-column prop="join_date" label="入网日" width="110" />
            <el-table-column prop="contract_end" label="合约到期" width="110" />
            <el-table-column prop="fee_drift_rate" label="资费漂移" width="90" />
            <el-table-column label="时间" width="170" show-overflow-tooltip>
                <template #default="{ row }">{{ formatDateTime(row.sample_time) }}</template>
            </el-table-column>
            <el-table-column prop="complaint_type" width="200">
                <template #header>
                    <div class="th-filter">
                        <el-select v-model="query.category_key" size="small" clearable filterable class="th-select">
                            <el-option v-for="item in categories" :key="item.key" :label="item.label" :value="item.key" />
                        </el-select>
                        <span>分类</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="sub_category" label="小类" width="120" />
            <el-table-column prop="raw_text" min-width="200" show-overflow-tooltip>
                <template #header>
                    <div class="th-filter">
                        <el-input v-model="query.text" size="small" clearable @keyup.enter="search" />
                        <span>投诉正文</span>
                    </div>
                </template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                    <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
                    <el-button link type="danger" @click="remove(row)">删除</el-button>
                </template>
            </el-table-column>
        </el-table>

        <el-pagination class="pager" background layout="total, prev, pager, next" :total="page.total" :page-size="page.size" :current-page="page.index" @current-change="changePage" />

        <el-dialog v-model="visible" :title="editingId ? '编辑投诉' : '新增投诉'" width="780px" destroy-on-close>
            <el-form :model="form" label-width="96px">
                <el-row :gutter="12">
                    <el-col :span="12"><el-form-item label="用户ID"><el-input v-model="form.user_id" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="时间"><el-date-picker v-model="form.sample_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" /></el-form-item></el-col>
                    <el-col :span="24">
                        <el-form-item label="分类">
                            <el-select v-model="form.category_key" filterable>
                                <el-option v-for="item in categories" :key="item.key" :label="item.label" :value="item.key" />
                            </el-select>
                        </el-form-item>
                    </el-col>
                    <el-col :span="24"><el-form-item label="正文"><el-input v-model="form.raw_text" type="textarea" :rows="4" /></el-form-item></el-col>
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
import {
    createInsightComplaint,
    deleteInsightComplaint,
    getInsightComplaintCategories,
    getInsightComplaints,
    updateInsightComplaint,
} from '@/api';
import { formatDateTime } from '@/utils';

interface ComplaintRow {
    complaint_id: string;
    user_id: string;
    name?: string | null;
    gender?: string | null;
    msisdn?: string | null;
    age?: number | null;
    sample_time: string;
    complaint_type: string;
    sub_category: string;
    raw_text: string;
    complaint_vector?: number[] | null;
    region?: string | null;
    plan_id?: string | null;
    vip_level?: string | null;
    channel?: string | null;
    device_brand?: string | null;
    network_type?: string | null;
    monthly_fee?: number | null;
    contract_end?: string | null;
}
interface CategoryOption {
    key: string;
    label: string;
    main_category: string;
    sub_category: string;
}

const emit = defineEmits<{ refresh: [] }>();
const rows = ref<ComplaintRow[]>([]);
const categories = ref<CategoryOption[]>([]);
const loading = ref(false);
const saving = ref(false);
const visible = ref(false);
const editingId = ref<string | null>(null);
const page = reactive({ index: 1, size: 10, total: 0 });
const query = reactive({ user_id: '', region: '', category_key: '', text: '' });
const emptyForm = () => ({
    user_id: '10000001',
    sample_time: '',
    category_key: '',
    raw_text: '',
});
const form = reactive(emptyForm());

function selectedCategory(key: string) {
    return categories.value.find((item) => item.key === key);
}

function formatVector(vector?: number[] | null) {
    if (!vector?.length) return '-';
    const preview = vector.slice(0, 3).map((item) => Number(item).toFixed(4));
    return `[${preview.join(', ')}, ...] ${vector.length}维`;
}

function params() {
    const category = selectedCategory(query.category_key);
    return {
        user_id: query.user_id || undefined,
        region: query.region || undefined,
        main_category: category?.main_category,
        sub_category: category?.sub_category,
        text: query.text || undefined,
        page: page.index,
        page_size: page.size,
    };
}

async function loadCategories() {
    const { data } = await getInsightComplaintCategories();
    categories.value = data.map((item: Omit<CategoryOption, 'key' | 'label'>) => ({
        ...item,
        key: `${item.main_category}:${item.sub_category}`,
        label: `${item.main_category} / ${item.sub_category}`,
    }));
}

async function loadData() {
    loading.value = true;
    try {
        const { data } = await getInsightComplaints(params());
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
    Object.assign(query, { user_id: '', region: '', category_key: '', text: '' });
    search();
}

function changePage(val: number) {
    page.index = val;
    loadData();
}

function openCreate() {
    editingId.value = null;
    Object.assign(form, emptyForm(), { category_key: categories.value[0]?.key || '' });
    visible.value = true;
}

function openEdit(row: ComplaintRow) {
    editingId.value = row.complaint_id;
    const sampleTime = formatDateTime(row.sample_time);
    Object.assign(form, row, {
        category_key: `${row.complaint_type}:${row.sub_category}`,
        sample_time: sampleTime === '-' ? '' : sampleTime,
    });
    visible.value = true;
}

function payload() {
    const category = selectedCategory(form.category_key);
    return {
        user_id: form.user_id,
        sample_time: form.sample_time,
        complaint_type: category?.main_category,
        sub_category: category?.sub_category,
        raw_text: form.raw_text,
    };
}

async function save() {
    saving.value = true;
    try {
        if (editingId.value) await updateInsightComplaint(editingId.value, payload());
        else await createInsightComplaint(payload());
        ElMessage.success('保存成功');
        visible.value = false;
        emit('refresh');
        loadData();
    } finally {
        saving.value = false;
    }
}

async function remove(row: ComplaintRow) {
    await ElMessageBox.confirm(`确认删除投诉 ${row.complaint_id}？`, '删除确认', { type: 'warning' });
    await deleteInsightComplaint(row.complaint_id);
    ElMessage.success('删除成功');
    emit('refresh');
    loadData();
}

onMounted(async () => {
    await loadCategories();
    loadData();
});
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
.th-filter span {
    font-size: 12px;
    color: var(--el-text-color-regular);
    white-space: nowrap;
}
.th-filter :deep(.el-input),
.th-select {
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
</style>
