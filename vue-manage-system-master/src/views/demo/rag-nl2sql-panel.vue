<template>
    <RagDemoShell
        title="问数 NL2SQL"
        description="先检索演示库 Schema，再生成只读 SQL 并执行，最后汇总成自然语言。"
        :loading="loading"
        :answer="answer"
        @submit="run"
    >
        <template #fields>
            <el-form-item label="问题" required>
                <el-input v-model="question" clearable placeholder="华东销售额前三的产品？" style="max-width: 560px" />
            </el-form-item>
        </template>
        <template #extra>
            <div v-if="sql" class="answer-box">
                <div class="answer-label">SQL</div>
                <div class="answer-body">{{ sql }}</div>
            </div>
            <el-table v-if="rows.length" :data="rows" stripe border size="small" style="width: 100%; margin-top: 8px">
                <el-table-column v-for="col in columns" :key="col" :prop="col" :label="col" min-width="120" show-overflow-tooltip />
            </el-table>
        </template>
    </RagDemoShell>
</template>

<script setup lang="ts" name="rag-nl2sql-panel">
import { computed, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { ragNl2sql } from '@/api';
import RagDemoShell from '@/views/demo/rag-demo-shell.vue';

const loading = ref(false);
const question = ref('华东销售额最高的产品是什么？');
const answer = ref('');
const sql = ref('');
const rows = ref<Record<string, unknown>[]>([]);
const columns = computed(() => (rows.value[0] ? Object.keys(rows.value[0]) : []));

const run = async () => {
    if (!question.value.trim()) {
        ElMessage.warning('请输入问题');
        return;
    }
    loading.value = true;
    answer.value = '';
    sql.value = '';
    rows.value = [];
    try {
        const res = await ragNl2sql({ question: question.value.trim() });
        const data = res.data as { answer?: string; sql?: string; rows?: Record<string, unknown>[] };
        answer.value = data.answer ?? '';
        sql.value = data.sql ?? '';
        rows.value = data.rows ?? [];
    } catch (err: unknown) {
        const detail =
            err && typeof err === 'object' && 'response' in err
                ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
                : undefined;
        ElMessage.error(detail || 'NL2SQL 失败');
    } finally {
        loading.value = false;
    }
};
</script>
