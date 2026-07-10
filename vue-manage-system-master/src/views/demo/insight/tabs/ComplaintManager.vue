<template>
    <el-card shadow="never" class="data-card">
        <template #header>
            <div class="card-header">
                <span>投诉样本管理 (insight_complaint_sample)</span>
                <el-button type="primary" @click="openCreate">新增投诉</el-button>
            </div>
        </template>

        <el-form :model="query" inline class="query-form">
            <el-form-item label="用户ID"><el-input v-model="query.user_id" clearable /></el-form-item>
            <el-form-item label="区域"><el-input v-model="query.region" clearable /></el-form-item>
            <el-form-item label="分类">
                <el-select v-model="query.category_key" clearable filterable>
                    <el-option v-for="item in categories" :key="item.key" :label="item.label" :value="item.key" />
                </el-select>
            </el-form-item>
            <el-form-item label="正文"><el-input v-model="query.text" clearable /></el-form-item>
            <el-form-item>
                <el-button type="primary" @click="search">查询</el-button>
                <el-button @click="resetQuery">重置</el-button>
            </el-form-item>
        </el-form>

        <el-table :data="rows" v-loading="loading" border stripe>
            <el-table-column prop="complaint_id" label="流水号" width="150" />
            <el-table-column prop="user_id" label="用户ID" width="110" />
            <el-table-column prop="region" label="区域" width="140" show-overflow-tooltip />
            <el-table-column prop="sample_time" label="时间" width="170" show-overflow-tooltip />
            <el-table-column prop="complaint_type" label="大类" width="100" />
            <el-table-column prop="sub_category" label="小类" width="120" />
            <el-table-column prop="raw_text" label="投诉正文" min-width="260" show-overflow-tooltip />
            <el-table-column label="向量" min-width="220" show-overflow-tooltip>
                <template #default="{ row }">
                    <span>{{ formatVector(row.complaint_vector) }}</span>
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

interface ComplaintRow {
    complaint_id: string;
    user_id: string;
    sample_time: string;
    complaint_type: string;
    sub_category: string;
    raw_text: string;
    complaint_vector?: number[] | null;
    region?: string;
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
    Object.assign(form, row, { category_key: `${row.complaint_type}:${row.sub_category}` });
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
.query-form {
    margin-bottom: 8px;
}
.query-form :deep(.el-input),
.query-form :deep(.el-select) {
    width: 130px;
}
.pager {
    justify-content: flex-end;
    margin-top: 16px;
}
</style>
