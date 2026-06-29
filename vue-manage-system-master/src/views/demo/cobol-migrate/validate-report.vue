<template>
    <div class="validate-report">
        <div class="sub-title">{{ t('pages.cobolMigrate.businessChainTitle') }}</div>
        <div class="chain-list">
            <div v-for="chain in businessChains" :key="chain.name" class="chain-card">
                <div class="chain-header">
                    <span class="chain-name">{{ chain.name }}</span>
                    <el-tag :type="statusTag(chain.status)" size="small">{{ statusLabel(chain.status) }}</el-tag>
                </div>
                <div class="chain-flow">
                    <template v-for="(node, i) in chain.nodes" :key="`${chain.name}-${node}-${i}`">
                        <span class="chain-node">{{ node }}</span>
                        <span v-if="i < chain.nodes.length - 1" class="chain-arrow">→</span>
                    </template>
                </div>
                <p v-if="chain.gap" class="chain-gap">{{ chain.gap }}</p>
            </div>
        </div>

        <div class="sub-title mgt16">{{ t('pages.cobolMigrate.checklistTitle') }}</div>
        <el-table :data="items" stripe size="small">
            <el-table-column prop="item" :label="t('pages.cobolMigrate.colCheckItem')" min-width="180" />
            <el-table-column :label="t('pages.cobolMigrate.colStatus')" width="100">
                <template #default="{ row }">
                    <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
                </template>
            </el-table-column>
            <el-table-column prop="detail" :label="t('pages.cobolMigrate.colDetail')" min-width="280" show-overflow-tooltip />
        </el-table>
    </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';

interface ChainRow {
    name: string;
    status: string;
    nodes: string[];
    gap?: string;
}

interface CheckItem {
    item: string;
    status: string;
    detail: string;
}

defineProps<{
    businessChains: ChainRow[];
    items: CheckItem[];
}>();

const { t } = useI18n();

const statusTag = (status: string) => {
    if (status === 'pass') return 'success';
    if (status === 'warn') return 'warning';
    return 'danger';
};

const statusLabel = (status: string) => {
    if (status === 'pass') return t('pages.cobolMigrate.statusPass');
    if (status === 'warn') return t('pages.cobolMigrate.statusWarn');
    return t('pages.cobolMigrate.statusFail');
};
</script>

<style scoped>
.sub-title {
    font-size: 13px;
    font-weight: 600;
    color: #606266;
    margin-bottom: 8px;
}

.mgt16 {
    margin-top: 16px;
}

.chain-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.chain-card {
    border: 1px solid #ebeef5;
    border-radius: 6px;
    padding: 10px 12px;
    background: #fafafa;
}

.chain-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}

.chain-name {
    font-weight: 600;
    font-size: 13px;
    color: #303133;
}

.chain-flow {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px;
}

.chain-node {
    padding: 2px 8px;
    background: #ecf5ff;
    color: #409eff;
    border-radius: 4px;
    font-size: 12px;
}

.chain-arrow {
    color: #c0c4cc;
    font-size: 12px;
}

.chain-gap {
    margin: 8px 0 0;
    font-size: 12px;
    color: #e6a23c;
}
</style>
