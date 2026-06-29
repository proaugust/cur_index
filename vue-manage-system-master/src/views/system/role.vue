<template>
    <div>
        <TableSearch :query="query" :options="searchOpt" :search="handleSearch" />
        <div class="container">
            <TableCustom
                :columns="columns"
                :tableData="tableData"
                :total="page.total"
                :viewFunc="handleView"
                :delFunc="canManage ? handleDelete : undefined"
                :page-change="changePage"
                :editFunc="canManage ? handleEdit : undefined"
            >
                <template #toolbarBtn>
                    <el-button v-if="canManage" type="warning" :icon="CirclePlusFilled" @click="openCreate">
                        新增
                    </el-button>
                </template>
                <template #status="{ rows }">
                    <el-tag type="success" v-if="rows.status">启用</el-tag>
                    <el-tag type="danger" v-else>禁用</el-tag>
                </template>
                <template #permissions="{ rows }">
                    <el-button
                        v-if="canManage"
                        type="primary"
                        size="small"
                        plain
                        @click="handleEdit(rows)"
                    >
                        编辑权限
                    </el-button>
                </template>
            </TableCustom>
        </div>

        <el-dialog
            :title="isEdit ? '编辑角色' : '新增角色'"
            v-model="visible"
            width="920px"
            destroy-on-close
            :close-on-click-modal="false"
            @close="closeDialog"
        >
            <el-form :model="form" label-width="100px">
                <el-row :gutter="16">
                    <el-col :span="12">
                        <el-form-item label="角色名称" required>
                            <el-input v-model="form.name" placeholder="请输入角色名称" />
                        </el-form-item>
                    </el-col>
                    <el-col :span="12">
                        <el-form-item label="角色标识" required>
                            <el-input v-model="form.key" :disabled="isEdit" placeholder="如 auditor" />
                        </el-form-item>
                    </el-col>
                    <el-col :span="12">
                        <el-form-item label="状态">
                            <el-switch v-model="form.status" active-text="启用" inactive-text="禁用" />
                        </el-form-item>
                    </el-col>
                </el-row>
            </el-form>

            <el-divider content-position="left">菜单与接口权限</el-divider>
            <RolePermission
                v-if="visible"
                ref="permRef"
                embedded
                :permiss-options="{ id: form.id, permiss: form.permiss }"
            />

            <template #footer>
                <el-button @click="closeDialog">取消</el-button>
                <el-button type="primary" :loading="saving" @click="saveRole">保存</el-button>
            </template>
        </el-dialog>

        <el-dialog title="查看详情" v-model="visible1" width="700px" destroy-on-close>
            <TableDetail :data="viewData">
                <template #status="{ rows }">
                    <el-tag type="success" v-if="rows.status">启用</el-tag>
                    <el-tag type="danger" v-else>禁用</el-tag>
                </template>
            </TableDetail>
        </el-dialog>
    </div>
</template>

<script setup lang="ts" name="system-role">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Role } from '@/types/role';
import { createRole, deleteRole, fetchMe, fetchRoleData, updateRole } from '@/api';
import TableCustom from '@/components/table-custom.vue';
import TableDetail from '@/components/table-detail.vue';
import TableSearch from '@/components/table-search.vue';
import RolePermission from './role-permission.vue';
import { CirclePlusFilled } from '@element-plus/icons-vue';
import { FormOptionList } from '@/types/form-option';

const canManage = ref(false);
const saving = ref(false);
const permRef = ref<InstanceType<typeof RolePermission>>();

const query = reactive({ name: '' });
const searchOpt = ref<FormOptionList[]>([{ type: 'input', label: '角色名称：', prop: 'name' }]);
const handleSearch = () => changePage(1);

const baseColumns = [
    { type: 'index', label: '序号', width: 55, align: 'center' },
    { prop: 'name', label: '角色名称' },
    { prop: 'key', label: '角色标识' },
    { prop: 'status', label: '状态' },
    { prop: 'permissions', label: '权限配置', width: 120 },
    { prop: 'operator', label: '操作', width: 250 },
];
const columns = ref(baseColumns);
const page = reactive({ index: 1, size: 10, total: 0 });
const tableData = ref<Role[]>([]);

const getData = async () => {
    const res = await fetchRoleData();
    let list = res.data.list as Role[];
    if (query.name) list = list.filter((item) => item.name.includes(query.name));
    tableData.value = list;
    page.total = res.data.pageTotal;
};

onMounted(async () => {
    const me = await fetchMe();
    canManage.value = me.data.user.level === 1;
    if (!canManage.value) {
        columns.value = baseColumns.filter((item) => item.prop !== 'operator' && item.prop !== 'permissions');
    }
    getData();
});

const changePage = (val: number) => {
    page.index = val;
    getData();
};

const visible = ref(false);
const isEdit = ref(false);
const form = ref({
    id: 0,
    name: '',
    key: '',
    status: true,
    permiss: [] as string[],
});

const openCreate = () => {
    form.value = { id: 0, name: '', key: '', status: true, permiss: [] };
    isEdit.value = false;
    visible.value = true;
};

const handleEdit = (row: Role) => {
    form.value = {
        id: row.id,
        name: row.name,
        key: row.key,
        status: row.status,
        permiss: [...row.permiss],
    };
    isEdit.value = true;
    visible.value = true;
};

const saveRole = async () => {
    if (!form.value.name.trim() || !form.value.key.trim()) {
        ElMessage.warning('请填写角色名称和标识');
        return;
    }
    const permiss = permRef.value?.getCheckedPermissions() || [];
    saving.value = true;
    try {
        if (isEdit.value) {
            await updateRole(form.value.id, {
                name: form.value.name,
                status: form.value.status,
                permiss,
            });
            ElMessage.success('角色与权限已更新');
        } else {
            await createRole({
                name: form.value.name,
                key: form.value.key,
                status: form.value.status,
                permiss,
            });
            ElMessage.success('角色已创建');
        }
        closeDialog();
        getData();
    } catch {
        ElMessage.error('保存失败');
    } finally {
        saving.value = false;
    }
};

const closeDialog = () => {
    visible.value = false;
    isEdit.value = false;
};

const visible1 = ref(false);
const viewData = ref({ row: {}, list: [], column: 1 });
const handleView = (row: Role) => {
    viewData.value.row = { ...row };
    viewData.value.list = [
        { prop: 'id', label: '角色ID' },
        { prop: 'name', label: '角色名称' },
        { prop: 'key', label: '角色标识' },
        { prop: 'status', label: '角色状态' },
    ];
    visible1.value = true;
};

const handleDelete = async (row: Role) => {
    try {
        await deleteRole(row.id);
        ElMessage.success('删除成功');
        getData();
    } catch {
        ElMessage.error('删除失败');
    }
};
</script>

<style scoped></style>
