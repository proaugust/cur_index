<template>
    <div class="translate-report">
        <el-row :gutter="16" class="mgb16">
            <el-col :xs="24" :md="10">
                <div class="sub-title">{{ t('pages.cobolMigrate.projectTreeTitle') }}</div>
                <el-tree
                    :data="projectTree"
                    default-expand-all
                    :props="{ label: 'label', children: 'children' }"
                    class="project-tree"
                />
            </el-col>
            <el-col :xs="24" :md="14">
                <div class="sub-title">{{ t('pages.cobolMigrate.mappingTableTitle') }}</div>
                <el-table :data="mappings" stripe size="small" max-height="280">
                    <el-table-column prop="cobol" :label="t('pages.cobolMigrate.colCobol')" width="130" />
                    <el-table-column prop="java" :label="t('pages.cobolMigrate.colJava')" min-width="260" show-overflow-tooltip />
                    <el-table-column prop="layer" :label="t('pages.cobolMigrate.colLayer')" width="110" />
                </el-table>
            </el-col>
        </el-row>

        <div class="sub-title">{{ t('pages.cobolMigrate.codeCompareTitle') }}</div>
        <el-tabs v-model="activePair" type="border-card" class="code-tabs">
            <el-tab-pane
                v-for="(pair, index) in codePairs"
                :key="pair.cobol_file"
                :label="pair.cobol_file"
                :name="String(index)"
            >
                <el-row :gutter="12">
                    <el-col :xs="24" :md="12">
                        <div class="code-label">COBOL · {{ pair.cobol_file }}</div>
                        <pre class="code-block cobol">{{ pair.cobol_snippet }}</pre>
                    </el-col>
                    <el-col :xs="24" :md="12">
                        <div class="code-label">Java · {{ pair.java_file }}</div>
                        <pre class="code-block java">{{ pair.java_snippet }}</pre>
                    </el-col>
                </el-row>
            </el-tab-pane>
        </el-tabs>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

interface TreeNode {
    label: string;
    children?: TreeNode[];
}

interface MappingRow {
    cobol: string;
    java: string;
    layer: string;
}

interface CodePair {
    cobol_file: string;
    java_file: string;
    cobol_snippet: string;
    java_snippet: string;
}

defineProps<{
    projectTree: TreeNode[];
    mappings: MappingRow[];
    codePairs: CodePair[];
}>();

const { t } = useI18n();
const activePair = ref('0');
</script>

<style scoped>
.mgb16 {
    margin-bottom: 16px;
}

.sub-title {
    font-size: 13px;
    font-weight: 600;
    color: #606266;
    margin-bottom: 8px;
}

.project-tree {
    border: 1px solid #ebeef5;
    border-radius: 6px;
    padding: 8px 12px;
    max-height: 280px;
    overflow: auto;
    background: #fafafa;
}

.code-tabs {
    margin-top: 4px;
}

.code-label {
    font-size: 12px;
    color: #909399;
    margin-bottom: 6px;
}

.code-block {
    margin: 0;
    padding: 12px;
    border-radius: 6px;
    font-size: 12px;
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 220px;
    overflow: auto;
}

.code-block.cobol {
    background: #fdf6ec;
    border: 1px solid #faecd8;
    color: #7d5a2e;
}

.code-block.java {
    background: #ecf5ff;
    border: 1px solid #d9ecff;
    color: #1f4a7a;
}
</style>
