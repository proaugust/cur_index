<template>
    <div>
        <div class="container">
            <TableCustom
                :columns="columns"
                :tableData="menuTree"
                row-key="id"
                :has-pagination="false"
                :viewFunc="handleView"
                :delFunc="handleDelete"
                :editFunc="handleEdit"
            >
                <template #toolbarBtn>
                    <el-button v-if="canManage" type="warning" :icon="CirclePlusFilled" @click="openCreate">
                        {{ t('pages.system.add') }}
                    </el-button>
                </template>
                <template #icon="{ rows }">
                    <el-icon v-if="rows.icon">
                        <component :is="rows.icon"></component>
                    </el-icon>
                </template>
            </TableCustom>
        </div>
        <el-dialog
            :title="isEdit ? t('pages.system.edit') : t('pages.system.add')"
            v-model="visible"
            width="700px"
            destroy-on-close
            :close-on-click-modal="false"
            @close="closeDialog"
        >
            <TableEdit :form-data="rowData" :options="options" :edit="isEdit" :update="updateData">
                <template #parent_code>
                    <el-cascader
                        v-model="parentPath"
                        :options="cascaderOptions"
                        :props="{ checkStrictly: true, emitPath: true, value: 'value', label: 'label' }"
                        clearable
                    />
                </template>
            </TableEdit>
        </el-dialog>
        <el-dialog :title="t('pages.system.viewDetail')" v-model="visible1" width="700px" destroy-on-close>
            <TableDetail :data="viewData">
                <template #icon="{ rows }">
                    <el-icon v-if="rows.icon">
                        <component :is="rows.icon"></component>
                    </el-icon>
                </template>
            </TableDetail>
        </el-dialog>
    </div>
</template>

<script setup lang="ts" name="system-menu">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { CirclePlusFilled } from '@element-plus/icons-vue';
import { createMenu, deleteMenu, fetchMe, fetchMenuData, updateMenu } from '@/api';
import TableCustom from '@/components/table-custom.vue';
import TableDetail from '@/components/table-detail.vue';
import TableEdit from '@/components/table-edit.vue';
import { FormOption } from '@/types/form-option';

const { t } = useI18n();

interface MenuItem {
    id: string;
    pid?: string | null;
    title: string;
    index: string;
    icon?: string | null;
    permiss: string;
    is_system?: boolean;
    children?: MenuItem[];
}

const canManage = ref(false);
const menuTree = ref<MenuItem[]>([]);
const parentPath = ref<string[]>([]);

const columns = computed(() => [
    { prop: 'title', label: t('pages.system.menuName'), align: 'left' },
    { prop: 'icon', label: t('pages.system.icon') },
    { prop: 'index', label: t('pages.system.routePath') },
    { prop: 'permiss', label: t('pages.system.permCode') },
    { prop: 'operator', label: t('pages.system.operator'), width: 250 },
]);

const buildCascader = (items: MenuItem[]) =>
    items.map((item) => ({
        label: item.title,
        value: item.id,
        children: item.children?.length ? buildCascader(item.children) : undefined,
    }));

const cascaderOptions = computed(() => buildCascader(menuTree.value));

const loadMenus = async () => {
    const res = await fetchMenuData();
    menuTree.value = res.data;
};

const loadMe = async () => {
    const res = await fetchMe();
    canManage.value = res.data.user.level === 1;
};

onMounted(async () => {
    await Promise.all([loadMenus(), loadMe()]);
});

const buildOptions = (): FormOption => ({
    labelWidth: '100px',
    span: 12,
    list: [
        { type: 'input', label: t('pages.system.menuName'), prop: 'title', required: true },
        { type: 'input', label: t('pages.system.permCode'), prop: 'permiss', required: true },
        { type: 'input', label: t('pages.system.routePath'), prop: 'index', required: true },
        { type: 'input', label: t('pages.system.icon'), prop: 'icon' },
        { type: 'parent_code', label: t('pages.system.parentMenu'), prop: 'parent_code' },
    ],
});

const options = ref<FormOption>(buildOptions());

const visible = ref(false);
const isEdit = ref(false);
const rowData = ref<Record<string, unknown>>({});

const openCreate = () => {
    rowData.value = {};
    parentPath.value = [];
    options.value.list = options.value.list.map((item) =>
        item.prop === 'permiss' ? { ...item, disabled: false } : item,
    );
    isEdit.value = false;
    visible.value = true;
};

const handleEdit = (row: MenuItem) => {
    rowData.value = { ...row };
    parentPath.value = row.pid ? [row.pid] : [];
    options.value.list = options.value.list.map((item) =>
        item.prop === 'permiss' ? { ...item, disabled: true } : item,
    );
    isEdit.value = true;
    visible.value = true;
};

const updateData = async (form: Record<string, unknown>) => {
    const parent_code = parentPath.value.length ? parentPath.value[parentPath.value.length - 1] : undefined;
    try {
        if (isEdit.value) {
            await updateMenu(form.permiss as string, {
                name: form.title as string,
                parent_code,
                route_path: form.index as string,
                icon: (form.icon as string) || undefined,
            });
            ElMessage.success(t('pages.system.updateSuccess'));
        } else {
            await createMenu({
                code: form.permiss as string,
                name: form.title as string,
                parent_code,
                route_path: form.index as string,
                icon: (form.icon as string) || undefined,
            });
            ElMessage.success(t('pages.system.createSuccess'));
        }
        closeDialog();
        loadMenus();
    } catch {
        ElMessage.error(t('pages.system.opFailed'));
    }
};

const closeDialog = () => {
    visible.value = false;
    isEdit.value = false;
    rowData.value = {};
    parentPath.value = [];
};

const visible1 = ref(false);
const viewData = ref({ row: {}, list: [] as { prop: string; label: string }[] });

const handleView = (row: MenuItem) => {
    viewData.value.row = { ...row };
    viewData.value.list = [
        { prop: 'id', label: t('pages.system.menuId') },
        { prop: 'pid', label: t('pages.system.parentMenuId') },
        { prop: 'title', label: t('pages.system.menuName') },
        { prop: 'index', label: t('pages.system.routePath') },
        { prop: 'permiss', label: t('pages.system.permCode') },
        { prop: 'icon', label: t('pages.system.icon') },
    ];
    visible1.value = true;
};

const handleDelete = async (row: MenuItem) => {
    if (row.is_system) {
        ElMessage.warning(t('pages.system.systemMenuNoDelete'));
        return;
    }
    try {
        await deleteMenu(row.permiss);
        ElMessage.success(t('pages.system.deleteSuccess'));
        loadMenus();
    } catch {
        ElMessage.error(t('pages.system.deleteFailed'));
    }
};
</script>

<style scoped></style>
