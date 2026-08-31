<template>
    <RagDemoShell
        title="长文档审计"
        description="业务库 hybrid 细节检索 + 章节摘要，适合宏观合规/风险类问题。"
        :loading="loading"
        :answer="answer"
        @submit="run"
    >
        <template #fields>
            <el-form-item label="资料库" required>
                <el-select
                    v-model="corpusName"
                    filterable
                    clearable
                    :loading="corporaLoading"
                    placeholder="选择业务资料库"
                    style="width: 280px"
                >
                    <el-option v-for="c in corpora" :key="c.name" :label="c.name" :value="c.name" />
                </el-select>
            </el-form-item>
            <el-form-item label="问题" required>
                <el-input
                    v-model="question"
                    clearable
                    style="max-width: 560px"
                    placeholder="这份资料有哪些潜在合规风险？"
                />
            </el-form-item>
        </template>
        <template #extra>
            <div v-for="(s, i) in summaries" :key="i" class="answer-box">
                <div class="answer-label">章节 · {{ s.section_path }}</div>
                <div class="answer-body">{{ s.summary }}</div>
            </div>
        </template>
    </RagDemoShell>
</template>

<script setup lang="ts" name="rag-longdoc-panel">
import { onMounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { listCorpora, ragLongdoc } from '@/api';
import RagDemoShell from '@/views/demo/rag-demo-shell.vue';

const loading = ref(false);
const corporaLoading = ref(false);
const corpora = ref<{ name: string }[]>([]);
const corpusName = ref('');
const question = ref('这份报销资料里，高铁和机票分别有哪些限制？');
const answer = ref('');
const summaries = ref<{ section_path: string; summary: string }[]>([]);

const loadCorpora = async () => {
    corporaLoading.value = true;
    try {
        const res = await listCorpora();
        corpora.value = (res.data as { name: string }[]) ?? [];
        if (!corpusName.value && corpora.value.length) {
            corpusName.value = corpora.value[0].name;
        }
    } catch {
        corpora.value = [];
    } finally {
        corporaLoading.value = false;
    }
};

const run = async () => {
    if (!corpusName.value.trim() || !question.value.trim()) {
        ElMessage.warning('请填写资料库与问题');
        return;
    }
    loading.value = true;
    answer.value = '';
    summaries.value = [];
    try {
        const res = await ragLongdoc({
            corpus_name: corpusName.value.trim(),
            question: question.value.trim(),
        });
        const data = res.data as {
            answer?: string;
            section_summaries?: { section_path: string; summary: string }[];
        };
        answer.value = data.answer ?? '';
        summaries.value = data.section_summaries ?? [];
    } catch (err: unknown) {
        const detail =
            err && typeof err === 'object' && 'response' in err
                ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
                : undefined;
        ElMessage.error(detail || '长文档分析失败');
    } finally {
        loading.value = false;
    }
};

onMounted(loadCorpora);
</script>
