<template>
    <div class="test-report">
        <el-row :gutter="12" class="stat-row">
            <el-col :span="6">
                <div class="stat-card">
                    <div class="stat-value">{{ stats.total }}</div>
                    <div class="stat-label">{{ t('pages.cobolMigrate.statTotal') }}</div>
                </div>
            </el-col>
            <el-col :span="6">
                <div class="stat-card pass">
                    <div class="stat-value">{{ stats.passed }}</div>
                    <div class="stat-label">{{ t('pages.cobolMigrate.statusPass') }}</div>
                </div>
            </el-col>
            <el-col :span="6">
                <div class="stat-card warn">
                    <div class="stat-value">{{ stats.warned }}</div>
                    <div class="stat-label">{{ t('pages.cobolMigrate.statusWarn') }}</div>
                </div>
            </el-col>
            <el-col :span="6">
                <div class="stat-card skip">
                    <div class="stat-value">{{ stats.skipped }}</div>
                    <div class="stat-label">{{ t('pages.cobolMigrate.statSkipped') }}</div>
                </div>
            </el-col>
        </el-row>

        <el-table :data="results" stripe size="small" class="result-table">
            <el-table-column type="expand">
                <template #default="{ row }">
                    <div class="expand-panel">
                        <div v-if="row.message" class="expand-message">{{ row.message }}</div>
                        <pre v-if="row.snippet" class="snippet-block">{{ row.snippet }}</pre>
                    </div>
                </template>
            </el-table-column>
            <el-table-column prop="java_class" :label="t('pages.cobolMigrate.colJavaClass')" min-width="180" />
            <el-table-column prop="method" :label="t('pages.cobolMigrate.colMethod')" width="160" />
            <el-table-column :label="t('pages.cobolMigrate.colStatus')" width="100">
                <template #default="{ row }">
                    <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
                </template>
            </el-table-column>
            <el-table-column :label="t('pages.cobolMigrate.colDuration')" width="100" align="right">
                <template #default="{ row }">{{ row.duration_ms }} ms</template>
            </el-table-column>
        </el-table>
    </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';

interface TestResult {
    java_class: string;
    method: string;
    status: string;
    duration_ms: number;
    message?: string;
    snippet?: string;
}

interface TestStats {
    total: number;
    passed: number;
    warned: number;
    skipped: number;
}

defineProps<{
    results: TestResult[];
    stats: TestStats;
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
.stat-row {
    margin-bottom: 16px;
}

.stat-card {
    text-align: center;
    padding: 12px 8px;
    border-radius: 6px;
    background: #f4f4f5;
    border: 1px solid #ebeef5;
}

.stat-card.pass {
    background: #f0f9eb;
    border-color: #e1f3d8;
}

.stat-card.warn {
    background: #fdf6ec;
    border-color: #faecd8;
}

.stat-card.skip {
    background: #f4f4f5;
}

.stat-value {
    font-size: 22px;
    font-weight: 700;
    color: #303133;
    line-height: 1.2;
}

.stat-label {
    margin-top: 4px;
    font-size: 12px;
    color: #909399;
}

.expand-panel {
    padding: 4px 12px 12px;
}

.expand-message {
    font-size: 13px;
    color: #606266;
    margin-bottom: 8px;
}

.snippet-block {
    margin: 0;
    padding: 10px 12px;
    background: #1e1e1e;
    color: #d4d4d4;
    border-radius: 6px;
    font-size: 12px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
}
</style>
