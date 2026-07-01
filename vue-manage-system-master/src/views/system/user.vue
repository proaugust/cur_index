<template>
    <div>
        <TableSearch :query="query" :options="searchOpt" :search="handleSearch" />
        <div class="container">
            <TableCustom :columns="columns" :tableData="tableData" :total="page.total" :viewFunc="handleView"
                :delFunc="handleDelete" :page-change="changePage" :editFunc="handleEdit">
                <template #toolbarBtn>
                    <el-button type="warning" :icon="CirclePlusFilled" @click="visible = true">{{ t('pages.system.add') }}</el-button>
                </template>
            </TableCustom>

        </div>
        <el-dialog :title="isEdit ? t('pages.system.edit') : t('pages.system.add')" v-model="visible" width="700px" destroy-on-close
            :close-on-click-modal="false" @close="closeDialog">
            <TableEdit :form-data="rowData" :options="options" :edit="isEdit" :update="updateData" />
        </el-dialog>
        <el-dialog :title="t('pages.system.viewDetail')" v-model="visible1" width="700px" destroy-on-close>
            <TableDetail :data="viewData"></TableDetail>
        </el-dialog>
    </div>
</template>

<script setup lang="ts" name="system-user">
import { ref, reactive, onMounted, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { CirclePlusFilled } from '@element-plus/icons-vue';
import { User } from '@/types/user';
import { createUser, deleteUser, fetchMe, fetchRoleData, fetchUserData, updateUser } from '@/api';
import TableCustom from '@/components/table-custom.vue';
import TableDetail from '@/components/table-detail.vue';
import TableSearch from '@/components/table-search.vue';
import TableEdit from '@/components/table-edit.vue';
import { FormOption, FormOptionList } from '@/types/form-option';

const { t } = useI18n();

const roleOptions = ref<{ label: string; value: number; level?: number }[]>([]);
const currentLevel = ref(99);

const loadRoles = async () => {
    const res = await fetchRoleData();
    const list = res.data.list as { id: number; name: string; level: number }[];
    roleOptions.value = list
        .filter((item) => currentLevel.value === 1 || item.level >= 3)
        .map((item) => ({
            label: item.name,
            value: item.id,
            level: item.level,
        }));
    options.value = buildFormOptions();
    options.value.list = options.value.list.map((item) =>
        item.prop === 'role_id' ? { ...item, opts: roleOptions.value } : item,
    );
};

onMounted(async () => {
    const me = await fetchMe();
    currentLevel.value = me.data.user.level;
    await loadRoles();
    getData();
});

const query = reactive({
    name: '',
});
const searchOpt = computed<FormOptionList[]>(() => [
    { type: 'input', label: t('pages.system.usernameLabel'), prop: 'name' },
]);
const handleSearch = () => {
    changePage(1);
};

const columns = computed(() => [
    { type: 'index', label: t('pages.system.index'), width: 55, align: 'center' },
    { prop: 'name', label: t('pages.system.username') },
    { prop: 'phone', label: t('pages.system.phone') },
    { prop: 'role', label: t('pages.system.role') },
    { prop: 'operator', label: t('pages.system.operator'), width: 250 },
]);
const page = reactive({
    index: 1,
    size: 10,
    total: 0,
})
const tableData = ref<User[]>([]);
const getData = async () => {
    const res = await fetchUserData({
        name: query.name || undefined,
        page: page.index,
        page_size: page.size,
    });
    tableData.value = res.data.list;
    page.total = res.data.pageTotal;
};

const changePage = (val: number) => {
    page.index = val;
    getData();
};

const buildFormOptions = (): FormOption => ({
    labelWidth: '100px',
    span: 12,
    list: [
        { type: 'input', label: t('pages.system.username'), prop: 'name', required: true },
        { type: 'input', label: t('pages.system.phone'), prop: 'phone', required: false },
        { type: 'input', label: t('pages.system.password'), prop: 'password', required: true },
        { type: 'input', label: t('pages.system.email'), prop: 'email', required: false },
        { type: 'select', label: t('pages.system.role'), prop: 'role_id', required: true, opts: roleOptions.value },
    ],
});

let options = ref<FormOption>(buildFormOptions());
const visible = ref(false);
const isEdit = ref(false);
const rowData = ref<Record<string, unknown>>({});
const handleEdit = (row: User) => {
    rowData.value = { ...row, password: '' };
    options.value.list = options.value.list.map((item) =>
        item.prop === 'password' ? { ...item, required: false } : item,
    );
    isEdit.value = true;
    visible.value = true;
};
const updateData = async (form: Record<string, unknown>) => {
    try {
        if (isEdit.value) {
            const payload: Record<string, unknown> = {
                name: form.name,
                email: form.email,
                phone: form.phone,
                role_id: form.role_id,
            };
            if (form.password) {
                payload.password = form.password;
            }
            await updateUser(form.id as number, payload);
            ElMessage.success(t('pages.system.updateSuccess'));
        } else {
            await createUser({
                name: form.name as string,
                password: form.password as string,
                email: form.email as string | undefined,
                phone: form.phone as string | undefined,
                role_id: form.role_id as number,
            });
            ElMessage.success(t('pages.system.createSuccess'));
        }
        closeDialog();
        getData();
    } catch {
        ElMessage.error(t('pages.system.opFailed'));
    }
};

const closeDialog = () => {
    visible.value = false;
    isEdit.value = false;
    rowData.value = {};
    options.value.list = options.value.list.map((item) =>
        item.prop === 'password' ? { ...item, required: true } : item,
    );
};

// 查看详情弹窗相关
const visible1 = ref(false);
const viewData = ref<{ row: Record<string, unknown>; list: { prop: string; label: string }[] }>({
    row: {},
    list: [],
});
const viewFieldList = computed(() => [
    { prop: 'id', label: t('pages.system.userId') },
    { prop: 'name', label: t('pages.system.username') },
    { prop: 'password', label: t('pages.system.password') },
    { prop: 'email', label: t('pages.system.email') },
    { prop: 'phone', label: t('pages.system.tel') },
    { prop: 'role', label: t('pages.system.role') },
    { prop: 'date', label: t('pages.system.registerDate') },
]);

const handleView = (row: User) => {
    viewData.value.row = { ...row };
    viewData.value.list = viewFieldList.value;
    visible1.value = true;
};

// 删除相关
const handleDelete = async (row: User) => {
    try {
        await deleteUser(row.id);
        ElMessage.success(t('pages.system.deleteSuccess'));
        getData();
    } catch {
        ElMessage.error(t('pages.system.deleteFailed'));
    }
};
</script>

<style scoped></style>