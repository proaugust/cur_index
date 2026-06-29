<template>
    <div class="role-permission">
        <el-alert
            v-if="hint"
            :title="hint"
            type="info"
            :closable="false"
            show-icon
            class="perm-hint"
        >
            <template #default>
                <p>{{ hint }}</p>
                <p v-if="menuCount || apiCount" class="perm-stats">
                    共 <strong>{{ menuCount }}</strong> 个菜单、<strong>{{ apiCount }}</strong> 个接口。
                    勾选父级将自动勾选其下所有子菜单与接口。
                </p>
            </template>
        </el-alert>

        <div class="perm-toolbar">
            <el-button size="small" @click="checkAll">全选</el-button>
            <el-button size="small" @click="uncheckAll">全不选</el-button>
            <el-button size="small" @click="expandAll">展开全部</el-button>
            <el-button size="small" @click="collapseAll">折叠全部</el-button>
            <span class="perm-selected">已选 {{ selectedCount }} 项</span>
        </div>

        <el-scrollbar max-height="420px" class="perm-tree-wrap">
            <el-tree
                v-if="data.length"
                ref="treeRef"
                :data="data"
                node-key="id"
                show-checkbox
                default-expand-all
                :props="{ label: 'title', children: 'children' }"
            >
                <template #default="{ data: node }">
                    <span class="tree-node">
                        <el-tag v-if="node.type === 'api'" size="small" type="info" class="tree-tag">接口</el-tag>
                        <el-tag v-else size="small" type="success" class="tree-tag">菜单</el-tag>
                        <span class="tree-title">{{ node.title }}</span>
                        <span class="tree-id">{{ node.id }}</span>
                        <span v-if="node.type === 'api'" class="tree-meta">{{ node.api_method }} {{ node.api_path }}</span>
                    </span>
                </template>
            </el-tree>
            <el-empty v-else description="权限树加载中..." />
        </el-scrollbar>

        <el-button v-if="!embedded" type="primary" class="perm-save" @click="onSubmit">保存权限</el-button>
    </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { ElMessage, ElTree } from 'element-plus';
import { fetchPermissionTree, updateRolePermissions } from '@/api';

interface PermissionTreeNode {
    id: string;
    title: string;
    type: 'menu' | 'api';
    api_method?: string | null;
    api_path?: string | null;
    children?: PermissionTreeNode[];
}

const props = defineProps({
    permissOptions: {
        type: Object,
        default: () => ({ id: 0, permiss: [] as string[] }),
    },
    embedded: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits(['saved']);

const treeRef = ref<InstanceType<typeof ElTree>>();
const data = ref<PermissionTreeNode[]>([]);
const hint = ref('');
const menuCount = ref(0);
const apiCount = ref(0);
const allNodeIds = ref<string[]>([]);

const collectIds = (nodes: PermissionTreeNode[]): string[] => {
    const ids: string[] = [];
    const walk = (items: PermissionTreeNode[]) => {
        for (const item of items) {
            ids.push(item.id);
            if (item.children?.length) walk(item.children);
        }
    };
    walk(nodes);
    return ids;
};

const applyChecked = async (codes: string[]) => {
    await nextTick();
    treeRef.value?.setCheckedKeys(codes, false);
};

const loadTree = async () => {
    const res = await fetchPermissionTree();
    const payload = res.data;
    data.value = payload.tree;
    hint.value = payload.hint;
    menuCount.value = payload.menu_count;
    apiCount.value = payload.api_count;
    allNodeIds.value = collectIds(payload.tree);
    await applyChecked(props.permissOptions.permiss || []);
};

onMounted(loadTree);

watch(
    () => props.permissOptions.permiss,
    (codes) => {
        applyChecked(codes || []);
    },
    { deep: true },
);

const selectedCount = computed(() => {
    const checked = (treeRef.value?.getCheckedKeys(false) as string[]) || [];
    const half = (treeRef.value?.getHalfCheckedKeys() as string[]) || [];
    return checked.length + half.length;
});

const getCheckedPermissions = (): string[] => {
    const checked = (treeRef.value?.getCheckedKeys(false) as string[]) || [];
    // 半选父节点表示子项部分选中，不授予父级菜单权限
    return checked;
};

const checkAll = () => treeRef.value?.setCheckedKeys(allNodeIds.value, false);
const uncheckAll = () => treeRef.value?.setCheckedKeys([], false);
const expandAll = () => {
    for (const id of allNodeIds.value) {
        const node = treeRef.value?.getNode(id);
        if (node) node.expanded = true;
    }
};
const collapseAll = () => {
    for (const id of allNodeIds.value) {
        const node = treeRef.value?.getNode(id);
        if (node) node.expanded = false;
    }
};

const onSubmit = async () => {
    const keys = getCheckedPermissions();
    try {
        await updateRolePermissions(props.permissOptions.id, keys);
        ElMessage.success('权限已保存');
        emit('saved');
    } catch {
        ElMessage.error('保存失败');
    }
};

defineExpose({ getCheckedPermissions, loadTree });
</script>

<style scoped>
.role-permission {
    width: 100%;
}
.perm-hint {
    margin-bottom: 12px;
}
.perm-hint p {
    margin: 0;
    line-height: 1.6;
}
.perm-stats {
    margin-top: 6px !important;
    color: #606266;
}
.perm-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    flex-wrap: wrap;
}
.perm-selected {
    margin-left: auto;
    color: #909399;
    font-size: 13px;
}
.perm-tree-wrap {
    border: 1px solid #ebeef5;
    border-radius: 4px;
    padding: 8px;
}
.perm-save {
    margin-top: 12px;
}
.tree-node {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}
.tree-tag {
    flex-shrink: 0;
}
.tree-title {
    font-weight: 500;
}
.tree-id {
    color: #909399;
    font-size: 12px;
}
.tree-meta {
    color: #a8abb2;
    font-size: 12px;
}
</style>
