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
                        {{ t('pages.system.add') }}
                    </el-button>
                </template>
                <template #status="{ rows }">
                    <el-tag type="success" v-if="rows.status">{{ t('pages.system.enabled') }}</el-tag>
                    <el-tag type="danger" v-else>{{ t('pages.system.disabled') }}</el-tag>
                </template>
                <template #permissions="{ rows }">
                    <el-button
                        v-if="canManage"
                        type="primary"
                        size="small"
                        plain
                        @click="handleEdit(rows)"
                    >
                        {{ t('pages.system.editPermissions') }}
                    </el-button>
                </template>
            </TableCustom>
        </div>

        <el-dialog
            :title="isEdit ? t('pages.system.editRole') : t('pages.system.addRole')"
            v-model="visible"
            width="920px"
            destroy-on-close
            :close-on-click-modal="false"
            @close="closeDialog"
        >
            <el-form :model="form" label-width="100px">
                <el-row :gutter="16">
                    <el-col :span="12">
                        <el-form-item :label="t('pages.system.roleName')" required>
                            <el-input v-model="form.name" :placeholder="t('pages.system.roleName')" />
                        </el-form-item>
                    </el-col>
                    <el-col :span="12">
                        <el-form-item :label="t('pages.system.roleKey')" required>
                            <el-input v-model="form.key" :disabled="isEdit" placeholder="auditor" />
                        </el-form-item>
                    </el-col>
                    <el-col :span="12">
                        <el-form-item :label="t('pages.system.status')">
                            <el-switch v-model="form.status" :active-text="t('pages.system.enabled')" :inactive-text="t('pages.system.disabled')" />
                        </el-form-item>
                    </el-col>
                </el-row>
            </el-form>

            <el-divider content-position="left">{{ t('pages.system.menuApiPermissions') }}</el-divider>
            <RolePermission
                v-if="visible"
                ref="permRef"
                embedded
                :permiss-options="{ id: form.id, permiss: form.permiss }"
            />

            <template #footer>
                <el-button @click="closeDialog">{{ t('common.cancel') }}</el-button>
                <el-button type="primary" :loading="saving" @click="saveRole">{{ t('common.save') }}</el-button>
            </template>
        </el-dialog>

        <el-dialog :title="t('pages.system.viewDetail')" v-model="visible1" width="700px" destroy-on-close>
            <TableDetail :data="viewData">
                <template #status="{ rows }">
                    <el-tag type="success" v-if="rows.status">{{ t('pages.system.enabled') }}</el-tag>
                    <el-tag type="danger" v-else>{{ t('pages.system.disabled') }}</el-tag>
                </template>
            </TableDetail>
        </el-dialog>
    </div>
</template>

<script setup lang="ts" name="system-role">
import { ref, reactive, onMounted, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { Role } from '@/types/role';
import { createRole, deleteRole, fetchMe, fetchRoleData, updateRole } from '@/api';
import TableCustom from '@/components/table-custom.vue';
import TableDetail from '@/components/table-detail.vue';
import TableSearch from '@/components/table-search.vue';
import RolePermission from './role-permission.vue';
import { CirclePlusFilled } from '@element-plus/icons-vue';
import { FormOptionList } from '@/types/form-option';

const { t } = useI18n();

const canManage = ref(false);
const saving = ref(false);
const permRef = ref<InstanceType<typeof RolePermission>>();

const query = reactive({ name: '' });
const searchOpt = computed<FormOptionList[]>(() => [{ type: 'input', label: t('pages.system.roleNameLabel'), prop: 'name' }]);
const handleSearch = () => changePage(1);

const columns = computed(() => {
    const cols = [
        { type: 'index', label: t('pages.system.index'), width: 55, align: 'center' },
        { prop: 'name', label: t('pages.system.roleName') },
        { prop: 'key', label: t('pages.system.roleKey') },
        { prop: 'status', label: t('pages.system.status') },
        { prop: 'permissions', label: t('pages.system.editPermissions'), width: 120 },
        { prop: 'operator', label: t('pages.system.operator'), width: 250 },
    ];
    if (!canManage.value) {
        return cols.filter((item) => item.prop !== 'operator' && item.prop !== 'permissions');
    }
    return cols;
});
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
        ElMessage.warning(t('pages.system.roleNameRequired'));
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
            ElMessage.success(t('pages.system.roleUpdated'));
        } else {
            await createRole({
                name: form.value.name,
                key: form.value.key,
                status: form.value.status,
                permiss,
            });
            ElMessage.success(t('pages.system.roleCreated'));
        }
        closeDialog();
        getData();
    } catch {
        ElMessage.error(t('pages.system.saveFailed'));
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
        { prop: 'id', label: t('pages.system.roleId') },
        { prop: 'name', label: t('pages.system.roleName') },
        { prop: 'key', label: t('pages.system.roleKey') },
        { prop: 'status', label: t('pages.system.roleStatus') },
    ];
    visible1.value = true;
};

const handleDelete = async (row: Role) => {
    try {
        await deleteRole(row.id);
        ElMessage.success(t('pages.system.deleteSuccess'));
        getData();
    } catch {
        ElMessage.error(t('pages.system.deleteFailed'));
    }
};
</script>

<style scoped></style>
