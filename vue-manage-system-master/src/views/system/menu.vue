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
                        新增
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
            :title="isEdit ? '编辑' : '新增'"
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
        <el-dialog title="查看详情" v-model="visible1" width="700px" destroy-on-close>
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
import { ElMessage } from 'element-plus';
import { CirclePlusFilled } from '@element-plus/icons-vue';
import { createMenu, deleteMenu, fetchMe, fetchMenuData, updateMenu } from '@/api';
import TableCustom from '@/components/table-custom.vue';
import TableDetail from '@/components/table-detail.vue';
import TableEdit from '@/components/table-edit.vue';
import { FormOption } from '@/types/form-option';

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

const columns = ref([
    { prop: 'title', label: '菜单名称', align: 'left' },
    { prop: 'icon', label: '图标' },
    { prop: 'index', label: '路由路径' },
    { prop: 'permiss', label: '权限标识' },
    { prop: 'operator', label: '操作', width: 250 },
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

const options = ref<FormOption>({
    labelWidth: '100px',
    span: 12,
    list: [
        { type: 'input', label: '菜单名称', prop: 'title', required: true },
        { type: 'input', label: '权限标识', prop: 'permiss', required: true },
        { type: 'input', label: '路由路径', prop: 'index', required: true },
        { type: 'input', label: '图标', prop: 'icon' },
        { type: 'parent_code', label: '父菜单', prop: 'parent_code' },
    ],
});

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
            ElMessage.success('更新成功');
        } else {
            await createMenu({
                code: form.permiss as string,
                name: form.title as string,
                parent_code,
                route_path: form.index as string,
                icon: (form.icon as string) || undefined,
            });
            ElMessage.success('创建成功');
        }
        closeDialog();
        loadMenus();
    } catch {
        ElMessage.error('操作失败');
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
        { prop: 'id', label: '菜单ID' },
        { prop: 'pid', label: '父菜单ID' },
        { prop: 'title', label: '菜单名称' },
        { prop: 'index', label: '路由路径' },
        { prop: 'permiss', label: '权限标识' },
        { prop: 'icon', label: '图标' },
    ];
    visible1.value = true;
};

const handleDelete = async (row: MenuItem) => {
    if (row.is_system) {
        ElMessage.warning('系统内置菜单不可删除');
        return;
    }
    try {
        await deleteMenu(row.permiss);
        ElMessage.success('删除成功');
        loadMenus();
    } catch {
        ElMessage.error('删除失败');
    }
};
</script>

<style scoped></style>
