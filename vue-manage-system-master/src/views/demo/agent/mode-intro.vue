<template>
    <div class="mode-intro">
        <h3 class="mode-title">{{ title }}</h3>

        <div class="flow-chart">
            <template v-for="(node, i) in nodes" :key="node">
                <div class="flow-node" :class="{ primary: i === 0 || i === nodes.length - 1 }">
                    {{ node }}
                </div>
                <div v-if="i < nodes.length - 1" class="flow-arrow">
                    <span v-if="loop && i === nodes.length - 2" class="loop-hint">↺</span>
                    <span v-else>→</span>
                </div>
            </template>
        </div>

        <div v-if="branches?.length" class="branch-row">
            <span class="branch-label">路由分支：</span>
            <el-tag v-for="b in branches" :key="b" size="small" class="branch-tag">{{ b }}</el-tag>
        </div>
    </div>
</template>

<script setup lang="ts">
defineProps<{
    title: string;
    nodes: string[];
    branches?: string[];
    loop?: boolean;
}>();
</script>

<style scoped>
.mode-intro {
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid #ebeef5;
}

.mode-title {
    font-size: 15px;
    font-weight: 600;
    color: #303133;
    margin: 0 0 8px;
}

.mode-desc {
    font-size: 13px;
    color: #606266;
    line-height: 1.6;
    margin: 0 0 16px;
}

.flow-chart {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
}

.flow-node {
    padding: 6px 14px;
    background: #ecf5ff;
    color: #409eff;
    border: 1px solid #d9ecff;
    border-radius: 4px;
    font-size: 13px;
    white-space: nowrap;
}

.flow-node.primary {
    background: #f0f9eb;
    color: #67c23a;
    border-color: #e1f3d8;
}

.flow-arrow {
    color: #c0c4cc;
    font-size: 16px;
    padding: 0 2px;
}

.loop-hint {
    color: #e6a23c;
    font-weight: bold;
}

.branch-row {
    margin-top: 12px;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
}

.branch-label {
    font-size: 13px;
    color: #909399;
}

.branch-tag {
    margin: 0;
}
</style>
