<template>
    <el-card shadow="never" class="data-card">
        <template #header>
            <div class="card-header">
                <span>用户画像管理 (insight_user_profile)</span>
                <el-button type="primary" @click="openCreate">新增用户</el-button>
            </div>
        </template>

        <el-form :model="query" inline class="query-form">
            <el-form-item label="用户ID"><el-input v-model="query.user_id" clearable /></el-form-item>
            <el-form-item label="区域"><el-input v-model="query.region" clearable /></el-form-item>
            <el-form-item label="年龄段"><el-input v-model="query.age_group" clearable /></el-form-item>
            <el-form-item label="套餐"><el-input v-model="query.plan_id" clearable /></el-form-item>
            <el-form-item label="VIP"><el-input v-model="query.vip_level" clearable /></el-form-item>
            <el-form-item label="风险"><el-input v-model="query.risk_level" clearable /></el-form-item>
            <el-form-item>
                <el-button type="primary" @click="search">查询</el-button>
                <el-button @click="resetQuery">重置</el-button>
            </el-form-item>
        </el-form>

        <el-table :data="rows" v-loading="loading" border stripe>
            <el-table-column prop="user_id" label="用户ID" width="110" />
            <el-table-column prop="name" label="姓名" width="90" />
            <el-table-column prop="age" label="年龄" width="70" />
            <el-table-column prop="age_group" label="年龄段" width="90" />
            <el-table-column prop="region" label="区域" min-width="140" show-overflow-tooltip />
            <el-table-column prop="plan_id" label="套餐" width="110" />
            <el-table-column prop="monthly_fee" label="月消费" width="90" />
            <el-table-column prop="risk_score" label="风险分" width="90">
                <template #default="{ row }">{{ row.risk_score ?? '-' }}</template>
            </el-table-column>
            <el-table-column prop="risk_level" label="风险等级" width="90">
                <template #default="{ row }">{{ row.risk_level || '-' }}</template>
            </el-table-column>
            <el-table-column prop="tags" label="标签" min-width="160">
                <template #default="{ row }">
                    <el-tag v-for="tag in row.tags || []" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
                    <span v-if="!row.tags?.length">-</span>
                </template>
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
                    <el-col :span="12"><el-form-item label="年龄"><el-input-number v-model="form.age" :min="0" :max="120" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="年龄段"><el-input v-model="form.age_group" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="区域"><el-input v-model="form.region" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="套餐"><el-input v-model="form.plan_id" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="VIP"><el-input v-model="form.vip_level" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="入网日期"><el-date-picker v-model="form.join_date" value-format="YYYY-MM-DD" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="月消费"><el-input-number v-model="form.monthly_fee" :min="0" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="网络满意度"><el-input-number v-model="form.satisfaction_net" :min="1" :max="5" /></el-form-item></el-col>
                    <el-col :span="12"><el-form-item label="客服满意度"><el-input-number v-model="form.satisfaction_srv" :min="1" :max="5" /></el-form-item></el-col>
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
    age: number;
    age_group: string;
    region: string;
    plan_id: string;
    monthly_fee: number | string;
    vip_level: string;
    join_date: string;
    satisfaction_net: number;
    satisfaction_srv: number;
    risk_score?: number | string;
    risk_level?: string;
    tags?: string[];
}

const emit = defineEmits<{ refresh: [] }>();
const rows = ref<UserRow[]>([]);
const loading = ref(false);
const saving = ref(false);
const visible = ref(false);
const editingId = ref<string | null>(null);
const page = reactive({ index: 1, size: 10, total: 0 });
const query = reactive({ user_id: '', region: '', age_group: '', plan_id: '', vip_level: '', risk_level: '' });
const emptyForm = (): UserRow => ({
    user_id: '',
    name: '',
    age: 30,
    age_group: '26-35',
    region: '',
    plan_id: '199元套餐',
    monthly_fee: 199,
    vip_level: '普通',
    join_date: '',
    satisfaction_net: 3,
    satisfaction_srv: 3,
});
const form = reactive(emptyForm());

function params() {
    return { ...query, page: page.index, page_size: page.size };
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
    Object.assign(query, { user_id: '', region: '', age_group: '', plan_id: '', vip_level: '', risk_level: '' });
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
    Object.assign(form, row, { monthly_fee: Number(row.monthly_fee) });
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
.query-form {
    margin-bottom: 8px;
}
.query-form :deep(.el-input) {
    width: 130px;
}
.pager {
    justify-content: flex-end;
    margin-top: 16px;
}
.tag-item {
    margin-right: 4px;
}
</style>
